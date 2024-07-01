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
    NestedStack,
    Duration,
    aws_s3 as s3,
    aws_logs as logs,
    aws_dynamodb as dynamodb,
    aws_stepfunctions as sfn,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
)

from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression

from stack.config.properties import AppProperties
from .preprocessing import PreprocessingStep
from .classification import ClassificationStep
from .evaluation import EvaluationStep
from .risk import RiskStep

from cdklabs.generative_ai_cdk_constructs import LangchainCommonDepsLayer


class StepFunctionsStack(NestedStack):

    def __init__(
            self,
            scope: Construct,
            id: str,
            contract_bucket: s3.Bucket,
            guidelines_table: dynamodb.Table,
            clauses_table: dynamodb.Table,
            jobs_table: dynamodb.Table,
            app_properties: AppProperties,
            **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.langchain_deps_layer = LangchainCommonDepsLayer(
            self,
            "LangChainDependenciesLayer",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64
        ).layer

        self.common_layer = lambda_python.PythonLayerVersion(
            self,
            'CommonLayer',
            entry=os.path.join(os.path.dirname(__file__), "common-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
        )

        self.preprocessing_step = PreprocessingStep(
            self,
            "PreprocessingStep",
            contract_bucket=contract_bucket,
            clauses_table=clauses_table,
            app_properties=app_properties,
            layers=[self.langchain_deps_layer, self.common_layer],
        )

        self.classification = ClassificationStep(
            self,
            "ClassificationStep",
            guidelines_table=guidelines_table,
            clauses_table=clauses_table,
            app_properties=app_properties,
            layers=[self.langchain_deps_layer, self.common_layer],
        )

        classify_clauses_map = sfn.Map(
            self,
            "Classify Contract Clauses Loop",
            max_concurrency=1,
            items_path="$.ClauseNumbers",
            parameters={
                "JobId.$": "$.JobId",
                "ClauseNumber": sfn.JsonPath.string_at("$$.Map.Item.Value")
            },
            result_selector={
                "Status": "OK"
            },
            result_path="$.ClassificationResult"
        )

        self.evaluation_step = EvaluationStep(
            self,
            "EvaluationStep",
            guidelines_table=guidelines_table,
            clauses_table=clauses_table,
            app_properties=app_properties,
            layers=[self.langchain_deps_layer, self.common_layer],
        )

        evaluate_clauses_map = sfn.Map(
            self,
            "Evaluate Contract Clauses Loop",
            max_concurrency=10,
            items_path="$.ClauseNumbers",
            parameters={
                "JobId.$": "$.JobId",
                "ClauseNumber": sfn.JsonPath.string_at("$$.Map.Item.Value")
            },
            result_selector={
                "Status": "OK"
            },
            result_path="$.EvaluationResult"
        )

        self.risk_step = RiskStep(
            self,
            "RiskCalculationStep",
            guidelines_table=guidelines_table,
            clauses_table=clauses_table,
            jobs_table=jobs_table,
            app_properties=app_properties,
            layers=[self.common_layer],
        )

        state_machine_def = (
            self.preprocessing_step.sfn_task
            .next(classify_clauses_map.iterator(self.classification.sfn_task))
            .next(evaluate_clauses_map.iterator(self.evaluation_step.sfn_task))
            .next(self.risk_step.sfn_task)
        )

        self.state_machine_logs = logs.LogGroup(
            self,
            "StateMachineLogGroup"
        )

        self.state_machine = sfn.StateMachine(
            self,
            "ContractAnalysisStateMachine",
            definition=state_machine_def,
            logs=sfn.LogOptions(
                destination=self.state_machine_logs,
                level=sfn.LogLevel.ALL
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
