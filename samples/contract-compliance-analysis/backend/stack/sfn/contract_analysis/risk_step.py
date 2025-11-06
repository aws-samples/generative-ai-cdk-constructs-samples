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
    Duration,
    Aws,
    aws_lambda as lambda_,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression

import stack_constructs

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "contract_analysis", "risk_fn")


class RiskStep(Construct):
    """CDK construct for calculating contract risk
    """

    def __init__(
            self,
            scope: Construct,
            id: str,
            jobs_table: dynamodb.Table,
            clauses_table: dynamodb.Table,
            guidelines_table: dynamodb.Table,
            contract_types_table: dynamodb.Table,
            layers: list[lambda_.LayerVersion],
    ):
        super().__init__(scope, id)

        self.calculate_risk_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "CalculateRiskFunction",
            entry=LAMBDA_PATH,
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(5),
            memory_size=128,
            environment={
                "LOG_LEVEL": "DEBUG",
                "JOBS_TABLE": jobs_table.table_name,
                "CLAUSES_TABLE": clauses_table.table_name,
                "GUIDELINES_TABLE": guidelines_table.table_name,
                "CONTRACT_TYPES_TABLE": contract_types_table.table_name,
                "DEFAULT_HIGH_RISK_THRESHOLD": "0",
                "DEFAULT_MEDIUM_RISK_THRESHOLD": "1",
                "DEFAULT_LOW_RISK_THRESHOLD": "3",
            },
            layers=layers,
        )

        # Grant SSM Parameter Store permissions
        self.calculate_risk_fn.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "ssm:GetParameter",
            ],
            resources=[
                f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/ContractAnalysis/*",
            ]
        ))

        NagSuppressions.add_resource_suppressions(
            construct=self.calculate_risk_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used for SSM parameters under /ContractAnalysis/ path",
                    applies_to=["Resource::arn:aws:ssm:<AWS::Region>:<AWS::AccountId>:parameter/ContractAnalysis/*"],
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.calculate_risk_fn,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Python 3.12 is the most recent supported version",
                ),
            ],
        )
        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Assess Contract Risk",
            lambda_function=self.calculate_risk_fn,
            payload_response_only=True,
            result_path="$.Risk",
        )

        jobs_table.grant_read_write_data(self.calculate_risk_fn)
        clauses_table.grant_read_data(self.calculate_risk_fn)
        guidelines_table.grant_read_data(self.calculate_risk_fn)
        contract_types_table.grant_read_data(self.calculate_risk_fn)
