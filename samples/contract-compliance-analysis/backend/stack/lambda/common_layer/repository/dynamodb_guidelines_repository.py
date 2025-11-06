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
import boto3
from datetime import datetime, timezone
from functools import reduce
from typing import Dict, List, Optional, Any
from pydantic import ValidationError
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from repository import GuidelinesRepository
from model import Guideline


class APIError(Exception):
    """Custom API error with status code and error details"""

    def __init__(self, status_code: int, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class GuidelineErrors:
    """Common guideline error scenarios"""

    @staticmethod
    def guideline_not_found(contract_type_id: str, clause_type_id: str) -> APIError:
        return APIError(
            404,
            "GUIDELINE_NOT_FOUND",
            f"Guideline not found for contract type '{contract_type_id}' and clause type '{clause_type_id}'"
        )

    @staticmethod
    def guideline_already_exists(contract_type_id: str, clause_type_id: str) -> APIError:
        return APIError(
            409,
            "GUIDELINE_ALREADY_EXISTS",
            f"Guideline already exists for contract type '{contract_type_id}' and clause type '{clause_type_id}'"
        )

    @staticmethod
    def invalid_contract_type(contract_type_id: str) -> APIError:
        return APIError(
            400,
            "INVALID_CONTRACT_TYPE",
            f"Invalid contract type '{contract_type_id}'"
        )

    @staticmethod
    def validation_error(message: str, details: Optional[Dict[str, Any]] = None) -> APIError:
        return APIError(
            400,
            "VALIDATION_ERROR",
            message,
            details
        )

    @staticmethod
    def unauthorized() -> APIError:
        return APIError(
            401,
            "UNAUTHORIZED",
            "Authentication required"
        )

    @staticmethod
    def forbidden() -> APIError:
        return APIError(
            403,
            "FORBIDDEN",
            "Insufficient permissions"
        )


class DynamoDBGuidelinesRepository(GuidelinesRepository):
    """DynamoDB implementation of the guidelines repository"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
        self.table = self.dynamodb.Table(table_name)

    def list_guidelines(self, contract_type_id: str, search: Optional[str] = None,
                       level: Optional[str] = None, limit: int = 50,
                       last_evaluated_key: Optional[Dict] = None) -> Dict:
        """List guidelines with filtering and pagination"""

        # Base query by contract type (partition key)
        query_params = {
            'KeyConditionExpression': Key('contract_type_id').eq(contract_type_id),
            'Limit': limit
        }

        # Add pagination
        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key

        # Build filter expressions
        filter_expressions = []

        if search:
            # Search across name and standard_wording fields
            # Note: clause_type_id cannot be used in filter expressions as it's a primary key attribute
            search_filter = (
                Attr('name').contains(search) |
                Attr('standard_wording').contains(search)
            )
            filter_expressions.append(search_filter)

        if level:
            filter_expressions.append(Attr('level').eq(level))

        # Combine filters with AND logic
        if filter_expressions:
            query_params['FilterExpression'] = reduce(lambda x, y: x & y, filter_expressions)

        try:
            response = self.table.query(**query_params)

            # Convert items to Guideline objects
            guidelines = []
            for item in response.get('Items', []):
                try:
                    guidelines.append(Guideline.model_validate(item))
                except ValidationError as e:
                    raise RuntimeError(f"Failed to parse guideline from DynamoDB: {item}, error: {e}")

            return {
                'guidelines': guidelines,
                'last_evaluated_key': response.get('LastEvaluatedKey'),
                'count': response.get('Count', 0)
            }

        except ClientError as e:
            raise RuntimeError(f"Failed to query guidelines from DynamoDB: {e}")

    def get_guideline(self, contract_type_id: str, clause_type_id: str) -> Optional[Guideline]:
        """Get specific guideline by composite key"""
        try:
            response = self.table.get_item(
                Key={
                    'contract_type_id': contract_type_id,
                    'clause_type_id': clause_type_id
                }
            )

            if 'Item' not in response:
                return None

            return Guideline.model_validate(response['Item'])

        except ValidationError as e:
            raise RuntimeError(f"Failed to parse guideline from DynamoDB: {response.get('Item')}, error: {e}")
        except ClientError as e:
            raise RuntimeError(f"Failed to get guideline from DynamoDB: {e}")

    def get_next_clause_type_id(self, contract_type_id: str) -> str:
        """Get the next sequential clause_type_id for a contract type"""
        try:
            # Query all guidelines for this contract type
            response = self.table.query(
                KeyConditionExpression=Key('contract_type_id').eq(contract_type_id),
                ProjectionExpression='clause_type_id'
            )

            # Extract numeric clause_type_ids and find the maximum
            max_id = 0
            for item in response.get('Items', []):
                clause_id = item.get('clause_type_id', '0')
                try:
                    numeric_id = int(clause_id)
                    max_id = max(max_id, numeric_id)
                except ValueError:
                    # Skip non-numeric clause_type_ids (for backward compatibility)
                    continue

            return str(max_id + 1)

        except ClientError as e:
            raise RuntimeError(f"Failed to get next clause_type_id: {e}")

    def create_guideline(self, guideline: Guideline) -> Guideline:
        """Create new guideline with auto-generated clause_type_id if not provided"""

        # Auto-generate clause_type_id if not provided or empty
        if not guideline.clause_type_id:
            guideline.clause_type_id = self.get_next_clause_type_id(guideline.contract_type_id)

        # Add timestamps
        now = datetime.now(timezone.utc).isoformat()
        guideline.created_at = now
        guideline.updated_at = now

        # Use retry logic to handle race conditions
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use condition to prevent overwriting existing guidelines
                self.table.put_item(
                    Item=guideline.model_dump(exclude_none=True),
                    ConditionExpression='attribute_not_exists(contract_type_id) AND attribute_not_exists(clause_type_id)'
                )
                return guideline

            except ClientError as e:
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    if attempt < max_retries - 1:
                        # Regenerate clause_type_id and retry
                        guideline.clause_type_id = self.get_next_clause_type_id(guideline.contract_type_id)
                        continue
                    else:
                        raise GuidelineErrors.guideline_already_exists(
                            guideline.contract_type_id,
                            guideline.clause_type_id
                        )
                raise RuntimeError(f"Failed to create guideline in DynamoDB: {e}")

    def update_guideline(self, contract_type_id: str, clause_type_id: str,
                        updates: Dict) -> Guideline:
        """Update existing guideline"""

        # Add updated timestamp
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()

        # Build update expression
        update_expression = "SET "
        expression_values = {}
        expression_names = {}

        for key, value in updates.items():
            attr_name = f"#{key}"
            attr_value = f":{key}"
            update_expression += f"{attr_name} = {attr_value}, "
            expression_names[attr_name] = key
            expression_values[attr_value] = value

        update_expression = update_expression.rstrip(", ")

        try:
            response = self.table.update_item(
                Key={
                    'contract_type_id': contract_type_id,
                    'clause_type_id': clause_type_id
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression='attribute_exists(contract_type_id) AND attribute_exists(clause_type_id)',
                ReturnValues='ALL_NEW'
            )

            return Guideline.model_validate(response['Attributes'])

        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise GuidelineErrors.guideline_not_found(contract_type_id, clause_type_id)
            raise RuntimeError(f"Failed to update guideline in DynamoDB: {e}")
        except ValidationError as e:
            raise RuntimeError(f"Failed to parse updated guideline from DynamoDB: {response.get('Attributes')}, error: {e}")

    def delete_guideline(self, contract_type_id: str, clause_type_id: str) -> bool:
        """Delete guideline with existence check"""
        try:
            self.table.delete_item(
                Key={
                    'contract_type_id': contract_type_id,
                    'clause_type_id': clause_type_id
                },
                ConditionExpression='attribute_exists(contract_type_id) AND attribute_exists(clause_type_id)'
            )
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False  # Guideline doesn't exist
            raise RuntimeError(f"Failed to delete guideline from DynamoDB: {e}")

    def delete_all_guidelines_for_contract_type(self, contract_type_id: str) -> int:
        """Delete all guidelines for a specific contract type"""
        try:
            # First, query all guidelines for this contract type
            response = self.table.query(
                KeyConditionExpression=Key('contract_type_id').eq(contract_type_id),
                ProjectionExpression='contract_type_id, clause_type_id'
            )

            guidelines_to_delete = response.get('Items', [])
            deleted_count = 0

            # Delete each guideline
            for guideline in guidelines_to_delete:
                try:
                    self.table.delete_item(
                        Key={
                            'contract_type_id': guideline['contract_type_id'],
                            'clause_type_id': guideline['clause_type_id']
                        }
                    )
                    deleted_count += 1
                except ClientError as e:
                    # Log error but continue with other deletions
                    print(f"Failed to delete guideline {guideline['contract_type_id']}/{guideline['clause_type_id']}: {e}")

            return deleted_count

        except ClientError as e:
            raise RuntimeError(f"Failed to delete guidelines for contract type from DynamoDB: {e}")