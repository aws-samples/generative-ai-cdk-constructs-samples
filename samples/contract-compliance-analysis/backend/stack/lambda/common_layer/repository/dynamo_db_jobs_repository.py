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
from pydantic import ValidationError
from typing import List, Optional, TYPE_CHECKING
from aws_lambda_powertools import Logger

if TYPE_CHECKING:
  from mypy_boto3_dynamodb.paginator import ScanPaginator, QueryPaginator

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

from repository import JobsRepository
from model import Job

deserializer = TypeDeserializer()
logger = Logger(child=True)


class DynamoDBJobsRepository(JobsRepository):  # type:ignore[misc]
  """DynamoDB implementation of the job repository"""

  def __init__(self, table_name: str):
    self.table_name = table_name
    self.dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
    self.table = self.dynamodb.Table(table_name)
    self.client = boto3.client("dynamodb", region_name=os.getenv("AWS_REGION"))
    self.scan_paginator: ScanPaginator = self.client.get_paginator('scan')
    self.query_paginator: QueryPaginator = self.client.get_paginator('query')

  def get_jobs(self, contract_type_id: Optional[str] = None) -> List[Job]:
    jobs: list[Job] = []

    if contract_type_id:
      # Use GSI to query by contract_type_id
      for page in self.query_paginator.paginate(
        TableName=self.table_name,
        IndexName='contract_type_id-created_at-index',
        KeyConditionExpression='contract_type_id = :contract_type_id',
        ExpressionAttributeValues={':contract_type_id': {'S': contract_type_id}},
        ScanIndexForward=False  # Sort by created_at descending (newest first)
      ):
        for item in page.get("Items", []):
          deserialized_item = {k: deserializer.deserialize(v) for k, v in item.items()}
          try:
            jobs.append(Job.model_validate(deserialized_item))
          except ValidationError as e:
            logger.error(f"Pydantic validation failed for job: {e}")
            raise RuntimeError(f"Failed to parse job from DynamoDB: {deserialized_item}")
    else:
      # Scan all jobs if no contract type filter
      for page in self.scan_paginator.paginate(TableName=self.table_name):
        for item in page.get("Items", []):
          deserialized_item = {k: deserializer.deserialize(v) for k, v in item.items()}
          try:
            jobs.append(Job.model_validate(deserialized_item))
          except ValidationError as e:
            logger.error(f"Pydantic validation failed for job: {e}")
            raise RuntimeError(f"Failed to parse job from DynamoDB: {deserialized_item}")

    return jobs

  def get_job(self, job_id: str) -> Job | None:
    result = self.table.get_item(Key={"id": job_id})
    if "Item" not in result:
      return None

    try:
      return Job.model_validate(result["Item"])
    except ValidationError as e:
      logger.error(f"Pydantic validation failed for job {job_id}: {e}")
      raise RuntimeError(f"Failed to parse job from DynamoDB: {result['Item']}") from e

  def record_job(self, job: Job) -> None:
    """Update the legislation_checks field for a clause"""
    try:
      self.table.put_item(
        Item=job.model_dump()
      )
    except ClientError as e:
      raise RuntimeError(f"Failed to put job in DynamoDB: {e}")
