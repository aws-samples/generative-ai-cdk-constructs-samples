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

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "contract_analysis", "preprocessing_fn")


class PreprocessingStep(Construct):
    """CDK construct for contract preprocessing
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        contract_bucket: s3.Bucket,
        clauses_table: dynamodb.Table,
        layers: list[lambda_.LayerVersion],
    ):
        super().__init__(scope, id)

        self.preprocess_contract_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "PreprocessContractFunction",
            entry=LAMBDA_PATH,
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(15),
            memory_size=128,
            environment={
                "LOG_LEVEL": "INFO",
                "CLAUSES_TABLE_NAME": clauses_table.table_name,
                "DEFAULT_LLM_MODEL_ID": "amazon.nova-pro-v1:0",
            },
            layers=layers,
        )

        # Grant SSM Parameter Store permissions
        self.preprocess_contract_fn.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "ssm:GetParameter",
            ],
            resources=[
                f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/ContractAnalysis/*",
            ]
        ))

        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Preprocess Contract",
            lambda_function=self.preprocess_contract_fn,
            payload=sfn.TaskInput.from_object({
                "ExecutionName.$": "$$.Execution.Name",
                "document_s3_path.$": "$.document_s3_path",
                "ContractTypeId.$": "$.ContractTypeId",
                "OutputLanguage.$": "$.OutputLanguage",
                "AdditionalChecks": sfn.JsonPath.object_at("$.AdditionalChecks")
            }),
            payload_response_only=True,
        )

        contract_bucket.grant_read(self.preprocess_contract_fn)
        clauses_table.grant_read_write_data(self.preprocess_contract_fn)

        self.preprocess_contract_fn.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
            ],
            resources=[
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*:"+Aws.ACCOUNT_ID+":inference-profile/*",
            ]
        ))

        # Add marketplace permissions for Claude models
        stack_constructs.add_bedrock_marketplace_permissions(self.preprocess_contract_fn.role)

        NagSuppressions.add_resource_suppressions(
            construct=self.preprocess_contract_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=[
                        "Action::s3:GetObject*",
                        "Action::s3:GetBucket*",
                        "Action::s3:List*",
                        "Resource::<ContractBucketFE738A79.Arn>/*",
                    ],
                    reason="S3 objects use dynamic keys (contracts/<cognito-user-id>/<job-uuid>/<filename>). User IDs and job IDs are runtime-generated.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=[
                        "Resource::arn:aws:bedrock:*::foundation-model/*",
                        "Resource::arn:aws:bedrock:*:*:inference-profile/*",
                    ],
                    reason="Bedrock model access for contract preprocessing. Model ID is user-configurable via SSM parameter /ContractAnalysis/ContractPreprocessing/LanguageModelId.",
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
            self.preprocess_contract_fn,
            suppressions=[
                NagPackSuppression(id="AwsSolutions-L1", reason="This is a tech debt, to update lambdas")
            ]
        )
