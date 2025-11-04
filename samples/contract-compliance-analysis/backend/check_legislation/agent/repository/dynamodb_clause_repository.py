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
from botocore.exceptions import ClientError

from repository import ClauseRepository
from model import Clause, CheckedClause

AWS_REGION = os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION')


class DynamoDBClauseRepository(ClauseRepository):  # type:ignore[misc]
    """DynamoDB implementation of the clause repository"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        self.table = self.dynamodb.Table(table_name)

    def get_clause(self, job_id: str, clause_number: int) -> Clause:
        """Retrieve a clause from DynamoDB by job_id and clause_number"""
        try:
            response = self.table.get_item(
                Key={
                    'job_id': job_id,
                    'clause_number': clause_number
                }
            )

            if 'Item' not in response:
                raise ValueError(f"Clause not found for job_id={job_id}, clause_number={clause_number}")

            item = response['Item']

            return Clause(
                job_id=item['job_id'],
                clause_number=item['clause_number'],
                text=item['text']
            )

        except ClientError as e:
            raise RuntimeError(f"Failed to retrieve clause from DynamoDB: {e}")

    def update_legislation_checks(self, checked_clause: CheckedClause) -> None:
        """Update the legislation_checks field for a clause"""
        try:
            # First ensure additional_checks exists
            self.table.update_item(
                Key={
                    'job_id': checked_clause.job_id,
                    'clause_number': checked_clause.clause_number
                },
                UpdateExpression='SET additional_checks = if_not_exists(additional_checks, :empty_obj)',
                ExpressionAttributeValues={
                    ':empty_obj': {}
                }
            )

            # Then set the legislation_check
            self.table.update_item(
                Key={
                    'job_id': checked_clause.job_id,
                    'clause_number': checked_clause.clause_number
                },
                UpdateExpression='SET additional_checks.legislation_check = :check',
                ExpressionAttributeValues={
                    ':check': checked_clause.additional_checks.legislation_check.model_dump()
                }
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to update legislation checks in DynamoDB: {e}")
