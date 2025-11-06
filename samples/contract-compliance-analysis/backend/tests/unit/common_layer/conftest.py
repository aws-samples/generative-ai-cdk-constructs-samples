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

# Setup paths for common layer testing
import sys
import os
import pytest
import boto3
from moto import mock_aws

# Add common layer to Python path
common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'stack', 'lambda', 'common_layer')

sys.path.insert(0, os.path.abspath(common_layer_path))

# Import common models and utilities for testing
from model import Job, Clause, ContractType, Guideline, ImportJob, AdditionalChecks, LegislationCheck
from polyfactory.factories.pydantic_factory import ModelFactory

class ClauseFactory(ModelFactory[Clause]):
    __check_model__ = True

@pytest.fixture
def job_id():
    return "foo_job_id"

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

    return table

@pytest.fixture
def clauses(job_id, additional_checks):
    """Sample clauses for testing"""
    return [
        Clause(
            job_id=job_id,
            clause_number=1,
            text="This is a test clause",
            types=[],
            additional_checks=additional_checks
        ),
        Clause(
            job_id=job_id,
            clause_number=2,
            text="This is another test clause",
            types=[],
            additional_checks=additional_checks
        ),
        Clause(
            job_id=job_id,
            clause_number=3,
            text="This is a third test clause",
            types=[],
            additional_checks=additional_checks
        )
    ]

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
    return clauses_table

@pytest.fixture
def legislation_check():
    return LegislationCheck(
        compliant=True,
        analysis="Test legislation analysis"
    )

@pytest.fixture
def additional_checks():
    return AdditionalChecks(legislation_check=LegislationCheck(
        compliant=True,
        analysis="Test legislation analysis"
    ))

@pytest.fixture
def clauses_for(faker, additional_checks):
    def _clauses_for(_job_id, _additional_checks: AdditionalChecks = additional_checks):
        return ClauseFactory.batch(3, job_id=_job_id, additional_checks=_additional_checks)
    return _clauses_for

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
def clause(additional_checks):
    return ClauseFactory.build(additional_checks=additional_checks)

@pytest.fixture
def table_with_completed_job(jobs_table, job_id):
    jobs_table.put_item(Item={
        "id": job_id,
        "document_s3_key": "service_contract_example.pdf",
        "contract_type_id": "service-agreement",
        "needs_review": True,
        "status": "SUCCEEDED",
        "total_clause_types_by_risk": {
            "high": {"quantity": 4, "threshold": 0},
            "low": {"quantity": 1, "threshold": 3},
            "medium": {"quantity": 6, "threshold": 1},
            "none": {"quantity": 30}
        },
        "total_compliance_by_impact": {
            "high": {
                "compliant": {"quantity": 5, "risk": "none"},
                "missing": {"quantity": 0, "risk": "high"},
                "non_compliant": {"quantity": 4, "risk": "high"}
            },
            "low": {
                "compliant": {"quantity": 7, "risk": "none"},
                "missing": {"quantity": 0, "risk": "medium"},
                "non_compliant": {"quantity": 1, "risk": "low"}
            },
            "medium": {
                "compliant": {"quantity": 18, "risk": "none"},
                "missing": {"quantity": 0, "risk": "high"},
                "non_compliant": {"quantity": 6, "risk": "medium"}
            }
        },
        "unknown_total": 5
    })

@pytest.fixture
def ddb(dynamodb_client):
    """Return the session-scoped DynamoDB client"""
    return dynamodb_client