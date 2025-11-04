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
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
  from mypy_boto3_dynamodb.paginator import QueryPaginator

import boto3
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

from repository import ClausesRepository
from model import Clause, ClauseType

deserializer = TypeDeserializer()


class DynamoDBClausesRepository(ClausesRepository):  # type:ignore[misc]
  """DynamoDB implementation of the job repository"""

  def __init__(self, table_name: str):
    self.table_name = table_name
    self.dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
    self.table = self.dynamodb.Table(table_name)
    self.paginator: QueryPaginator = boto3.client("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1")).get_paginator('query')

  def get_clauses(self, job_id) -> List[Clause]:
    clauses = []
    for page in self.paginator.paginate(
        TableName=self.table_name, KeyConditionExpression="job_id = :jid", ExpressionAttributeValues={":jid": {"S": job_id}}):
      for item in page.get("Items", []):
        clause = {k: deserializer.deserialize(v) for k, v in item.items()}
        clauses.append(Clause.model_validate(clause))

    return clauses