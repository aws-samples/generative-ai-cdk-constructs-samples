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
    Aws,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_events as events,
)
from aws_solutions_constructs.aws_eventbridge_lambda import EventbridgeToLambda
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression
from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    BedrockDataAutomation
)
from .stack_constructs import (
    ServerAccessLogsBucketConstruct,
    BucketConstruct,
    TableConstruct,
    CognitoConstruct,
    ApiGatewayConstruct,
    PythonFunctionConstruct
)

class BackendStack(Stack):

    BDA_KB_DOCUMENTS_PREFIX = 'jobs'

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

       # Create the S3 bucket used to store the output of the custom parsing and act as data source of KB
        self.logging_bucket = ServerAccessLogsBucketConstruct(
            self,
            "LoggingBucket",
        )

        # BDA output S3 bucket
        self.bda_custom_parsing_output_bucket = BucketConstruct(
            self,
            "BDACustomParsingOutputBucket",
            server_access_logs_bucket=self.logging_bucket,
        )

        # DynamoDB Video task table
        self.video_task_table = TableConstruct(
            self,
            "VideoTaskTable",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING)
        )

        # BDA construct
        self.bda_construct = BedrockDataAutomation(self, "BDAConstruct",
            is_custom_bda_blueprint_required=True,
            is_bda_project_required=True,
            is_bda_invocation_required=False, #we use our own function since we want to do additional things like put a job in DynamoDB
            is_status_required=False,
        )

         # Amazon Vector Knowledge Base
        self.kb = bedrock.VectorKnowledgeBase(self, 'KnowledgeBase-BDA', 
            embeddings_model= bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_1024,
            instruction=  'Use this knowledge base to answer questions about BDA processed files.',
            description= 'BDA customized parser Knowledge Bases',                    
        )

        ## Bedrock knowledge base data source
        self.kb_ds = bedrock.S3DataSource(self, 'DataSource-BDA',
            bucket= self.bda_custom_parsing_output_bucket,
            knowledge_base=self.kb,
            data_source_name='bda-customized-ds',
            chunking_strategy= bedrock.ChunkingStrategy.fixed_size(
                max_tokens=500,
                overlap_percentage=20 
            ),
            inclusion_prefixes=[f"{BackendStack.BDA_KB_DOCUMENTS_PREFIX}/"]     
        )

        # Custom parsing process
        self.custom_parsing_fn = PythonFunctionConstruct(
            self,
            "CustomParsingFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambdas", "custom_parsing_fn"),
            description="Custom parsing of Amazon BDA outputs for Amazon KB.",
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(1),
            environment={
                "LOG_LEVEL": "DEBUG",
                "JOBS_TABLE": self.video_task_table.table_name,
                "OUTPUT_BUCKET": self.bda_custom_parsing_output_bucket.bucket_name,
                "KB_DATA_SOURCE_PREFIX": BackendStack.BDA_KB_DOCUMENTS_PREFIX,
                "KB_DATA_SOURCE_ID": self.kb_ds.data_source_id,
                "KB_ID": self.kb.knowledge_base_id
            },
        )

        self.video_task_table.grant_read_write_data(self.custom_parsing_fn.role)
        self.bda_custom_parsing_output_bucket.grant_read_write(self.custom_parsing_fn)
        self.bda_construct.bda_output_bucket.grant_read_write(self.custom_parsing_fn)

        # Add policy to the Lambda function role to trigger Ingestion Job in KB
        self.custom_parsing_fn.role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'bedrock:StartIngestionJob',
            ],
            resources=[self.kb.knowledge_base_arn],
        ))

        # rule to trigger the custom parsing lambda when the job completion event is emitted by BDA
        EventbridgeToLambda(self, 'eventbridgecustomparsing',
            existing_lambda_obj=self.custom_parsing_fn,
            event_rule_props=events.RuleProps(
                description="Rule triggered when a BDA job is done",
                event_pattern=events.EventPattern(
                    source= ["aws.bedrock"],
                    detail_type=["Bedrock Data Automation Job Succeeded", "Bedrock Data Automation Job Failed With Client Error", "Bedrock Data Automation Job Failed With Service Error"],
                ),
            )
        )

       # Cognito user pool
        self.cognito = CognitoConstruct(
            self,
            "Cognito",
            region=self.region,
            bucket=self.bda_construct.bda_input_bucket
        )

       # Api Gateway
        self.apigw = ApiGatewayConstruct(
            self,
            "ApiGateway",
            region=self.region,
            user_pool=self.cognito.user_pool,
        )

        self.get_job_fn = PythonFunctionConstruct(
            self,
            "GetJobFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambdas", "get_job_fn"),
            description="Get a specific job.",
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(1),
            environment={
                "LOG_LEVEL": "DEBUG",
                "JOBS_TABLE": self.video_task_table.table_name,
            },
        )
        self.get_job_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                resources=[
                    f"arn:aws:s3:::{self.bda_construct.bda_input_bucket.bucket_name}",
                    f"arn:aws:s3:::{self.bda_construct.bda_input_bucket.bucket_name}/*",
                    f"arn:aws:s3:::{self.bda_construct.bda_output_bucket.bucket_name}",
                    f"arn:aws:s3:::{self.bda_construct.bda_output_bucket.bucket_name}/*"
                ]
            )
        )
        self.video_task_table.grant_read_data(self.get_job_fn.role)

        self.get_jobs_fn = PythonFunctionConstruct(
            self,
            "GetJobsFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambdas", "get_jobs_fn"),
            description="Get all jobs.",
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(5),
            environment={
                "LOG_LEVEL": "DEBUG",
                "JOBS_TABLE": self.video_task_table.table_name,
            },
        )

        # lambda to send a new job
        self.start_job_fn = PythonFunctionConstruct(
            self,
            "StartJobFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambdas", "start_job_fn"),
            description="Trigger Amazon BDA and update the jobs table.",
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(5),
            environment={
                "LOG_LEVEL": "DEBUG",
                "JOBS_TABLE": self.video_task_table.table_name,
                "OUTPUT_BUCKET": self.bda_construct.bda_output_bucket.bucket_name,
                "INPUT_BUCKET": self.bda_construct.bda_input_bucket.bucket_name,
            },
        )

        # Add policy to the Lambda function role to trigger BDA
        # update resources when it goes GA
        self.start_job_fn.role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'bedrock:InvokeDataAutomationAsync',
            ],
            resources=[
                #f"arn:{Aws.PARTITION}:bedrock:{Aws.REGION}:aws:data-automation-project/public-default",
                f"arn:{Aws.PARTITION}:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:data-automation-project/*",
                f"arn:{Aws.PARTITION}:bedrock:*:{Aws.ACCOUNT_ID}:data-automation-profile/*",
            ],
        ))

        self.video_task_table.grant_read_write_data(self.start_job_fn.role)
        self.bda_construct.bda_input_bucket.grant_read(self.start_job_fn)
        self.bda_construct.bda_output_bucket.grant_read_write(self.start_job_fn)

        self.video_task_table.grant_read_data(self.get_jobs_fn.role)

        # Q&A Lambda function for document questions
        self.qa_fn = PythonFunctionConstruct(
            self,
            "QAFunction",
            entry=os.path.join(os.path.dirname(__file__), "lambdas", "qa_fn"),
            description="Answer questions about documents using RAG and Bedrock.",
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(5),
            environment={
                "LOG_LEVEL": "DEBUG",
                "KB_ID": self.kb.knowledge_base_id
            },
        )

        # Add policy for Bedrock and KB access for on demand inference
        self.qa_fn.role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'bedrock:InvokeModel',
                'bedrock:InvokeModelWithResponseStream',
            ],
            resources=[
                f'arn:{Aws.PARTITION}:bedrock:{Aws.REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0',
                f'arn:{Aws.PARTITION}:bedrock:{Aws.REGION}::foundation-model/amazon.nova-pro-v1:0',
                f'arn:{Aws.PARTITION}:bedrock:{Aws.REGION}::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0'
            ]  # Bedrock model ARNs
        ))

        # Add policy for Bedrock and KB access for on CRIS
        self.qa_fn.role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'bedrock:InvokeModel',
                'bedrock:InvokeModelWithResponseStream',
                'bedrock:GetInferenceProfile',
                'bedrock:GetFoundationModel'
            ],
            resources=[
                f'arn:{Aws.PARTITION}:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0',
                f'arn:{Aws.PARTITION}:bedrock:*::foundation-model/amazon.nova-pro-v1:0',
                f'arn:{Aws.PARTITION}:bedrock:*::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0',
                f'arn:{Aws.PARTITION}:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0',
                f'arn:{Aws.PARTITION}:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:inference-profile/us.amazon.nova-pro-v1:0',
                f'arn:{Aws.PARTITION}:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0'
            ]  # Inference profile ARNs
        ))

        self.qa_fn.role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'bedrock:RetrieveAndGenerate',
                'bedrock:Retrieve'
            ],
            resources=[self.kb.knowledge_base_arn]
        ))

        # Get the content of a specific job
        self.apigw.add_lambda_method(
            resource_path="/jobs/{id}",
            http_method="GET",
            lambda_function=self.get_job_fn,
            request_validator=self.apigw.request_params_validator,
            request_parameters={
                "method.request.path.id": True  # Path parameter is required
            }
        )

        # List all the jobs stored in dynamoDB
        self.apigw.add_lambda_method(
            resource_path="/jobs",
            http_method="GET",
            lambda_function=self.get_jobs_fn,
            request_validator=self.apigw.request_params_validator,
            request_parameters={
                "method.request.querystring.limit": False,  # Optional parameter
                "method.request.querystring.start_key": False  # Optional parameter
            }
        )

        # Submit a new job for processing
        self.apigw.add_lambda_method(
            resource_path="/jobs",
            http_method="POST",
            lambda_function=self.start_job_fn,
            request_validator=self.apigw.request_body_params_validator,
        )

        # BDA Blueprint management
        self.apigw.add_lambda_method(
            resource_path="/blueprint",
            http_method="POST",
            lambda_function=self.bda_construct.bda_blueprint_lambda_function,
            request_validator=self.apigw.request_body_params_validator,
        )

        # BDA Project management
        self.apigw.add_lambda_method(
            resource_path="/project",
            http_method="POST",
            lambda_function=self.bda_construct.bda_project_function,
            request_validator=self.apigw.request_body_params_validator,
        )

        # Q&A endpoint for document questions
        self.apigw.add_lambda_method(
            resource_path="/qa",
            http_method="POST",
            lambda_function=self.qa_fn,
            request_validator=self.apigw.request_body_params_validator,
        )

        self.api_gw_exec_role = iam.Role(self, "APIGWExecutionRole",
                                         assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
                                         description="Used by API Gateway to execute S3 operations",
                                         )
        
        # Upload a document to the input BDA S3 bucket
        self.apigw.add_s3_method(
            resource_path="/documents/{key}",
            http_method="PUT",
            request_validator=self.apigw.request_body_validator,
            execution_role=self.api_gw_exec_role,
            bucket_name=self.bda_construct.bda_input_bucket.bucket_name,
        )

        # Get a specific document from the input BDA S3 bucket
        self.apigw.add_s3_method(
            resource_path="/documents/{key}",
            http_method="GET",
            request_validator=self.apigw.request_body_validator,
            execution_role=self.api_gw_exec_role,
            bucket_name=self.bda_construct.bda_input_bucket.bucket_name,
        )

        self.bda_construct.bda_input_bucket.grant_read_write(self.api_gw_exec_role)

        #####################
        ### STACK OUTPUTS ###
        #####################

        CfnOutput(
            self,
            "BDACustomParsinOutputBucket",
            value=self.bda_custom_parsing_output_bucket.bucket_name,
            description="S3 bucket used to store the output of the custom parsing and act as data source of KB."
        )

        CfnOutput(
            self,
            "RegionName",
            value=self.region,
            export_name=f"{Stack.of(self).stack_name}RegionName",
        )

        CfnOutput(
            self,
            "VideoTaskTableName",
            value=self.video_task_table.table_name,
            description="DynamoDB table containing processing jobs."
        )

        CfnOutput(
            self,
            "BDAOutputBucket",
            value=self.bda_construct.bda_output_bucket.bucket_name,
            description="S3 bucket used to store the output of the BDA process."
        )

        CfnOutput(
            self,
            "BDAInputBucket",
            value=self.bda_construct.bda_input_bucket.bucket_name,
            description="S3 bucket used to store the inputs documents for the BDA process."
        )

        CfnOutput(
            self,
            "KnowledgeBaseId",
            value=self.kb.knowledge_base_id,
            description="If of the Amazon Bedrock Knowledge Base."
        )

        CfnOutput(
            self,
            "KnowledgeBaseDataSourceId",
            value=self.kb_ds.data_source_id,
            description="If of the Amazon Bedrock Knowledge Base S3 data source."
        )

        ##########################
        ## CDK NAG SUPPRESSIONS ##
        ##########################

        NagSuppressions.add_resource_suppressions_by_path(
            stack=self,
            path=f"/{self.node.path}/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole",
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="CDK CustomResource LogRetention Lambda uses the AWSLambdaBasicExecutionRole AWS Managed Policy. Managed by CDK.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="CDK CustomResource LogRetention Lambda uses a wildcard to manage log streams created at runtime. Managed by CDK.",
                ),
            ],
            apply_to_children=True
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

        NagSuppressions.add_resource_suppressions(
            construct=self.custom_parsing_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because object naming is not standardized",
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.start_job_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because object naming is not standardized",
                ),
            ],
            apply_to_children=True,
        )
        
        NagSuppressions.add_resource_suppressions(
            construct=self.cognito.auth_user_role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because object naming is not standardized",
                ),
            ],
            apply_to_children=True,
        )
        
        NagSuppressions.add_resource_suppressions(
            construct=self.get_job_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because object naming is not standardized",
                ),
            ],
            apply_to_children=True,
        )
        
        NagSuppressions.add_resource_suppressions(
            construct=self.qa_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because bedrock invokation is not standardized",
                ),
            ],
            apply_to_children=True,
        )
