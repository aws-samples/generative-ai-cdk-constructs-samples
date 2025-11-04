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
import boto3
import json
import os
from typing import Optional
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
  from mypy_boto3_stepfunctions.client import SFNClient
  from mypy_boto3_stepfunctions.type_defs import DescribeExecutionOutputTypeDef
else:
  SFNClient = object
  DescribeExecutionOutputTypeDef = object

from aws_lambda_powertools import Logger

from model import Workflow
from schema import StartWorkflowRequest
from repository import WorkflowsRepository

logger = Logger()

class StepFunctionsWorkflowsRepository(WorkflowsRepository):
  def __init__(self, state_machine_arn: str, sfn_client: Optional[SFNClient] = None):
    self.state_machine_arn = state_machine_arn
    self.sfn_client: SFNClient = sfn_client or boto3.client("stepfunctions", region_name=os.getenv("AWS_REGION", "us-east-1"))

  def start_execution(self, input_data: StartWorkflowRequest) -> str:
    logger.info(f'Starting state machine {self.state_machine_arn} with input {input_data}')

    result = self.sfn_client.start_execution(
      stateMachineArn=self.state_machine_arn,
      input=input_data.model_dump_json(by_alias=True)
    )

    if 'ResponseMetadata' not in result or result['ResponseMetadata']['HTTPStatusCode'] != 200:
      raise AssertionError
    return result['executionArn']

  def to_job_id(self, execution_id: str) -> str:
    return execution_id.split(':')[-1]

  def to_execution_id(self, job_id: str) -> str:
    return f"{self.state_machine_arn.replace('stateMachine', 'execution')}:{job_id}"

  def get_state_machine_execution_details(self, execution_id: str) -> Workflow | None:
    try:
      result: DescribeExecutionOutputTypeDef = self.sfn_client.describe_execution(executionArn=execution_id)

      return Workflow(
        id=execution_id,
        state_machine_id=result["stateMachineArn"],
        status=result["status"],
        start_date=result["startDate"],
        end_date=result.get("stopDate", None),
      )
    except Exception as e:
      logger.exception(e)
      return None

