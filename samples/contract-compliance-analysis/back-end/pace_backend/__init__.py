#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import os
from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression
from pace_backend.config.properties import AppProperties

import pace_constructs as pace
from .sfn import StepFunctionsStack

class PACEBackendStack(Stack):
    DOCUMENTS_FOLDER = 'documents'

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        properties_file_path = self.node.try_get_context('appPropertiesFilePath')
        app_properties = AppProperties(properties_file_path)

        # Logging S3 bucket
        self.logging_bucket = pace.PACEServerAccessLogsBucket(
            self,
            "LoggingBucket",
        )

        # Contract S3 bucket
        self.contract_bucket = pace.PACEBucket(
            self,
            "ContractBucket",
            server_access_logs_bucket=self.logging_bucket,
        )

        # Guidelines DynamoDB table
        self.guidelines_table = pace.PACETable(
            self,
            "GuidelinesTable",
            partition_key=dynamodb.Attribute(name="type_id", type=dynamodb.AttributeType.STRING)
        )

        CfnOutput(
            self,
            "GuidelinesTableName",
            value=self.guidelines_table.table_name,
        )

        # Clauses DynamoDB table
        self.clauses_table = pace.PACETable(
            self,
            "ClausesTable",
            partition_key=dynamodb.Attribute(name="job_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="clause_number", type=dynamodb.AttributeType.NUMBER)
        )

        # Jobs DynamoDB table
        self.jobs_table = pace.PACETable(
            self,
            "JobsTable",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
        )

        # Contract Analysis State Machine
        self.sfn_stack = StepFunctionsStack(
            self,
            "StepFunctionsStack",
            contract_bucket=self.contract_bucket,
            guidelines_table=self.guidelines_table,
            clauses_table=self.clauses_table,
            jobs_table=self.jobs_table,
            app_properties=app_properties
        )

        # API protected with Cognito
        self.cognito = pace.PACECognito(
            self,
            "Cognito",
            region=self.region,
        )
        self.apigw = pace.PACEApiGateway(
            self,
            "ApiGateway",
            region=self.region,
            user_pool=self.cognito.user_pool,
        )

        # Lambda functions for the API
        self.get_job_fn = pace.PACEPythonFunction(
            self,
            "GetJobFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambda", "get_job_fn"),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.minutes(1),
            environment={
                "LOG_LEVEL": "DEBUG",
                "JOBS_TABLE": self.jobs_table.table_name,
                "CLAUSES_TABLE": self.clauses_table.table_name,
                "STATE_MACHINE_ARN": self.sfn_stack.state_machine.state_machine_arn
            },
        )
        self.jobs_table.grant_read_data(self.get_job_fn.role)
        self.clauses_table.grant_read_data(self.get_job_fn.role)
        self.sfn_stack.state_machine.grant_read(self.get_job_fn.role)

        awswrangler_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "AwsWranglerLayer",
            f"arn:aws:lambda:{Stack.of(self).region}:336392948345:layer:AWSSDKPandas-Python312:9"
        )

        self.get_jobs_fn = pace.PACEPythonFunction(
            self,
            "GetJobsFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambda", "get_jobs_fn"),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.minutes(5),
            environment={
                "LOG_LEVEL": "DEBUG",
                "JOBS_TABLE": self.jobs_table.table_name,
                "STATE_MACHINE_ARN": self.sfn_stack.state_machine.state_machine_arn
            },
            layers=[awswrangler_layer]
        )
        self.jobs_table.grant_read_data(self.get_jobs_fn.role)
        self.jobs_table.grant_write_data(self.get_jobs_fn.role)
        self.sfn_stack.state_machine.grant_read(self.get_jobs_fn.role)

        self.post_jobs_fn = pace.PACEPythonFunction(
            self,
            "PostJobsFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambda", "post_jobs_fn"),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.minutes(1),
            environment={
                "LOG_LEVEL": "DEBUG",
                "JOBS_TABLE": self.jobs_table.table_name,
                "DOCUMENTS_BUCKET": self.contract_bucket.bucket_name,
                "DOCUMENTS_FOLDER": PACEBackendStack.DOCUMENTS_FOLDER,
                "STATE_MACHINE_ARN": self.sfn_stack.state_machine.state_machine_arn
            },
        )
        self.jobs_table.grant_write_data(self.post_jobs_fn.role)
        self.sfn_stack.state_machine.grant_read(self.post_jobs_fn.role)
        self.sfn_stack.state_machine.grant_start_execution(self.post_jobs_fn.role)

        # API methods
        self.apigw.add_lambda_method(
            resource_path="/jobs/{id}",
            http_method="GET",
            lambda_function=self.get_job_fn,
            request_validator=self.apigw.request_body_params_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/jobs",
            http_method="GET",
            lambda_function=self.get_jobs_fn,
            request_validator=self.apigw.request_body_params_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/jobs",
            http_method="POST",
            lambda_function=self.post_jobs_fn,
            request_validator=self.apigw.request_body_params_validator,
        )

        self.api_gw_exec_role = iam.Role(self, "APIGWExecutionRole",
                                         assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
                                         description="Used by API Gateway to execute S3 operations",
                                         )
        self.apigw.add_s3_method(
            resource_path="/documents/{key}",
            http_method="PUT",
            request_validator=self.apigw.request_body_validator,
            execution_role=self.api_gw_exec_role,
            bucket_name=self.contract_bucket.bucket_name,
            bucket_folder=PACEBackendStack.DOCUMENTS_FOLDER,
        )
        self.apigw.add_s3_method(
            resource_path="/documents/{key}",
            http_method="GET",
            request_validator=self.apigw.request_body_validator,
            execution_role=self.api_gw_exec_role,
            bucket_name=self.contract_bucket.bucket_name,
            bucket_folder=PACEBackendStack.DOCUMENTS_FOLDER,
        )
        self.contract_bucket.grant_read_write(self.api_gw_exec_role)

        CfnOutput(
            self,
            "RegionName",
            value=self.region,
            export_name=f"{Stack.of(self).stack_name}RegionName",
        )

        # cdk-nag suppressions
        stack_suppressions = [
            # Insert your stack-level NagPackSuppression"s here
        ]
        NagSuppressions.add_stack_suppressions(
            stack=self,
            suppressions=stack_suppressions,
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.get_jobs_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because to support multiple versions of the state machine",
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.get_jobs_fn,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Python 3.11 is the most recent supported version",
                ),
            ],
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.get_job_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because to support multiple versions of the state machine",
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.get_job_fn,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Python 3.11 is the most recent supported version",
                ),
            ],
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.post_jobs_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because to support multiple versions of the state machine",
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.post_jobs_fn,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Python 3.11 is the most recent supported version",
                ),
            ],
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.api_gw_exec_role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because object naming is not standardized",
                ),
            ],
            apply_to_children=True,
        )
