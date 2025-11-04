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
  from mypy_boto3_dynamodb.paginator import ScanPaginator

import boto3
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

from repository import ContractTypeRepository
from model import ContractType

deserializer = TypeDeserializer()


class DynamoDBContractTypeRepository(ContractTypeRepository):  # type:ignore[misc]
  """DynamoDB implementation of the contract type repository"""

  def __init__(self, table_name: str):
    self.table_name = table_name
    self.dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
    self.table = self.dynamodb.Table(table_name)
    self.paginator: ScanPaginator = boto3.client("dynamodb", region_name=os.getenv("AWS_REGION")).get_paginator('scan')

  def create_contract_type(self, contract_type: ContractType) -> None:
    """Create a new contract type"""
    try:
      self.table.put_item(
        Item=contract_type.model_dump(),
        ConditionExpression="attribute_not_exists(contract_type_id)"
      )
    except ClientError as e:
      if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
        raise ValueError(f"Contract type with ID '{contract_type.contract_type_id}' already exists")
      raise RuntimeError(f"Failed to create contract type in DynamoDB: {e}")

  def get_contract_types(self) -> List[ContractType]:
    """Get all contract types"""
    contract_types: list[ContractType] = []
    for page in self.paginator.paginate(TableName=self.table_name):
      for item in page.get("Items", []):
        deserialized_item = {k: deserializer.deserialize(v) for k, v in item.items()}
        try:
          contract_types.append(ContractType.model_validate(deserialized_item))
        except ValidationError:
          raise RuntimeError(f"Failed to parse contract type from DynamoDB: {deserialized_item}")
    return contract_types

  def get_contract_type(self, contract_type_id: str) -> ContractType | None:
    """Get a specific contract type by ID"""
    result = self.table.get_item(Key={"contract_type_id": contract_type_id})
    if "Item" not in result:
      return None

    try:
      return ContractType.model_validate(result["Item"])
    except ValidationError:
      raise RuntimeError(f"Failed to parse contract type from DynamoDB: {result['Item']}")

  def update_contract_type(self, contract_type: ContractType) -> None:
    """Update an existing contract type"""
    try:
      self.table.put_item(
        Item=contract_type.model_dump(),
        ConditionExpression="attribute_exists(contract_type_id)"
      )
    except ClientError as e:
      if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
        raise ValueError(f"Contract type with ID '{contract_type.contract_type_id}' does not exist")
      raise RuntimeError(f"Failed to update contract type in DynamoDB: {e}")

  def delete_contract_type(self, contract_type_id: str) -> None:
    """Delete a contract type"""
    try:
      self.table.delete_item(
        Key={"contract_type_id": contract_type_id},
        ConditionExpression="attribute_exists(contract_type_id)"
      )
    except ClientError as e:
      if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
        raise ValueError(f"Contract type with ID '{contract_type_id}' does not exist")
      raise RuntimeError(f"Failed to delete contract type from DynamoDB: {e}")