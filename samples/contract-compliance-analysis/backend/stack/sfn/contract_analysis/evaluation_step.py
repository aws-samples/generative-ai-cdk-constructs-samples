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
    aws_dynamodb as dynamodb,
    aws_iam as iam,
)
from cdk_nag import NagSuppressions, NagPackSuppression

import stack_constructs

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "contract_analysis", "evaluation_fn")


class EvaluationStep(Construct):
    """CDK construct for evaluating contract clauses against guidelines rules
    """

    def __init__(
            self,
            scope: Construct,
            id: str,
            layers: list[lambda_.LayerVersion],
            guidelines_table=dynamodb.Table,
            clauses_table=dynamodb.Table,
            contract_types_table=dynamodb.Table,
            **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.evaluate_clauses_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "EvaluateClauseFunction",
            entry=LAMBDA_PATH,
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(15),
            memory_size=512,
            environment={
                "LOG_LEVEL": "INFO",
                "CLAUSES_TABLE_NAME": clauses_table.table_name,
                "GUIDELINES_TABLE_NAME": guidelines_table.table_name,
                "CONTRACT_TYPES_TABLE": contract_types_table.table_name,
                "DEFAULT_LLM_MODEL_ID": "amazon.nova-pro-v1:0",
                "DEFAULT_COMPANY_NAME": "AnyCompany",
                "DEFAULT_CONTRACT_TYPE": "service contract",
                "DEFAULT_COMPANY_PARTY_TYPE": "Contractor/Customer",
                "DEFAULT_OTHER_PARTY_TYPE": "Service Provider",
            },
            layers=layers,
        )
        clauses_table.grant_read_write_data(self.evaluate_clauses_fn)
        guidelines_table.grant_read_data(self.evaluate_clauses_fn)
        contract_types_table.grant_read_data(self.evaluate_clauses_fn)

        # Grant SSM Parameter Store permissions
        self.evaluate_clauses_fn.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "ssm:GetParameter",
            ],
            resources=[
                f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/ContractAnalysis/*",
            ]
        ))

        self.evaluate_clauses_fn.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
            ],
            resources=[
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*:"+Aws.ACCOUNT_ID+":inference-profile/*",
            ]
        ))

        # Add marketplace permissions for Claude models
        stack_constructs.add_bedrock_marketplace_permissions(self.evaluate_clauses_fn.role)

        NagSuppressions.add_resource_suppressions(
            construct=self.evaluate_clauses_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=[
                        "Resource::arn:aws:bedrock:*::foundation-model/*",
                        "Resource::arn:aws:bedrock:*:*:inference-profile/*",
                    ],
                    reason="Lambda requires access to Bedrock foundation models and cross-region inference profiles. Model IDs are user-configurable via SSM parameter /ContractAnalysis/ContractEvaluation/LanguageModelId and cannot be predetermined at deployment.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=["Resource::arn:aws:ssm:<AWS::Region>:<AWS::AccountId>:parameter/ContractAnalysis/*"],
                    reason="SSM parameters under /ContractAnalysis/ path for configuration.",
                ),
            ],
            apply_to_children=True,
        )

        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Evaluate Clause",
            lambda_function=self.evaluate_clauses_fn,
            payload_response_only=True,
            result_path="$.Evaluation",
            task_timeout=sfn.Timeout.duration(Duration.minutes(90)),
            retry_on_service_exceptions=False,
        )

        # Reference: https://docs.aws.amazon.com/step-functions/latest/dg/bp-lambda-serviceexception.html
        self.sfn_task.add_retry(
            errors=['Lambda.ServiceException', 'Lambda.AWSLambdaException', 'Lambda.SdkClientException',
                    'Lambda.ClientExecutionTimeoutException', 'Lambda.Unknown'],
            max_attempts=5,
            interval=Duration.seconds(2),
        )

        NagSuppressions.add_resource_suppressions(
            self.evaluate_clauses_fn,
            suppressions=[
                NagPackSuppression(id="AwsSolutions-L1", reason="This is a tech debt, to update lambdas")
            ]
        )
