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
    Aws,
    Stack,
    CfnOutput,
    Duration,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression

import stack_constructs
from .sfn.contract_analysis import ContractAnalysisWorkflow
from .sfn.contract_import import ContractImportWorkflow


class BackendStack(Stack):
    DOCUMENTS_FOLDER = 'documents'

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Logging S3 bucket
        self.logging_bucket = stack_constructs.ServerAccessLogsBucketConstruct(
            self,
            "LoggingBucket",
        )

        # Contract S3 bucket
        self.contract_bucket = stack_constructs.BucketConstruct(
            self,
            "ContractBucket",
            server_access_logs_bucket=self.logging_bucket,
        )

        CfnOutput(
            self,
            "ContractBucketName",
            value=self.contract_bucket.bucket_name,
            export_name=f"{Stack.of(self).stack_name}-ContractBucketName"
        )

        # Guidelines DynamoDB table
        self.guidelines_table = stack_constructs.TableConstruct(
            self,
            "GuidelinesTable",
            partition_key=dynamodb.Attribute(name="contract_type_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="clause_type_id", type=dynamodb.AttributeType.STRING)
        )

        CfnOutput(
            self,
            "GuidelinesTableName",
            value=self.guidelines_table.table_name,
        )

        # Clauses DynamoDB table
        self.clauses_table = stack_constructs.TableConstruct(
            self,
            "ClausesTable",
            partition_key=dynamodb.Attribute(name="job_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="clause_number", type=dynamodb.AttributeType.NUMBER)
        )

        CfnOutput(
            self,
            "ClausesTableName",
            value=self.clauses_table.table_name,
            export_name=f"{Stack.of(self).stack_name}-ClausesTableName"
        )

        # Jobs DynamoDB table
        self.jobs_table = stack_constructs.TableConstruct(
            self,
            "JobsTable",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
        )

        # Add GSI for contract type filtering
        self.jobs_table.add_global_secondary_index(
            index_name="contract_type_id-created_at-index",
            partition_key=dynamodb.Attribute(name="contract_type_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="created_at", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Contract Types DynamoDB table
        self.contract_types_table = stack_constructs.TableConstruct(
            self,
            "ContractTypesTable",
            partition_key=dynamodb.Attribute(name="contract_type_id", type=dynamodb.AttributeType.STRING),
        )

        CfnOutput(
            self,
            "ContractTypesTableName",
            value=self.contract_types_table.table_name,
        )

        # Import Jobs DynamoDB table
        self.import_jobs_table = stack_constructs.TableConstruct(
            self,
            "ImportJobsTable",
            partition_key=dynamodb.Attribute(name="import_job_id", type=dynamodb.AttributeType.STRING),
        )

        CfnOutput(
            self,
            "ImportJobsTableName",
            value=self.import_jobs_table.table_name,
        )

        self.event_bus = events.EventBus(self, "EventBus")

        # Contract Analysis Workflow Stack
        self.analysis_workflow = ContractAnalysisWorkflow(
            self,
            "ContractAnalysisWorkflow",
            contract_bucket=self.contract_bucket,
            guidelines_table=self.guidelines_table,
            clauses_table=self.clauses_table,
            jobs_table=self.jobs_table,
            contract_types_table=self.contract_types_table,
            event_bus=self.event_bus,
        )

        # Contract Import Workflow Stack
        self.import_workflow = ContractImportWorkflow(
            self,
            "ContractImportWorkflow",
            contract_bucket=self.contract_bucket,
            contract_types_table=self.contract_types_table,
            guidelines_table=self.guidelines_table,
            import_jobs_table=self.import_jobs_table,
            common_layer=self.analysis_workflow.common_layer,
            langchain_deps_layer=self.analysis_workflow.langchain_deps_layer,
        )

        # API protected with Cognito
        self.cognito = stack_constructs.CognitoConstruct(
            self,
            "Cognito",
            region=self.region,
        )

        # Grant S3 permissions to Cognito authenticated users for Amplify Storage
        self.cognito.auth_user_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:PutObject",  # For uploads
                "s3:ListBucket"  # For listing objects (required by Amplify Storage)
            ],
            resources=[
                f"{self.contract_bucket.bucket_arn}/*",
                self.contract_bucket.bucket_arn,  # Bucket-level permissions for ListBucket
            ]
        ))

        self.apigw = stack_constructs.ApiGatewayConstruct(
            self,
            "ApiGateway",
            region=self.region,
            user_pool=self.cognito.user_pool,
        )

        # NEW API
        powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "PowertoolsLayer",
            f"arn:aws:lambda:{Stack.of(self).region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-x86_64:21")
        self.jobs_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "JobsApiFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambda", "api", "jobs_fn"),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(1),
            layers=[powertools_layer, self.analysis_workflow.common_layer],
            environment={
                "JOBS_TABLE": self.jobs_table.table_name,
                "CLAUSES_TABLE": self.clauses_table.table_name,
                "CONTRACT_TYPES_TABLE": self.contract_types_table.table_name,  # Only for validation
                "STATE_MACHINE_ARN": self.analysis_workflow.state_machine.state_machine_arn,
                "DOCUMENTS_BUCKET": self.contract_bucket.bucket_name,
                "DOCUMENTS_FOLDER": BackendStack.DOCUMENTS_FOLDER,
                "POWERTOOLS_SERVICE_NAME": "jobs_api",
                "POWERTOOLS_LOG_LEVEL": "INFO",
            },
        )

        # Grant permissions to Jobs Function (reduced scope)
        self.jobs_table.grant_read_write_data(self.jobs_fn.role)
        self.clauses_table.grant_read_data(self.jobs_fn.role)
        self.contract_types_table.grant_read_data(self.jobs_fn.role)  # Only read access for validation
        self.analysis_workflow.state_machine.grant_read(self.jobs_fn.role)
        self.analysis_workflow.state_machine.grant_start_execution(self.jobs_fn.role)
        
        # Grant permission to describe CheckLegislation workflow executions (optional CheckLegislationStack)
        # Jobs API needs to query legislation check status when it's enabled
        # Note: This permission must be added here (where the role is created) rather than in CheckLegislationStack
        # because: 1) imported roles (IRole) are read-only and don't support add_to_policy(), and
        # 2) attempting to modify the role from CheckLegislationStack would create a circular dependency
        self.jobs_fn.role.add_to_policy(
            iam.PolicyStatement(
                actions=["states:DescribeExecution"],
                resources=[f"arn:aws:states:{self.region}:{self.account}:execution:CheckLegislation*:*"]
            )
        )



        # Contract Types API Function
        self.contract_types_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "ContractTypesApiFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambda", "api", "contract_types_fn"),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(2),
            layers=[powertools_layer, self.analysis_workflow.common_layer],
            environment={
                "CONTRACT_TYPES_TABLE": self.contract_types_table.table_name,
                "GUIDELINES_TABLE": self.guidelines_table.table_name,
                "IMPORT_JOBS_TABLE": self.import_jobs_table.table_name,
                "IMPORT_STATE_MACHINE_ARN": self.import_workflow.state_machine.state_machine_arn,
                "POWERTOOLS_SERVICE_NAME": "contract_types_api",
                "POWERTOOLS_LOG_LEVEL": "INFO",
            },
        )

        # Grant permissions to Contract Types Function
        self.contract_types_table.grant_read_write_data(self.contract_types_fn.role)
        self.guidelines_table.grant_read_write_data(self.contract_types_fn.role)  # For deletion cascade
        self.import_jobs_table.grant_read_write_data(self.contract_types_fn.role)
        self.import_workflow.state_machine.grant_start_execution(self.contract_types_fn.role)
        self.import_workflow.state_machine.grant_read(self.contract_types_fn.role)

        # Guidelines API Function
        self.guidelines_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "GuidelinesApiFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambda", "api", "guidelines_fn"),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(2),
            layers=[powertools_layer, self.analysis_workflow.common_layer, self.analysis_workflow.langchain_deps_layer],
            environment={
                "CONTRACT_TYPES_TABLE": self.contract_types_table.table_name,
                "GUIDELINES_TABLE": self.guidelines_table.table_name,
                "POWERTOOLS_SERVICE_NAME": "guidelines_api",
                "POWERTOOLS_LOG_LEVEL": "INFO",
            },
        )

        # Grant permissions to Guidelines Function
        self.contract_types_table.grant_read_data(self.guidelines_fn.role)  # For validation
        self.guidelines_table.grant_read_write_data(self.guidelines_fn.role)

        # Grant Bedrock permissions to Guidelines Function for LLM operations
        self.guidelines_fn.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
            ],
            resources=[
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*:"+Aws.ACCOUNT_ID+":inference-profile/*",
            ]
        ))

        # Add marketplace permissions for Claude models
        stack_constructs.add_bedrock_marketplace_permissions(self.guidelines_fn.role)

        # Grant SSM permissions to Guidelines Function for parameter access
        self.guidelines_fn.role.add_to_policy(iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/ContractAnalysis/*"]
        ))
        
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"{self.guidelines_fn.role.node.path}/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard required for SSM parameters under /ContractAnalysis/ path",
                    "appliesTo": [f"Resource::arn:aws:ssm:<AWS::Region>:<AWS::AccountId>:parameter/ContractAnalysis/*"]
                }
            ]
        )

        # API methods for Jobs
        self.apigw.add_lambda_method(
            resource_path="/jobs/{job_id}",
            http_method="GET",
            lambda_function=self.jobs_fn,
            request_validator=self.apigw.request_body_params_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/jobs",
            http_method="GET",
            lambda_function=self.jobs_fn,
            request_validator=self.apigw.request_body_params_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/jobs",
            http_method="POST",
            lambda_function=self.jobs_fn,
            request_validator=self.apigw.request_body_params_validator,
        )

        # API methods for Contract Types
        self.apigw.add_lambda_method(
            resource_path="/contract-types",
            http_method="GET",
            lambda_function=self.contract_types_fn,
            request_validator=self.apigw.request_params_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/contract-types",
            http_method="POST",
            lambda_function=self.contract_types_fn,
            request_validator=self.apigw.request_body_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/contract-types/{contract_type_id}",
            http_method="GET",
            lambda_function=self.contract_types_fn,
            request_validator=self.apigw.request_params_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/contract-types/{contract_type_id}",
            http_method="PUT",
            lambda_function=self.contract_types_fn,
            request_validator=self.apigw.request_body_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/contract-types/{contract_type_id}",
            http_method="DELETE",
            lambda_function=self.contract_types_fn,
            request_validator=self.apigw.request_params_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/import/contract-types",
            http_method="POST",
            lambda_function=self.contract_types_fn,
            request_validator=self.apigw.request_body_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/import/contract-types/{import_job_id}",
            http_method="GET",
            lambda_function=self.contract_types_fn,
            request_validator=self.apigw.request_params_validator,
        )

        # API methods for Guidelines
        self.apigw.add_lambda_method(
            resource_path="/guidelines",
            http_method="GET",
            lambda_function=self.guidelines_fn,
            request_validator=self.apigw.request_params_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/guidelines",
            http_method="POST",
            lambda_function=self.guidelines_fn,
            request_validator=self.apigw.request_body_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/guidelines/{contract_type_id}/{clause_type_id}",
            http_method="GET",
            lambda_function=self.guidelines_fn,
            request_validator=self.apigw.request_params_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/guidelines/{contract_type_id}/{clause_type_id}",
            http_method="PUT",
            lambda_function=self.guidelines_fn,
            request_validator=self.apigw.request_body_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/guidelines/{contract_type_id}/{clause_type_id}",
            http_method="DELETE",
            lambda_function=self.guidelines_fn,
            request_validator=self.apigw.request_params_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/guidelines/{contract_type_id}/{clause_type_id}/generate-questions",
            http_method="POST",
            lambda_function=self.guidelines_fn,
            request_validator=self.apigw.request_body_validator,
        )
        self.apigw.add_lambda_method(
            resource_path="/guidelines/{contract_type_id}/{clause_type_id}/generate-examples",
            http_method="POST",
            lambda_function=self.guidelines_fn,
            request_validator=self.apigw.request_body_validator,
        )

        CfnOutput(
            self,
            "RegionName",
            value=self.region,
            export_name=f"{Stack.of(self).stack_name}RegionName",
        )

        # Import State Machine output
        CfnOutput(
            self,
            "ContractImportWorkflowArn",
            value=self.import_workflow.state_machine.state_machine_arn,
            description="ARN of the contract import state machine"
        )

        # Log group outputs for token usage tracking
        CfnOutput(
            self,
            "PreprocessingLogGroup",
            value=self.analysis_workflow.preprocessing_step.preprocess_contract_fn.log_group.log_group_name,
            description="CloudWatch log group for the preprocessing Lambda function"
        )

        CfnOutput(
            self,
            "ClassificationLogGroup",
            value=self.analysis_workflow.classification.classify_clauses_fn.log_group.log_group_name,
            description="CloudWatch log group for the classification Lambda function"
        )

        CfnOutput(
            self,
            "EvaluationLogGroup",
            value=self.analysis_workflow.evaluation_step.evaluate_clauses_fn.log_group.log_group_name,
            description="CloudWatch log group for the evaluation Lambda function"
        )

        # Import State Machine log group outputs
        CfnOutput(
            self,
            "ContractImportWorkflowLogGroup",
            value=self.import_workflow.state_machine_logs.log_group_name,
            description="CloudWatch log group for the import state machine"
        )

        CfnOutput(
            self,
            "InitializeImportLogGroup",
            value=self.import_workflow.initialize_step.initialize_import_fn.log_group.log_group_name,
            description="CloudWatch log group for the initialize import Lambda function"
        )

        CfnOutput(
            self,
            "ExtractContractTypeInfoLogGroup",
            value=self.import_workflow.extract_contract_type_info_step.extract_contract_type_info_fn.log_group.log_group_name,
            description="CloudWatch log group for the extract contract type info Lambda function"
        )

        CfnOutput(
            self,
            "ExtractClauseTypesLogGroup",
            value=self.import_workflow.extract_clause_types_step.extract_clause_types_fn.log_group.log_group_name,
            description="CloudWatch log group for the extract clause types Lambda function"
        )

        CfnOutput(
            self,
            "FinalizeImportLogGroup",
            value=self.import_workflow.finalize_step.finalize_import_fn.log_group.log_group_name,
            description="CloudWatch log group for the finalize import Lambda function"
        )

        # Export for CheckLegislationStack
        CfnOutput(
            self,
            "JobsLambdaRoleArn",
            value=self.jobs_fn.role.role_arn,
            export_name=f"{Stack.of(self).stack_name}-JobsLambdaRoleArn"
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
            self.guidelines_fn,
            suppressions=[
                NagPackSuppression(id="AwsSolutions-L1", reason="This is a tech debt, to update lambdas")
            ]
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.jobs_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=[
                        'Resource::arn:<AWS::Partition>:states:<AWS::Region>:<AWS::AccountId>:execution:{"Fn::Select":[6,{"Fn::Split":[":",{"Ref":"ContractAnalysisStateMachineB5CAF393"}]}]}:*',
                        'Resource::arn:<AWS::Partition>:states:<AWS::Region>:<AWS::AccountId>:execution:{"Fn::Select":[6,{"Fn::Split":[":",{"Ref":"ContractImportWorkflow658B6A4F"}]}]}:*',
                    ],
                    reason="Function needs permissions to start and get details for any execution of the state machines (both contract analysis and import).",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=["Resource::*"],
                    reason="Function uses grant_read() on state machines which adds states:ListExecutions action. This action does not support resource-level permissions per AWS Step Functions service limitations.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function needs permissions to describe CheckLegislation workflow executions (optional stack).",
                    applies_to=[
                        'Resource::arn:aws:states:<AWS::Region>:<AWS::AccountId>:execution:CheckLegislation*:*'
                    ]
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function needs permissions to access GSI on Jobs table for contract type filtering.",
                    applies_to=[
                        'Resource::<JobsTable1970BC16.Arn>/index/*'
                    ]
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function requires access to all Bedrock foundation models across regions for AI-powered contract analysis functionality.",
                    applies_to=[
                        "Resource::arn:aws:bedrock:*::foundation-model/*"
                    ]
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function requires access to all Bedrock inference profiles in the account across regions for optimized AI model routing.",
                    applies_to=[
                        "Resource::arn:aws:bedrock:*:<AWS::AccountId>:inference-profile/*"
                    ]
                )
            ],
            apply_to_children=True
        )

        # Add suppression for Cognito authenticated user role S3 permissions
        NagSuppressions.add_resource_suppressions(
            construct=self.cognito.auth_user_role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard required for Amplify Storage to access contract documents with dynamic naming patterns",
                ),
            ],
            apply_to_children=True,
        )

        # Add suppression for risk calculation function GSI permissions
        NagSuppressions.add_resource_suppressions(
            construct=self.analysis_workflow.risk_step.calculate_risk_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function needs permissions to access GSI on Jobs table for contract type filtering.",
                    applies_to=[
                        'Resource::<JobsTable1970BC16.Arn>/index/*'
                    ]
                )
            ],
            apply_to_children=True,
        )

        # Add suppression for import state machine initialize function S3 permissions
        NagSuppressions.add_resource_suppressions(
            construct=self.import_workflow.initialize_step.initialize_import_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function needs S3 permissions to read contract documents from the bucket with dynamic object keys.",
                    applies_to=[
                        "Action::s3:GetObject*",
                        "Action::s3:GetBucket*",
                        "Action::s3:List*",
                        "Resource::<ContractBucketFE738A79.Arn>/*"
                    ]
                )
            ],
            apply_to_children=True,
        )

        # Add suppression for contract types function IAM permissions
        NagSuppressions.add_resource_suppressions(
            construct=self.contract_types_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function needs permissions to start and get details for any execution of the import state machine.",
                    applies_to=[
                        'Resource::arn:<AWS::Partition>:states:<AWS::Region>:<AWS::AccountId>:execution:{"Fn::Select":[6,{"Fn::Split":[":",{"Ref":"ContractImportWorkflow658B6A4F"}]}]}:*',
                        "Resource::*"
                    ]
                )
            ],
            apply_to_children=True,
        )

        # Add suppression for guidelines function Bedrock permissions
        NagSuppressions.add_resource_suppressions(
            construct=self.guidelines_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function requires access to all Bedrock foundation models across regions for AI-powered guideline generation functionality.",
                    applies_to=[
                        "Resource::arn:aws:bedrock:*::foundation-model/*"
                    ]
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function requires access to all Bedrock inference profiles in the account across regions for optimized AI model routing.",
                    applies_to=[
                        "Resource::arn:aws:bedrock:*:<AWS::AccountId>:inference-profile/*"
                    ]
                )
            ],
            apply_to_children=True,
        )
        # Add suppressions for log retention functions (automatically created by CDK)
        # These suppressions will be applied to any log retention resources created by nested stacks
        NagSuppressions.add_stack_suppressions(
            stack=self.analysis_workflow,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="AWS managed policy AWSLambdaBasicExecutionRole is required for log retention Lambda function created by CDK"
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard permissions are required for log retention Lambda function to manage CloudWatch log groups"
                )
            ]
        )

        NagSuppressions.add_stack_suppressions(
            stack=self.import_workflow,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="AWS managed policy AWSLambdaBasicExecutionRole is required for log retention Lambda function created by CDK"
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard permissions are required for log retention Lambda function to manage CloudWatch log groups"
                )
            ]
        )