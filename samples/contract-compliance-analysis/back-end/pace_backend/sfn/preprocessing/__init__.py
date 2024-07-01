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
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
)
from cdk_nag import NagSuppressions, NagPackSuppression

import pace_constructs as pace

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "fn-preprocess-contract")


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

        self.preprocess_contract_fn = pace.PACEPythonFunction(
            self,
            "PreprocessContractFunction",
            entry=LAMBDA_PATH,
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.minutes(5),
            memory_size=128,
            environment={
                "LOG_LEVEL": "DEBUG",
                "CLAUSES_TABLE_NAME": clauses_table.table_name,
            },
            layers=layers,
        )

        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Preprocess Contract",
            lambda_function=self.preprocess_contract_fn,
            payload=sfn.TaskInput.from_object({
                "ExecutionName.$": "$$.Execution.Name",
                "document_s3_path.$": "$.document_s3_path"
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
                "arn:aws:bedrock:*::foundation-model/anthropic*"
            ]
        ))

        NagSuppressions.add_resource_suppressions(
            construct=self.preprocess_contract_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because object naming is not standardized",
                ),
            ],
            apply_to_children=True,
        )
