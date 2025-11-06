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

from aws_cdk import (
    Duration,
    Stack,
    aws_bedrockagentcore as bedrockagentcore,
    aws_dynamodb as ddb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_s3 as s3,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression
import os

from check_legislation.sfn.check_legislation import CheckLegislationStep


class CheckLegislationWorkflow(Construct):

    def __init__(
        self,
        scope,
        id,
        agent_runtime: bedrockagentcore.CfnRuntime,
        agent_role: iam.IRole,
        clauses_table: ddb.ITable,
        jobs_table: ddb.ITable,
        contract_bucket: s3.IBucket,
    ):
        super().__init__(scope, id)

        powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            f"arn:aws:lambda:{Stack.of(self).region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-x86_64:21",
        )

        # Record legislation workflow execution ARN in the job
        record_execution_task = tasks.DynamoUpdateItem(
            self,
            "RecordLegislationExecution",
            table=jobs_table,
            key={
                "id": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.JobId")
                )
            },
            update_expression="SET legislation_check_execution_arn = :exec_arn",
            expression_attribute_values={
                ":exec_arn": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$$.Execution.Id")
                )
            },
            result_path=sfn.JsonPath.DISCARD,
        )

        check_legislation_step = CheckLegislationStep(
            self,
            "CheckLegislationStep",
            agent_runtime=agent_runtime,
            agent_role=agent_role,
            clauses_table=clauses_table,
            contract_bucket=contract_bucket,
        )

        check_legislation_map = sfn.Map(
            self,
            "Legislation: Evaluate Clauses",
            max_concurrency=1,
            items_path="$.ClauseNumbers",
            item_selector={
                "JobId.$": "$.JobId",
                "OutputLanguage.$": "$.OutputLanguage",
                "ClauseNumber": sfn.JsonPath.string_at("$$.Map.Item.Value"),
                "LegislationCheck": sfn.JsonPath.object_at(
                    "$.AdditionalChecks.legislationCheck"
                ),
            },
            result_selector={"Status": "OK"},
            result_path="$.LegislationCheckResult",
        )

        # Lambda to record legislation compliance
        record_compliance_fn = lambda_.Function(
            self,
            "RecordLegislationComplianceFn",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(
                os.path.join(
                    os.path.dirname(__file__),
                    "check_legislation",
                    "calculate_legislation_compliance_fn",
                )
            ),
            timeout=Duration.minutes(1),
            layers=[powertools_layer],
            environment={
                "CLAUSES_TABLE": clauses_table.table_name,
                "JOBS_TABLE": jobs_table.table_name,
            },
        )

        # Grant permissions
        clauses_table.grant_read_data(record_compliance_fn)
        jobs_table.grant_read_write_data(record_compliance_fn)

        # Step Functions task to record legislation compliance
        record_compliance_task = tasks.LambdaInvoke(
            self,
            "RecordLegislationCompliance",
            lambda_function=record_compliance_fn,
            payload=sfn.TaskInput.from_object(
                {
                    "JobId": sfn.JsonPath.string_at("$.JobId"),
                    "ClausesTableName": clauses_table.table_name,
                }
            ),
            result_path="$.ComplianceResult",
        )

        # Create CloudWatch log group for Step Function
        log_group = logs.LogGroup(
            self,
            "CheckLegislationSMLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
        )

        self.state_machine = sfn.StateMachine(
            self,
            "CheckLegislationSM",
            definition_body=sfn.DefinitionBody.from_chainable(
                record_execution_task.next(
                    check_legislation_map.item_processor(
                        check_legislation_step.sfn_task
                    )
                ).next(record_compliance_task)
            ),
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ALL,
            ),
        )

        NagSuppressions.add_resource_suppressions(
            self.state_machine,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-SF2",
                    reason="We are arbitrarily choosing to not have x-ray traces, you should evaluate if you need them.",
                ),
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.state_machine.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=[
                        {"regex": "/^Resource::<CheckLegislationSfn.*\\.Arn>:\\*$/"},
                    ],
                    reason="State machine needs to invoke Lambda functions with any version",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=["Resource::*"],
                    reason="Needs this to be able to send ALL logs to cloudwatch",
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions(
            record_compliance_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                    ],
                    reason="Lambda function uses AWS managed policy for basic execution",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=["Resource::<JobsTable1970BC16.Arn>/index/*"],
                    reason="Function needs access to Jobs table GSI",
                ),
            ],
            apply_to_children=True,
        )
