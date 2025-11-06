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

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "contract_analysis", "validation_fn")


class ValidationStep(Construct):
    """CDK construct for validating contract type
    """

    def __init__(
            self,
            scope: Construct,
            id: str,
            contract_types_table: dynamodb.Table,
            layers: list[lambda_.LayerVersion],
    ):
        super().__init__(scope, id)

        self.validate_contract_type_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "ValidateContractTypeFunction",
            entry=LAMBDA_PATH,
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(1),
            memory_size=128,
            environment={
                "LOG_LEVEL": "INFO",
                "CONTRACT_TYPES_TABLE": contract_types_table.table_name,
            },
            layers=layers,
        )

        contract_types_table.grant_read_data(self.validate_contract_type_fn)

        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Validate Contract Type",
            lambda_function=self.validate_contract_type_fn,
            payload_response_only=True,
            task_timeout=sfn.Timeout.duration(Duration.minutes(2)),
            retry_on_service_exceptions=False
        )

        # Add retry for service exceptions
        self.sfn_task.add_retry(
            errors=['Lambda.ServiceException', 'Lambda.AWSLambdaException', 'Lambda.SdkClientException',
                    'Lambda.ClientExecutionTimeoutException', 'Lambda.Unknown'],
            max_attempts=3,
            interval=Duration.seconds(2),
        )

        NagSuppressions.add_resource_suppressions(
            self.validate_contract_type_fn,
            suppressions=[
                NagPackSuppression(id="AwsSolutions-L1", reason="This is a tech debt, to update lambdas")
            ]
        )
