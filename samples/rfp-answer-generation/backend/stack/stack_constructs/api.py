#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import os

from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_stepfunctions as sfn,
    Duration,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression

from .apigateway import ApiGatewayConstruct
from .aws_lambda import PythonFunctionConstruct
from .cognito import CognitoConstruct


class APIConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        region: str,
        inference_bucket: s3.Bucket,
        questionnaire_table: dynamodb.Table,
        jobs_table: dynamodb.Table,
        state_machine: sfn.StateMachine,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.cognito = CognitoConstruct(
            self,
            "Cognito",
            region=region,
        )

        self.apigw = ApiGatewayConstruct(
            self,
            "ApiGateway",
            region=region,
            user_pool=self.cognito.user_pool,
        )

        # Lambda functions for the API
        self.start_job_fn = PythonFunctionConstruct(
            self,
            "StartJobFunction",
            entry=os.path.join(
                os.path.dirname(__file__), "..", "lambdas", "start_job_fn"
            ),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.minutes(1),
            environment={
                "LOG_LEVEL": "INFO",
                "JOBS_TABLE": jobs_table.table_name,
                "STATE_MACHINE_ARN": state_machine.state_machine_arn,
            },
        )

        self.get_jobs_fn = PythonFunctionConstruct(
            self,
            "GetJobsFunction",
            entry=os.path.join(
                os.path.dirname(__file__), "..", "lambdas", "get_jobs_fn"
            ),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.minutes(1),
            environment={
                "LOG_LEVEL": "INFO",
                "JOBS_TABLE": jobs_table.table_name,
            },
        )

        self.get_questionnaire_fn = PythonFunctionConstruct(
            self,
            "GetQuestionnaireFunction",
            entry=os.path.join(
                os.path.dirname(__file__), "..", "lambdas", "get_questionnaire_fn"
            ),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.minutes(1),
            environment={
                "LOG_LEVEL": "INFO",
                "QUESTIONNAIRE_TABLE": questionnaire_table.table_name,
                "JOBS_TABLE": jobs_table.table_name,
            },
        )

        self.put_questionnaire_entry_fn = PythonFunctionConstruct(
            self,
            "PutQuestionnaireEntryFunction",
            entry=os.path.join(
                os.path.dirname(__file__), "..", "lambdas", "put_questionnaire_entry_fn"
            ),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.minutes(1),
            environment={
                "LOG_LEVEL": "INFO",
                "QUESTIONNAIRE_TABLE": questionnaire_table.table_name,
            },
        )

        self.approve_job_fn = PythonFunctionConstruct(
            self,
            "ApproveJobFunction",
            entry=os.path.join(
                os.path.dirname(__file__), "..", "lambdas", "approve_job_fn"
            ),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.minutes(1),
            environment={
                "LOG_LEVEL": "INFO",
                "QUESTIONNAIRE_TABLE": questionnaire_table.table_name,
                "JOBS_TABLE": jobs_table.table_name,
            },
        )

        # API methods
        self.apigw.add_lambda_method(
            resource_path="/jobs",
            http_method="GET",
            lambda_function=self.get_jobs_fn,
            request_validator=self.apigw.request_body_params_validator,
        )

        self.apigw.add_lambda_method(
            resource_path="/questionnaires/{job_id}",
            http_method="GET",
            lambda_function=self.get_questionnaire_fn,
            request_validator=self.apigw.request_body_params_validator,
        )

        self.apigw.add_lambda_method(
            resource_path="/questionnaires/{job_id}/{question_number}",
            http_method="PUT",
            lambda_function=self.put_questionnaire_entry_fn,
            request_validator=self.apigw.request_body_params_validator,
        )

        self.apigw.add_lambda_method(
            resource_path="/approve/{job_id}",
            http_method="PUT",
            lambda_function=self.approve_job_fn,
            request_validator=self.apigw.request_body_params_validator,
        )

        self.api_gw_exec_role = iam.Role(
            self,
            "APIGWExecutionRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            description="Used by API Gateway to execute S3 operations",
        )

        self.apigw.add_s3_method(
            resource_path="/inference/{key}",
            http_method="PUT",
            request_validator=self.apigw.request_body_validator,
            execution_role=self.api_gw_exec_role,
            bucket_name=inference_bucket.bucket_name,
        )

        jobs_table.grant_read_data(self.start_job_fn.role)
        jobs_table.grant_write_data(self.start_job_fn.role)
        jobs_table.grant_read_data(self.get_jobs_fn.role)
        jobs_table.grant_read_data(self.get_questionnaire_fn.role)
        jobs_table.grant_read_data(self.approve_job_fn.role)
        jobs_table.grant_write_data(self.approve_job_fn.role)

        questionnaire_table.grant_read_data(self.get_questionnaire_fn.role)
        questionnaire_table.grant_read_data(self.put_questionnaire_entry_fn.role)
        questionnaire_table.grant_write_data(self.put_questionnaire_entry_fn.role)
        questionnaire_table.grant_read_data(self.approve_job_fn.role)
        questionnaire_table.grant_write_data(self.approve_job_fn.role)

        state_machine.grant_read(self.start_job_fn.role)
        state_machine.grant_start_execution(self.start_job_fn.role)

        inference_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(self.start_job_fn),
            s3.NotificationKeyFilter(suffix=".xlsx"),
        )

        inference_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(self.start_job_fn),
            s3.NotificationKeyFilter(suffix=".csv"),
        )

        inference_bucket.grant_read_write(self.api_gw_exec_role)

        NagSuppressions.add_resource_suppressions(
            construct=self.start_job_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because to support multiple versions of the state machine",
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.api_gw_exec_role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="API Gateway uses wildcard used because object naming is not standardized",
                ),
            ],
            apply_to_children=True,
        )
