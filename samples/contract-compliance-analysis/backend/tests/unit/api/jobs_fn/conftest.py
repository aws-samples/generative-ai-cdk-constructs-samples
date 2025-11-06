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

from datetime import datetime, timezone
from faker import Faker
from freezegun import freeze_time
import os
import pytest

from test_utils.datetime_helpers import parse_datetime, to_utc

import boto3
from moto import mock_aws

from polyfactory.factories.pydantic_factory import ModelFactory

# Setup paths for testing - add at the very beginning to avoid lambda keyword issues
import sys
import os

# Note: We don't modify sys.path globally to avoid conflicts with other test files
# All imports are handled within the fixture function

# Import models with temporary path setup
def _import_with_temp_path():
    """Import models with temporary sys.path setup"""
    import sys
    jobs_fn_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'jobs_fn')
    common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer')

    original_path = sys.path.copy()
    try:
        sys.path.insert(0, os.path.abspath(jobs_fn_path))
        sys.path.insert(0, os.path.abspath(common_layer_path))
        from model import Job, Clause, AdditionalChecks, LegislationCheck
        return Job, Clause, AdditionalChecks, LegislationCheck
    finally:
        sys.path[:] = original_path

Job, Clause, AdditionalChecks, LegislationCheck = _import_with_temp_path()

# Import helper to ensure we get the correct index module
def get_jobs_index_module():
    """Get the jobs function index module, ensuring it's the correct one"""
    import importlib.util
    import sys

    # Clear any cached jobs index module to avoid conflicts
    modules_to_clear = [k for k in sys.modules.keys() if k.startswith('jobs_index') or (k == 'index' and 'jobs_fn' in str(sys.modules.get(k, '')))]
    for module in modules_to_clear:
        del sys.modules[module]

    # Import the jobs index module specifically
    jobs_index_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'jobs_fn', 'index.py')
    spec = importlib.util.spec_from_file_location("jobs_index", jobs_index_path)
    jobs_index = importlib.util.module_from_spec(spec)

    # Add necessary paths to sys.path temporarily
    common_layer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer'))
    jobs_fn_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'jobs_fn'))

    original_path = sys.path.copy()
    try:
        sys.path.insert(0, jobs_fn_path)
        sys.path.insert(0, common_layer_path)
        spec.loader.exec_module(jobs_index)
    finally:
        sys.path[:] = original_path

    return jobs_index

@pytest.fixture
def jobs_index():
    """Fixture to provide the jobs index module"""
    return get_jobs_index_module()

def import_jobs_function(function_name):
    """Helper to import a specific function from the jobs index module"""
    jobs_index = get_jobs_index_module()
    return getattr(jobs_index, function_name)

def patch_jobs_repository(repository_name):
    """Helper to create a patch for a jobs repository"""
    from unittest.mock import patch
    jobs_index = get_jobs_index_module()
    return patch.object(jobs_index, repository_name)


class ClauseFactory(ModelFactory[Clause]):
  __check_model__ = True


class JobFactory(ModelFactory[Job]):
  __check_model__ = True


class AdditionalChecksFactory(ModelFactory[AdditionalChecks]):
  __check_model__ = True


class LegislationCheckFactory(ModelFactory[LegislationCheck]):
  __check_model__ = True


@pytest.fixture
def freeze_utc_now():
  with freeze_time(auto_tick_seconds=0, tz_offset=0):  # UTC
    yield


@pytest.fixture
def assert_datetime_near_now():
  def _assert(dt_like, tolerance_seconds=5, now=None):
    actual = to_utc(parse_datetime(dt_like))
    reference = to_utc(parse_datetime(now)) if now else datetime.now(timezone.utc)
    delta = abs((reference - actual).total_seconds())
    assert delta <= tolerance_seconds, (
      f"{actual} not within {tolerance_seconds}s of {reference}, delta={delta:.3f}"
    )

  return _assert


@pytest.fixture
def ddb(dynamodb_client):
  """Return the session-scoped DynamoDB client"""
  return dynamodb_client


@pytest.fixture
def sfn(mock_aws_session):
  """Return a mocked Step Functions client"""
  return boto3.client("stepfunctions", region_name="us-east-1")


@pytest.fixture(scope="function")
def mocked_aws(aws_credentials):
  """Mock all AWS interactions"""
  with mock_aws():
    yield


@pytest.fixture
def jobs_table_name():
  return 'test-jobs-table'


