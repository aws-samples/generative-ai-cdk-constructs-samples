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
    aws_s3 as s3,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    Duration,
    Stack,
)
from cdk_nag import NagSuppressions, NagPackSuppression
from constructs import Construct
from .aws_lambda import PythonFunctionConstruct

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "fn_preprocess")


class PreprocessingStep(Construct):
    """CDK construct for Preprocessing"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        inference_bucket: s3.Bucket,
        questionnaire_table: dynamodb.Table,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.preprocess_fn = PythonFunctionConstruct(
            self,
            "PreprocessingFunction",
            entry=os.path.join(
                os.path.dirname(__file__), "..", "lambdas", "preprocess_fn"
            ),
            index="app/index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.minutes(15),
            memory_size=4096,
            environment={
                "LOG_LEVEL": "INFO",
                "QUESTIONNAIRE_TABLE_NAME": questionnaire_table.table_name,
            },
        )

        self.preprocess_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                ],
                resources=[
                    f"arn:aws:bedrock:{Stack.of(self).region}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
                ],
            )
        )

        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Preprocess Input",
            lambda_function=self.preprocess_fn,
            payload=sfn.TaskInput.from_object(
                {
                    "ExecutionName.$": "$$.Execution.Name",
                    "document_s3_path.$": "$.document_s3_path",
                }
            ),
            payload_response_only=True,
        )

        inference_bucket.grant_read(self.preprocess_fn)
        questionnaire_table.grant_read_write_data(self.preprocess_fn)

        NagSuppressions.add_resource_suppressions(
            construct=self.preprocess_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because object naming is not standardized",
                ),
            ],
            apply_to_children=True,
        )
