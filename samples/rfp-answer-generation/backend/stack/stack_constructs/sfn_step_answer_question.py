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
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    Duration,
    Stack,
)
from cdk_nag import NagSuppressions, NagPackSuppression
from constructs import Construct
from .aws_lambda import PythonFunctionConstruct


class AnswerQuestionStep(Construct):

    def __init__(
        self,
        scope: Construct,
        id: str,
        questionnaire_table: dynamodb.Table,
        faq_knowledge_base_id: str,
        docs_knowledge_base_id: str,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.answer_question_fn = PythonFunctionConstruct(
            self,
            "AnswerQuestionFunction",
            entry=os.path.join(
                os.path.dirname(__file__), "..", "lambdas", "answer_question_fn"
            ),
            index="app/index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "LOG_LEVEL": "INFO",
                "QUESTIONNAIRE_TABLE": questionnaire_table.table_name,
                "FAQ_KNOWLEDGE_BASE_ID": faq_knowledge_base_id,
                "DOC_KNOWLEDGE_BASE_ID": docs_knowledge_base_id,
            },
        )

        questionnaire_table.grant_read_write_data(self.answer_question_fn)
        self.answer_question_fn.role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                ],
                resources=[
                    f"arn:aws:bedrock:{Stack.of(self).region}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
                    f"arn:aws:bedrock:{Stack.of(self).region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                ],
            )
        )

        self.answer_question_fn.role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:Retrieve",
                ],
                resources=[
                    f"arn:aws:bedrock:{Stack.of(self).region}:{Stack.of(self).account}:knowledge-base/{faq_knowledge_base_id}",
                    f"arn:aws:bedrock:{Stack.of(self).region}:{Stack.of(self).account}:knowledge-base/{docs_knowledge_base_id}",
                ],
            )
        )

        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Respond Question",
            lambda_function=self.answer_question_fn,
            payload_response_only=True,
            task_timeout=sfn.Timeout.duration(Duration.minutes(90)),
        )
