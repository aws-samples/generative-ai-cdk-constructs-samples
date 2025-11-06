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

from constructs import Construct
from aws_cdk import (
    NestedStack,
    Duration,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_logs as logs,
)
from cdk_nag import NagSuppressions, NagPackSuppression

from .initialize_import_step import InitializeImportStep
from .extract_contract_type_info_step import ExtractContractTypeInfoStep
from .extract_clause_types_step import ExtractClauseTypesStep
from .finalize_import_step import FinalizeImportStep


class ContractImportWorkflow(NestedStack):
    """Import State Machine for contract type import workflow"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        contract_bucket: s3.Bucket,
        contract_types_table: dynamodb.Table,
        guidelines_table: dynamodb.Table,
        import_jobs_table: dynamodb.Table,
        common_layer: lambda_.LayerVersion,
        langchain_deps_layer: lambda_.LayerVersion,
        **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        layers = [common_layer, langchain_deps_layer]

        # Create step function steps
        self.initialize_step = InitializeImportStep(
            self,
            "InitializeImportStep",
            contract_bucket=contract_bucket,
            import_jobs_table=import_jobs_table,
            layers=layers,
        )

        self.extract_contract_type_info_step = ExtractContractTypeInfoStep(
            self,
            "ExtractContractTypeInfoStep",
            contract_bucket=contract_bucket,
            import_jobs_table=import_jobs_table,
            layers=layers,
        )

        self.extract_clause_types_step = ExtractClauseTypesStep(
            self,
            "ExtractClauseTypesStep",
            contract_bucket=contract_bucket,
            import_jobs_table=import_jobs_table,
            layers=layers,
        )

        self.finalize_step = FinalizeImportStep(
            self,
            "FinalizeImportStep",
            contract_types_table=contract_types_table,
            guidelines_table=guidelines_table,
            import_jobs_table=import_jobs_table,
            layers=layers,
        )

        # Create the state machine definition
        definition = (
            self.initialize_step.sfn_task
            .next(self.extract_contract_type_info_step.sfn_task)
            .next(self.extract_clause_types_step.sfn_task)
            .next(self.finalize_step.sfn_task)
        )

        # Create CloudWatch log group for the state machine
        self.state_machine_logs = logs.LogGroup(
            self,
            "ContractImportWorkflowLogGroup",
            retention=logs.RetentionDays.ONE_MONTH,
        )

        # Create the state machine
        self.state_machine = sfn.StateMachine(
            self,
            "ContractImportWorkflow",
            definition=definition,
            timeout=Duration.hours(1),
            logs=sfn.LogOptions(
                destination=self.state_machine_logs,
                level=sfn.LogLevel.ALL,
            ),
        )

        # Add CDK Nag suppressions for the state machine
        NagSuppressions.add_resource_suppressions(
            self.state_machine,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-SF2",
                    reason="State machine has CloudWatch logging enabled for monitoring import workflows"
                )
            ]
        )

        # Add CDK Nag suppressions for IAM wildcard permissions
        NagSuppressions.add_resource_suppressions(
            self.state_machine.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=[
                        "Resource::<InitializeImportStepInitializeImportFunction45293B21.Arn>:*",
                        "Resource::<ExtractContractTypeInfoStepExtractContractTypeInfoFunction44936E90.Arn>:*",
                        "Resource::<ExtractClauseTypesStepExtractClauseTypesFunction053A6E14.Arn>:*",
                        "Resource::<FinalizeImportStepFinalizeImportFunctionA2451D16.Arn>:*",
                    ],
                    reason="Step Functions requires wildcard suffix on Lambda ARNs to invoke any version or alias of the functions.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=["Resource::*"],
                    reason="Step Functions CloudWatch Logs delivery (logs:CreateLogDelivery, logs:GetLogDelivery, logs:UpdateLogDelivery, logs:DeleteLogDelivery, logs:ListLogDeliveries, logs:PutResourcePolicy, logs:DescribeResourcePolicies) does not support resource-level permissions per AWS service limitations.",
                ),
            ]
        )