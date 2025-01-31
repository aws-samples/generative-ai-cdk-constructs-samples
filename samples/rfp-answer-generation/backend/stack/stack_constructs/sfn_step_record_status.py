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
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    Duration,
)
from cdk_nag import NagSuppressions, NagPackSuppression
from constructs import Construct
from .aws_lambda import PythonFunctionConstruct


class RecordStatusStep(Construct):
    """CDK construct for Recording Execution Status"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        jobs_table: dynamodb.Table,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.record_status_fn = PythonFunctionConstruct(
            self,
            "RecordStatusFunction",
            entry=os.path.join(
                os.path.dirname(__file__), "..", "lambdas", "record_status_fn"
            ),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.minutes(15),
            memory_size=4096,
            environment={
                "LOG_LEVEL": "INFO",
                "JOBS_TABLE_NAME": jobs_table.table_name,
            },
        )

        self.success_sfn_task = tasks.LambdaInvoke(
            self,
            "Record Status Succeeeded",
            lambda_function=self.record_status_fn,
            payload=sfn.TaskInput.from_object(
                {
                    "ExecutionArn.$": "$$.Execution.Id",
                    "Status": "SUCCEEDED",
                }
            ),
            payload_response_only=True,
        )

        self.failure_sfn_task = tasks.LambdaInvoke(
            self,
            "Record Status Failed",
            lambda_function=self.record_status_fn,
            payload=sfn.TaskInput.from_object(
                {
                    "ExecutionArn.$": "$$.Execution.Id",
                    "Status": "FAILED",
                }
            ),
            payload_response_only=True,
        )

        jobs_table.grant_read_write_data(self.record_status_fn)
