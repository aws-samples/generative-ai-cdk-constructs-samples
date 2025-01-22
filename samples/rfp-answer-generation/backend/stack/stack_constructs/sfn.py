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

from aws_cdk import (
    Duration,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
    aws_s3 as s3,
    aws_stepfunctions as sfn,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression

from .sfn_step_preprocess import PreprocessingStep
from .sfn_step_answer_question import AnswerQuestionStep
from .sfn_step_record_status import RecordStatusStep


class StepFunctionsConstruct(Construct):

    def __init__(
        self,
        scope: Construct,
        id: str,
        inference_bucket: s3.Bucket,
        jobs_table: dynamodb.Table,
        questionnaire_table: dynamodb.Table,
        faq_knowledge_base_id: str,
        docs_knowledge_base_id: str,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.preprocessing_step = PreprocessingStep(
            self,
            "PreprocessingStep",
            inference_bucket=inference_bucket,
            questionnaire_table=questionnaire_table,
        )

        self.question_answering_step = AnswerQuestionStep(
            self,
            "AnswerQuestionStep",
            questionnaire_table=questionnaire_table,
            faq_knowledge_base_id=faq_knowledge_base_id,
            docs_knowledge_base_id=docs_knowledge_base_id,
        )

        respond_questions_map = sfn.Map(
            self,
            "Question Answering Loop",
            max_concurrency=1,
            items_path="$.QuestionNumbers",
            parameters={
                "JobId.$": "$.JobId",
                "QuestionNumber": sfn.JsonPath.string_at("$$.Map.Item.Value"),
            },
            result_selector={"Status": "OK"},
            result_path="$.QuestionAnsweringResult",
        )

        self.record_status_step = RecordStatusStep(
            self,
            "RecordStatusStep",
            jobs_table=jobs_table,
        )

        self.preprocessing_step.sfn_task.add_catch(
            self.record_status_step.failure_sfn_task
        )
        respond_questions_map.add_catch(self.record_status_step.failure_sfn_task)
        # self.question_answering_step.sfn_task.add_catch(self.record_status_step.sfn_task)

        state_machine_def = self.preprocessing_step.sfn_task.next(
            respond_questions_map.item_processor(self.question_answering_step.sfn_task)
        ).next(self.record_status_step.success_sfn_task)

        self.state_machine_logs = logs.LogGroup(self, "StateMachineLogGroup")

        self.state_machine = sfn.StateMachine(
            self,
            "QuestionAnsweringStateMachine",
            definition=state_machine_def,
            logs=sfn.LogOptions(
                destination=self.state_machine_logs, level=sfn.LogLevel.ALL
            ),
            state_machine_type=sfn.StateMachineType.STANDARD,
            timeout=Duration.hours(48),
            tracing_enabled=True,
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.state_machine.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard used because to support multiple function versions",
                ),
            ],
            apply_to_children=True,
        )
