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
from constructs import Construct
from aws_cdk import (
    Duration,
    Aws,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
)
from cdk_nag import NagSuppressions, NagPackSuppression

import stack_constructs

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "contract_import", "extract_contract_type_info_fn")


class ExtractContractTypeInfoStep(Construct):
    """CDK construct for contract type info extraction step"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        contract_bucket: s3.Bucket,
        import_jobs_table: dynamodb.Table,
        layers: list[lambda_.LayerVersion],
    ):
        super().__init__(scope, id)

        self.extract_contract_type_info_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "ExtractContractTypeInfoFunction",
            entry=LAMBDA_PATH,
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(10),
            memory_size=256,
            environment={
                "LOG_LEVEL": "INFO",
                "IMPORT_JOBS_TABLE_NAME": import_jobs_table.table_name,
                "CONTRACT_BUCKET_NAME": contract_bucket.bucket_name
            },
            layers=layers,
        )

        # Grant SSM Parameter Store permissions
        self.extract_contract_type_info_fn.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "ssm:GetParameter",
            ],
            resources=[
                f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/ContractAnalysis/*",
            ]
        ))

        # Grant Bedrock permissions
        self.extract_contract_type_info_fn.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
            ],
            resources=[
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*:"+Aws.ACCOUNT_ID+":inference-profile/*",
            ]
        ))

        # Add marketplace permissions for Claude models
        stack_constructs.add_bedrock_marketplace_permissions(self.extract_contract_type_info_fn.role)

        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Extract Contract Type Info",
            lambda_function=self.extract_contract_type_info_fn,
            payload=sfn.TaskInput.from_object({
                "ExecutionName.$": "$$.Execution.Name",
                "ImportJobId.$": "$.ImportJobId",
                "DocumentS3Key.$": "$.DocumentS3Key"
            }),
            payload_response_only=True,
        )

        # Grant S3 and DynamoDB permissions
        contract_bucket.grant_read(self.extract_contract_type_info_fn)
        import_jobs_table.grant_read_write_data(self.extract_contract_type_info_fn)

        # CDK Nag suppressions
        NagSuppressions.add_resource_suppressions(
            construct=self.extract_contract_type_info_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=[
                        "Action::s3:GetObject*",
                        "Action::s3:GetBucket*",
                        "Action::s3:List*",
                        "Resource::<ContractBucketFE738A79.Arn>/*",
                    ],
                    reason="S3 objects use dynamic keys for reference contract imports (contracts/<cognito-user-id>/<import-job-uuid>/<filename>).",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=[
                        "Resource::arn:aws:bedrock:*::foundation-model/*",
                        "Resource::arn:aws:bedrock:*:*:inference-profile/*",
                    ],
                    reason="Bedrock model access for extracting contract type metadata from reference contracts. Model ID is user-configurable via SSM parameter.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=["Resource::arn:aws:ssm:<AWS::Region>:<AWS::AccountId>:parameter/ContractAnalysis/*"],
                    reason="SSM parameters under /ContractAnalysis/ path for configuration.",
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions(
            self.extract_contract_type_info_fn,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="This is a tech debt, to update lambdas"
                )
            ]
        )