@pytest.fixture
def jobs_table(dynamodb_resource, jobs_table_name):
  """Get the session-scoped jobs table and clear it before each test"""
  table = dynamodb_resource.Table(jobs_table_name)

  # Clear any existing items before each test
  scan_result = table.scan()
  with table.batch_writer() as batch:
    for item in scan_result.get('Items', []):
      batch.delete_item(Key={'id': item['id']})

  yield table


@pytest.fixture
def job_id():
  return "foo_job_id"


@pytest.fixture
def job(job_id):
  return JobFactory.build(id=job_id)


@pytest.fixture
def table_with_jobs(jobs_table, job):
  jobs_table.put_item(Item=job.model_dump())
  jobs_table.put_item(Item=JobFactory.build().model_dump())


@pytest.fixture
def table_with_completed_job(jobs_table, job_id):
  jobs_table.put_item(Item={
    "id": job_id,
    "document_s3_key": "service_contract_example.pdf",
    "contract_type_id": "service-agreement",
    "end_date": "2025-08-21T23:04:16.668000+00:00",
    "needs_review": True,
    "start_date": "2025-08-21T22:39:07.075000+00:00",
    "status": "SUCCEEDED",
    "total_clause_types_by_risk": {
      "high": {
        "quantity": 4,
        "threshold": 0
      },
      "low": {
        "quantity": 1,
        "threshold": 3
      },
      "medium": {
        "quantity": 6,
        "threshold": 1
      },
      "none": {
        "quantity": 30
      }
    },
    "total_compliance_by_impact": {
      "high": {
        "compliant": {
          "quantity": 5,
          "risk": "none"
        },
        "missing": {
          "quantity": 0,
          "risk": "high"
        },
        "non_compliant": {
          "quantity": 4,
          "risk": "high"
        }
      },
      "low": {
        "compliant": {
          "quantity": 7,
          "risk": "none"
        },
        "missing": {
          "quantity": 0,
          "risk": "medium"
        },
        "non_compliant": {
          "quantity": 1,
          "risk": "low"
        }
      },
      "medium": {
        "compliant": {
          "quantity": 18,
          "risk": "none"
        },
        "missing": {
          "quantity": 0,
          "risk": "high"
        },
        "non_compliant": {
          "quantity": 6,
          "risk": "medium"
        }
      }
    },
    "unknown_total": 5
  })


@pytest.fixture
def clauses_table_name():
  return 'test-clauses-table'


@pytest.fixture
def clauses_table(dynamodb_resource, clauses_table_name):
  """Get the session-scoped clauses table and clear it before each test"""
  table = dynamodb_resource.Table(clauses_table_name)

  # Clear any existing items before each test
  scan_result = table.scan()
  with table.batch_writer() as batch:
    for item in scan_result.get('Items', []):
      batch.delete_item(
        Key={
          'job_id': item['job_id'],
          'clause_number': item['clause_number']
        }
      )

  yield table


@pytest.fixture
def additional_checks(faker: Faker):
  return AdditionalChecksFactory.build(legislation_check=LegislationCheckFactory.build(analysis=faker.paragraph()))

@pytest.fixture
def clauses(job_id, additional_checks):
  return ClauseFactory.batch(3, job_id=job_id, additional_checks=additional_checks)


@pytest.fixture
def clauses_for(faker: Faker, additional_checks):
  def _clauses_for(_job_id, _additional_checks: AdditionalChecks = additional_checks):
    return ClauseFactory.batch(3, job_id=_job_id, additional_checks=_additional_checks)

  return _clauses_for


@pytest.fixture
def clause(additional_checks):
  return ClauseFactory.build(additional_checks=additional_checks)


@pytest.fixture
def table_with_clauses(clauses_table, clauses):
  """
  Clauses in the table will contain extraneous fields, we will mimic this to see if
  our repository is robust to it
  """
  for clause in clauses:
    full_clause = clause.model_dump() | {"evaluation_request_id": "foo", "classification_request_id": "bar"}
    clauses_table.put_item(Item=full_clause)


@pytest.fixture
def clauses_table_with_unknown_clause_type(clauses_table, job_id):
  clauses_table.put_item(Item={"job_id": job_id, "clause_number": 49, "text": "some text", "types": [
    {"type_id": "UNKNOWN", "classification_request_id": "20a297ce-febe-4eb5-be71-0aeedbfa0294"}]})
