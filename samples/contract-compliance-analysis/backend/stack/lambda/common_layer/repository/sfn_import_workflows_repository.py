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
import uuid
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
  from mypy_boto3_stepfunctions.client import SFNClient
  from mypy_boto3_stepfunctions.type_defs import DescribeExecutionOutputTypeDef
else:
  SFNClient = object
  DescribeExecutionOutputTypeDef = object

from aws_lambda_powertools import Logger

from model import Workflow

logger = Logger()


class ImportWorkflowRequest:
  """Request model for starting import workflow"""
  def __init__(self, document_s3_key: str, import_job_id: str, description: Optional[str] = None):
    self.document_s3_key = document_s3_key
    self.import_job_id = import_job_id
    self.description = description or ""

  def model_dump_json(self, by_alias: bool = True) -> str:
    """Convert to JSON for Step Functions input"""
    return json.dumps({
      "DocumentS3Key": self.document_s3_key,
      "ImportJobId": self.import_job_id,
      "Description": self.description
    })


class StepFunctionsImportWorkflowsRepository:
  """Repository for managing import workflow executions"""

  def __init__(self, state_machine_arn: str, sfn_client: Optional[SFNClient] = None):
    self.state_machine_arn = state_machine_arn
    self.sfn_client: SFNClient = sfn_client or boto3.client("stepfunctions", region_name=os.getenv("AWS_REGION", "us-east-1"))

  def start_execution(self, input_data: ImportWorkflowRequest) -> str:
    """Start import workflow execution"""
    logger.info(f'Starting import state machine {self.state_machine_arn} with input {input_data.model_dump_json()}')

    # Generate unique execution name
    execution_name = f"import-{input_data.import_job_id}-{uuid.uuid4().hex[:8]}"

    result = self.sfn_client.start_execution(
      stateMachineArn=self.state_machine_arn,
      name=execution_name,
      input=input_data.model_dump_json(by_alias=True)
    )

    if 'ResponseMetadata' not in result or result['ResponseMetadata']['HTTPStatusCode'] != 200:
      raise RuntimeError(f"Failed to start import workflow: {result}")

    return result['executionArn']

  def to_import_job_id(self, execution_id: str) -> str:
    """Extract import job ID from execution ARN"""
    # Execution name format: import-{import_job_id}-{random}
    execution_name = execution_id.split(':')[-1]
    if execution_name.startswith('import-'):
      parts = execution_name.split('-')
      if len(parts) >= 3:
        # Join all parts except 'import' and the last random part
        return '-'.join(parts[1:-1])
    return execution_name

  def to_execution_id(self, import_job_id: str) -> str:
    """Convert import job ID to execution ARN pattern (for searching)"""
    # This is used for pattern matching, not exact ARN construction
    return f"{self.state_machine_arn.replace('stateMachine', 'execution')}:import-{import_job_id}-"

  def get_state_machine_execution_details(self, execution_id: str) -> Workflow | None:
    """Get execution details for import workflow"""
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
      logger.exception(f"Failed to get execution details for {execution_id}: {e}")
      return None

  def get_execution_status(self, execution_id: str) -> str | None:
    """Get just the status of an execution"""
    try:
      result: DescribeExecutionOutputTypeDef = self.sfn_client.describe_execution(executionArn=execution_id)
      return result["status"]
    except Exception as e:
      logger.exception(f"Failed to get execution status for {execution_id}: {e}")
      return None