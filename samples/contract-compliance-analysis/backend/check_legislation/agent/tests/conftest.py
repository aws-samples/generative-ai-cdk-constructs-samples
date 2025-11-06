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
from faker import Faker
import os
import pytest
from moto import mock_aws

from model import Clause


@pytest.fixture(scope="function")
def aws_credentials():
  """Mocked AWS Credentials for moto.
  
  These are fake credentials required by the moto library for AWS service mocking.
  They are never used for actual AWS authentication and have no security implications.
  See: https://docs.getmoto.org/en/latest/docs/getting_started.html#how-do-i-avoid-tests-from-mutating-my-real-infrastructure
  """
  os.environ["AWS_ACCESS_KEY_ID"] = "testing"
  os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"  # nosec B105
  os.environ["AWS_SECURITY_TOKEN"] = "testing"  # nosec B105
  os.environ["AWS_SESSION_TOKEN"] = "testing"  # nosec B105
  os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def ddb(aws_credentials):
  """Return a mocked DynamoDB client"""
  with mock_aws():
    yield boto3.client("dynamodb", region_name="us-east-1")

@pytest.fixture
def clauses_table_name():
  return 'test-clauses-table'


@pytest.fixture
def clauses_table(ddb, clauses_table_name):
  ddb.create_table(TableName=clauses_table_name,
                   KeySchema=[
                     {'AttributeName': 'job_id', 'KeyType': 'HASH'},
                     {'AttributeName': 'clause_number', 'KeyType': 'RANGE'},
                   ],
                   AttributeDefinitions=[
                     {'AttributeName': 'job_id', 'AttributeType': 'S'},
                     {'AttributeName': 'clause_number', 'AttributeType': 'N'},
                   ],
                   BillingMode='PAY_PER_REQUEST'
                   )

  yield boto3.resource("dynamodb", region_name="us-east-1").Table(clauses_table_name)


@pytest.fixture
def job_id(faker: Faker):
  return faker.uuid4()


@pytest.fixture
def clause(job_id, faker: Faker):
  return Clause(job_id=job_id, clause_number=faker.random_int(min=1, max=10), text=faker.paragraph())

@pytest.fixture
def table_with_clause(clauses_table, clause):
  clauses_table.put_item(Item=clause.model_dump())
  yield clauses_table