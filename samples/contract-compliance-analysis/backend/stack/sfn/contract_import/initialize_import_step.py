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
    aws_s3 as s3,
)
from cdk_nag import NagSuppressions, NagPackSuppression

import stack_constructs

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "contract_import", "initialize_import_fn")


class InitializeImportStep(Construct):
    """CDK construct for import initialization step"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        contract_bucket: s3.Bucket,
        import_jobs_table: dynamodb.Table,
        layers: list[lambda_.LayerVersion],
    ):
        super().__init__(scope, id)

        self.initialize_import_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "InitializeImportFunction",
            entry=LAMBDA_PATH,
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(5),
            memory_size=128,
            environment={
                "LOG_LEVEL": "INFO",
                "IMPORT_JOBS_TABLE_NAME": import_jobs_table.table_name,
                "CONTRACT_BUCKET_NAME": contract_bucket.bucket_name,
            },
            layers=layers,
        )

        self.sfn_task = tasks.LambdaInvoke(
            self,
            "Initialize Import",
            lambda_function=self.initialize_import_fn,
            payload=sfn.TaskInput.from_object({
                "ExecutionName.$": "$$.Execution.Name",
                "ImportJobId.$": "$.ImportJobId",
                "DocumentS3Key.$": "$.DocumentS3Key",
                "Description.$": "$.Description"
            }),
            payload_response_only=True,
        )

        # Grant S3 and DynamoDB permissions
        contract_bucket.grant_read(self.initialize_import_fn)
        import_jobs_table.grant_read_write_data(self.initialize_import_fn)

        # CDK Nag suppressions
        NagSuppressions.add_resource_suppressions(
            self.initialize_import_fn,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="This is a tech debt, to update lambdas"
                )
            ]
        )