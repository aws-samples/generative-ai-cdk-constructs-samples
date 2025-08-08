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
    aws_iam as iam,
    aws_dynamodb as dynamodb
)
from cdk_nag import NagSuppressions, NagPackSuppression

import stack_constructs
from stack.config.properties import AppProperties

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "fn-classify-clauses")


class ClassificationStep(Construct):
    """CDK construct for classifying contract clauses
    """

    def __init__(
            self,
            scope: Construct,
            id: str,
            guidelines_table: dynamodb.Table,
            clauses_table: dynamodb.Table,
            app_properties: AppProperties,
            layers: list[lambda_.LayerVersion],
    ):
        super().__init__(scope, id)

        prompt_vars = '%%'.join(
            [f"{key}={app_properties.get_value(key)}" for key in app_properties.get_all_property_names()])

        self.classify_clauses_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "ClassifyClauseFunction",
            entry=LAMBDA_PATH,
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(15),
            memory_size=512,
            environment={
                "LOG_LEVEL": "INFO",
                "GUIDELINES_TABLE_NAME": guidelines_table.table_name,
                "CLAUSES_TABLE_NAME": clauses_table.table_name,
                "PROMPT_VARS": prompt_vars,
                "BEDROCK_MAX_CONCURRENCY": "3",
            },
            layers=layers,
        )

        guidelines_table.grant_read_data(self.classify_clauses_fn)
        clauses_table.grant_read_write_data(self.classify_clauses_fn)

        self.classify_clauses_fn.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
            ],
            resources=[
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*:"+Aws.ACCOUNT_ID+":inference-profile/*",
            ]
        ))

        NagSuppressions.add_resource_suppressions(
            construct=self.classify_clauses_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because to support multiple models",
                ),
            ],
            apply_to_children=True,
        )

        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Classify Clause",
            lambda_function=self.classify_clauses_fn,
            payload_response_only=True,
            task_timeout=sfn.Timeout.duration(Duration.minutes(90)),
            retry_on_service_exceptions=False
        )

        # Reference: https://docs.aws.amazon.com/step-functions/latest/dg/bp-lambda-serviceexception.html
        self.sfn_task.add_retry(
            errors=['Lambda.ServiceException', 'Lambda.AWSLambdaException', 'Lambda.SdkClientException',
                    'Lambda.ClientExecutionTimeoutException', 'Lambda.Unknown'],
            max_attempts=5,
            interval=Duration.seconds(2),
        )
