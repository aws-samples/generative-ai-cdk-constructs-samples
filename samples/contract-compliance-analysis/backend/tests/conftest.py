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

# Root conftest.py for all backend tests
# This provides session-scoped AWS mocks to avoid table creation conflicts

import os
import pytest
import boto3
from moto import mock_aws


@pytest.fixture(scope="session", autouse=True)
def aws_credentials():
    """Set up AWS credentials for the entire test session.
    
    These are fake credentials required by the moto library for AWS service mocking.
    They are never used for actual AWS authentication and have no security implications.
    See: https://docs.getmoto.org/en/latest/docs/getting_started.html#how-do-i-avoid-tests-from-mutating-my-real-infrastructure
    """
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'  # nosec B105
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'  # nosec B105
    os.environ['AWS_SESSION_TOKEN'] = 'testing'  # nosec B105
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture(scope="session", autouse=True)
def mock_aws_session():
    """Session-scoped AWS mock that persists across all tests"""
    with mock_aws():
        yield


@pytest.fixture(scope="session")
def dynamodb_client(mock_aws_session, aws_credentials):
    """Session-scoped DynamoDB client"""
    return boto3.client('dynamodb', region_name='us-east-1')


@pytest.fixture(scope="session")
def dynamodb_resource(mock_aws_session, aws_credentials):
    """Session-scoped DynamoDB resource"""
    return boto3.resource('dynamodb', region_name='us-east-1')


@pytest.fixture(scope="session", autouse=True)
def create_common_tables(dynamodb_client):
    """Create commonly used DynamoDB tables once for the entire session"""

    tables_to_create = [
        {
            'TableName': 'test-guidelines-table',
            'KeySchema': [
                {'AttributeName': 'contract_type_id', 'KeyType': 'HASH'},
                {'AttributeName': 'clause_type_id', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'contract_type_id', 'AttributeType': 'S'},
                {'AttributeName': 'clause_type_id', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        {
            'TableName': 'test-contract-types-table',
            'KeySchema': [
                {'AttributeName': 'contract_type_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'contract_type_id', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        {
            'TableName': 'test-jobs-table',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'contract_type_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'contract_type_id-created_at-index',
                    'KeySchema': [
                        {'AttributeName': 'contract_type_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        {
            'TableName': 'test-clauses-table',
            'KeySchema': [
                {'AttributeName': 'job_id', 'KeyType': 'HASH'},
                {'AttributeName': 'clause_number', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'job_id', 'AttributeType': 'S'},
                {'AttributeName': 'clause_number', 'AttributeType': 'N'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        {
            'TableName': 'test-import-jobs-table',
            'KeySchema': [
                {'AttributeName': 'import_job_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'import_job_id', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }
    ]

    for table_config in tables_to_create:
        try:
            dynamodb_client.create_table(**table_config)
        except dynamodb_client.exceptions.ResourceInUseException:
            # Table already exists, skip
            pass

    yield
