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
from datetime import datetime
from pydantic import ValidationError
from typing import Optional
from aws_lambda_powertools import Logger

import boto3
from botocore.exceptions import ClientError

from repository import ImportJobsRepository
from model import ImportJob

logger = Logger(child=True)


class DynamoDBImportJobsRepository(ImportJobsRepository):  # type:ignore[misc]
  """DynamoDB implementation of the import jobs repository"""

  def __init__(self, table_name: str):
    self.table_name = table_name
    self.dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
    self.table = self.dynamodb.Table(table_name)

  def create_import_job(self, import_job: ImportJob) -> None:
    """Create a new import job"""
    try:
      self.table.put_item(
        Item=import_job.model_dump(),
        ConditionExpression="attribute_not_exists(import_job_id)"
      )
    except ClientError as e:
      if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
        raise ValueError(f"Import job with ID '{import_job.import_job_id}' already exists")
      raise RuntimeError(f"Failed to create import job in DynamoDB: {e}")

  def get_import_job(self, import_job_id: str) -> Optional[ImportJob]:
    """Get a specific import job by ID"""
    result = self.table.get_item(Key={"import_job_id": import_job_id})
    if "Item" not in result:
      return None

    try:
      return ImportJob.model_validate(result["Item"])
    except ValidationError as e:
      logger.error(f"Pydantic validation failed for import job {import_job_id}: {e}")
      raise RuntimeError(f"Failed to parse import job from DynamoDB: {result['Item']}") from e

  def update_import_job(self, import_job: ImportJob) -> None:
    """Update an existing import job"""
    try:
      # Update the updated_at timestamp
      import_job.updated_at = datetime.utcnow().isoformat()

      self.table.put_item(
        Item=import_job.model_dump(),
        ConditionExpression="attribute_exists(import_job_id)"
      )
    except ClientError as e:
      if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
        raise ValueError(f"Import job with ID '{import_job.import_job_id}' does not exist")
      raise RuntimeError(f"Failed to update import job in DynamoDB: {e}")

  def update_import_job_status(self, import_job_id: str, status: str,
                              error_message: Optional[str] = None,
                              progress: Optional[int] = None,
                              current_step: Optional[str] = None,
                              contract_type_id: Optional[str] = None) -> None:
    """Update import job status and related fields"""
    try:
      # Build update expression dynamically
      update_expression = "SET #status = :status, updated_at = :updated_at"
      expression_attribute_names = {"#status": "status"}
      expression_attribute_values = {
        ":status": status,
        ":updated_at": datetime.utcnow().isoformat()
      }

      if error_message is not None:
        update_expression += ", error_message = :error_message"
        expression_attribute_values[":error_message"] = error_message

      if progress is not None:
        update_expression += ", progress = :progress"
        expression_attribute_values[":progress"] = progress

      if current_step is not None:
        update_expression += ", current_step = :current_step"
        expression_attribute_values[":current_step"] = current_step

      if contract_type_id is not None:
        update_expression += ", contract_type_id = :contract_type_id"
        expression_attribute_values[":contract_type_id"] = contract_type_id

      self.table.update_item(
        Key={"import_job_id": import_job_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values,
        ConditionExpression="attribute_exists(import_job_id)"
      )
    except ClientError as e:
      if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
        raise ValueError(f"Import job with ID '{import_job_id}' does not exist")
      raise RuntimeError(f"Failed to update import job status in DynamoDB: {e}")