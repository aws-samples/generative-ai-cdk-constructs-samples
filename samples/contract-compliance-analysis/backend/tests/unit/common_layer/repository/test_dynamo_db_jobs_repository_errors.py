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

import pytest
from repository.dynamo_db_jobs_repository import DynamoDBJobsRepository
from model import Job


def test_record_job_handles_client_error(mock_aws_session):
    """Test that record_job raises RuntimeError on ClientError"""
    # Use a non-existent table to trigger ClientError
    repository = DynamoDBJobsRepository("non-existent-table")
    job = Job(id="test-job", status="RUNNING", document_s3_key="test.pdf", contract_type_id="service-agreement")

    with pytest.raises(RuntimeError, match="Failed to put job in DynamoDB"):
        repository.record_job(job)


def test_get_jobs_handles_validation_error(dynamodb_client):
    """Test that get_jobs raises RuntimeError on ValidationError"""
    table_name = "test-jobs-table"

    # Table already exists from session fixture, just clear and add invalid data
    # Put invalid data that will fail Job validation
    dynamodb_client.put_item(
        TableName=table_name,
        Item={"id": {"S": "test"}, "invalid_field": {"S": "invalid"}}
    )

    repository = DynamoDBJobsRepository(table_name)

    try:
        with pytest.raises(RuntimeError, match="Failed to parse job from DynamoDB"):
            repository.get_jobs()
    finally:
        # Clean up the invalid item
        dynamodb_client.delete_item(
            TableName=table_name,
            Key={"id": {"S": "test"}}
        )


def test_get_job_handles_validation_error(dynamodb_client):
    """Test that get_job raises RuntimeError on ValidationError"""
    table_name = "test-jobs-table"

    # Put invalid data that will fail Job validation
    dynamodb_client.put_item(
        TableName=table_name,
        Item={"id": {"S": "test2"}, "invalid_field": {"S": "invalid"}}
    )

    repository = DynamoDBJobsRepository(table_name)

    try:
        with pytest.raises(RuntimeError, match="Failed to parse job from DynamoDB"):
            repository.get_job("test2")
    finally:
        # Clean up the invalid item
        dynamodb_client.delete_item(
            TableName=table_name,
            Key={"id": {"S": "test2"}}
        )
