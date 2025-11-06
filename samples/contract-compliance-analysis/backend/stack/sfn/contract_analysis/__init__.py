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
    NestedStack,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_events as events,
    aws_logs as logs,
)
from cdk_nag import NagSuppressions, NagPackSuppression

import stack_constructs
from .validation_step import ValidationStep
from .preprocessing_step import PreprocessingStep
from .classification_step import ClassificationStep
from .evaluation_step import EvaluationStep
from .risk_step import RiskStep


class ContractAnalysisWorkflow(NestedStack):
    """Step Functions stack for contract analysis workflow"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        contract_bucket: s3.Bucket,
        guidelines_table: dynamodb.Table,
        clauses_table: dynamodb.Table,
        jobs_table: dynamodb.Table,
        contract_types_table: dynamodb.Table,
        event_bus: events.EventBus,
        **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda layers
        self.common_layer = lambda_python.PythonLayerVersion(
            self,
            "CommonLayer",
            entry=os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "common_layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12, lambda_.Runtime.PYTHON_3_13],
            compatible_architectures=[lambda_.Architecture.X86_64],

        )

        self.langchain_deps_layer = lambda_python.PythonLayerVersion(
            self,
            "LangchainDepsLayer",
            entry=os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "langchain_deps_layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12, lambda_.Runtime.PYTHON_3_13],
        )

        self.validation_step = ValidationStep(
            self,
            "ValidationStep",
            contract_types_table=contract_types_table,
            layers=[self.common_layer],
        )

        self.preprocessing_step = PreprocessingStep(
            self,
            "PreprocessingStep",
            contract_bucket=contract_bucket,
            clauses_table=clauses_table,
            layers=[self.langchain_deps_layer, self.common_layer],
        )

        self.notify_step = tasks.EventBridgePutEvents(
            self,
            "Notify Preprocessed Contract",
            entries=[
                tasks.EventBridgePutEventsEntry(
                    event_bus=event_bus,
                    source="contract-analysis",
                    detail_type="PreProcessedContract",
                    detail=sfn.TaskInput.from_object(
                        {
                            "JobId.$": "$.JobId",
                            "ContractTypeId.$": "$.ContractTypeId",
                            "OutputLanguage.$": "$.OutputLanguage",
                            "ClauseNumbers": sfn.JsonPath.list_at("$.ClauseNumbers"),
                            "AdditionalChecks": sfn.JsonPath.object_at(
                                "$.AdditionalChecks"
                            ),
                        }
                    ),
                )
            ],
            result_path=sfn.JsonPath.DISCARD,
        )

        self.classification = ClassificationStep(
            self,
            "ClassificationStep",
            guidelines_table=guidelines_table,
            clauses_table=clauses_table,
            contract_types_table=contract_types_table,
            layers=[self.langchain_deps_layer, self.common_layer],
        )

        classify_clauses_map = sfn.Map(
            self,
            "Guidelines: Classify Clauses",
            max_concurrency=1,
            items_path="$.ClauseNumbers",
            parameters={
                "JobId.$": "$.JobId",
                "ClauseNumber": sfn.JsonPath.string_at("$$.Map.Item.Value"),
                "ContractTypeId.$": "$$.Execution.Input.ContractTypeId",
                "OutputLanguage.$": "$$.Execution.Input.OutputLanguage"
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
            contract_types_table=contract_types_table,
            layers=[self.langchain_deps_layer, self.common_layer],
        )

        evaluate_clauses_map = sfn.Map(
            self,
            "Guidelines: Evaluate Clauses",
            max_concurrency=10,
            items_path="$.ClauseNumbers",
            parameters={
                "JobId.$": "$.JobId",
                "ClauseNumber": sfn.JsonPath.string_at("$$.Map.Item.Value"),
                "ContractTypeId.$": "$$.Execution.Input.ContractTypeId",
                "OutputLanguage.$": "$$.Execution.Input.OutputLanguage"
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
            contract_types_table=contract_types_table,
            layers=[self.langchain_deps_layer, self.common_layer],
        )

        state_machine_def = (
            self.validation_step.sfn_task
            .next(self.preprocessing_step.sfn_task)
            .next(self.notify_step)
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

        # Not all X-Ray actions support resource-level permissions
        # Reference: https://docs.aws.amazon.com/xray/latest/devguide/security_iam_service-with-iam.html
        NagSuppressions.add_resource_suppressions(
            construct=self.state_machine.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=["Resource::*"],
                    reason="Step Functions X-Ray tracing (xray:PutTraceSegments, xray:PutTelemetryRecords) and CloudWatch Logs delivery (logs:CreateLogDelivery, logs:GetLogDelivery, logs:UpdateLogDelivery, logs:DeleteLogDelivery, logs:ListLogDeliveries, logs:PutResourcePolicy, logs:DescribeResourcePolicies) do not support resource-level permissions per AWS service limitations.",
                ),
            ],
            apply_to_children=True,
        )

        # Suppress CDK-nag errors for LogRetention constructs
        # These are automatically created by CDK for Lambda functions
        NagSuppressions.add_stack_suppressions(
            stack=self,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="LogRetention construct requires AWSLambdaBasicExecutionRole managed policy for CloudWatch log operations",
                    applies_to=["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="LogRetention construct requires wildcard permissions for CloudWatch log group operations across different log groups",
                    applies_to=["Resource::*"],
                ),
            ],
        )
