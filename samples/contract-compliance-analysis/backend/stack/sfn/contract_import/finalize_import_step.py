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
    aws_dynamodb as dynamodb,
)
from cdk_nag import NagSuppressions, NagPackSuppression

import stack_constructs

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "contract_import", "finalize_import_fn")


class FinalizeImportStep(Construct):
    """CDK construct for import finalization step"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        contract_types_table: dynamodb.Table,
        guidelines_table: dynamodb.Table,
        import_jobs_table: dynamodb.Table,
        layers: list[lambda_.LayerVersion],
    ):
        super().__init__(scope, id)

        self.finalize_import_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "FinalizeImportFunction",
            entry=LAMBDA_PATH,
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "LOG_LEVEL": "INFO",
                "CONTRACT_TYPES_TABLE_NAME": contract_types_table.table_name,
                "GUIDELINES_TABLE_NAME": guidelines_table.table_name,
                "IMPORT_JOBS_TABLE_NAME": import_jobs_table.table_name,
            },
            layers=layers,
        )

        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Finalize Import",
            lambda_function=self.finalize_import_fn,
            payload=sfn.TaskInput.from_object({
                "ExecutionName.$": "$$.Execution.Name",
                "ImportJobId.$": "$.ImportJobId",
                "ContractTypeInfo.$": "$.ContractTypeInfo",
                "ClauseTypes.$": "$.ClauseTypes"
            }),
            payload_response_only=True,
        )

        # Grant DynamoDB permissions
        contract_types_table.grant_read_write_data(self.finalize_import_fn)
        guidelines_table.grant_read_write_data(self.finalize_import_fn)
        import_jobs_table.grant_read_write_data(self.finalize_import_fn)

        # CDK Nag suppressions
        NagSuppressions.add_resource_suppressions(
            self.finalize_import_fn,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="This is a tech debt, to update lambdas"
                )
            ]
        )