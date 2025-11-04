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

from faker import Faker
import json
import pytest
from typing import Literal
import sys
import os

# Add the jobs function path to sys.path for imports
jobs_fn_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'jobs_fn')
common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer')
if jobs_fn_path not in sys.path:
    sys.path.insert(0, jobs_fn_path)
if common_layer_path not in sys.path:
    sys.path.insert(0, common_layer_path)

from model import AdditionalChecks, LegislationCheck


@pytest.fixture
def timed_definition():
  return json.dumps({
    "Comment": "A state machine with a Wait followed by a Pass that outputs a result.",
    "StartAt": "WaitState",
    "States": {
      "WaitState": {
        "Type": "Wait",
        "Seconds": 1,
        "Next": "OutputState"
      },
      "OutputState": {
        "Type": "Pass",
        "Result": {
          "Status": "OK"
        },
        "End": True
      }
    }
  })


@pytest.fixture
def role_arn():
  return "arn:aws:iam::241803840483:role/unknown_sf_role"


@pytest.fixture
def state_machine(sfn, role_arn, timed_definition):
  return sfn.create_state_machine(
    name="test",
    definition=timed_definition,
    roleArn=role_arn,
  )


def test_it_creates_a_job_using_new_api(jobs_table, jobs_table_name, sfn, state_machine, jobs_index):
  from unittest.mock import patch, MagicMock
  from model import ContractType, Workflow
  from datetime import datetime, timezone

  # Mock contract type repository to return a valid active contract type
  with patch.object(jobs_index, 'contract_type_repository') as mock_contract_repo, \
       patch.object(jobs_index, 'workflows_repository') as mock_workflows_repo, \
       patch.object(jobs_index, 'jobs_repository') as mock_jobs_repo:

    mock_contract_type = ContractType(
      contract_type_id="service-agreement",
      name="Service Agreement",
      description="Service agreement contracts",
      company_party_type="Customer",
      other_party_type="Service Provider",
      is_active=True,
      created_at="2024-01-01T00:00:00Z",
      updated_at="2024-01-01T00:00:00Z"
    )
    mock_contract_repo.get_contract_type.return_value = mock_contract_type

    # Mock workflows repository
    mock_execution_id = "test-execution-id"
    mock_job_id = "test-job-id"
    mock_workflows_repo.start_execution.return_value = mock_execution_id
    mock_workflows_repo.to_job_id.return_value = mock_job_id

    # Mock execution details
    mock_execution_details = Workflow(
      id=mock_execution_id,
      state_machine_id="arn:aws:states:us-east-1:123456789012:stateMachine:test",
      status="RUNNING",
      start_date=datetime.now(timezone.utc),
      end_date=None
    )
    mock_workflows_repo.get_state_machine_execution_details.return_value = mock_execution_details

    # Mock jobs repository
    mock_jobs_repo.record_job.return_value = None

    post_job = jobs_index.post_job
    PostJobRequest = jobs_index.PostJobRequest

    s3_key = "foo"
    contract_type_id = "service-agreement"
    description = "bar"
    output_lang: Literal["en"] = "en"
    additional_checks = {
      "legislationCheck": {
        "legislationId": "123"
      }
    }

    request_payload = {
      "documentS3Key": s3_key,
      "contractTypeId": contract_type_id,
      "description": description,
      "outputLanguage": output_lang,
      "additionalChecks": additional_checks
    }

    request = PostJobRequest.model_validate(request_payload)  # type: ignore

    response = post_job(request)

    assert "id" in response
    assert response["documentS3Key"] == s3_key
    assert response["contractTypeId"] == contract_type_id


def test_it_lists_jobs_persisted(jobs_table, state_machine, sfn, freeze_utc_now, assert_datetime_near_now, jobs_index):
  """
  This tests the new api
  """
  from unittest.mock import patch, MagicMock
  from model import ContractType, Job, Workflow
  from datetime import datetime, timezone

  # Mock contract type repository to return a valid active contract type
  with patch.object(jobs_index, 'contract_type_repository') as mock_contract_repo, \
       patch.object(jobs_index, 'workflows_repository') as mock_workflows_repo, \
       patch.object(jobs_index, 'jobs_repository') as mock_jobs_repo:

    mock_contract_type = ContractType(
      contract_type_id="service-agreement",
      name="Service Agreement",
      description="Service agreement contracts",
      company_party_type="Customer",
      other_party_type="Service Provider",
      is_active=True,
      created_at="2024-01-01T00:00:00Z",
      updated_at="2024-01-01T00:00:00Z"
    )
    mock_contract_repo.get_contract_type.return_value = mock_contract_type

    # Mock workflows repository for post_job
    mock_execution_id = "test-execution-id"
    mock_job_id = "test-job-id"
    mock_workflows_repo.start_execution.return_value = mock_execution_id
    mock_workflows_repo.to_job_id.return_value = mock_job_id
    mock_workflows_repo.to_execution_id.return_value = mock_execution_id

    # Mock execution details
    mock_start_date = datetime.now(timezone.utc)
    mock_execution_details = Workflow(
      id=mock_execution_id,
      state_machine_id="arn:aws:states:us-east-1:123456789012:stateMachine:test",
      status="RUNNING",
      start_date=mock_start_date,
      end_date=None
    )
    mock_workflows_repo.get_state_machine_execution_details.return_value = mock_execution_details

    # Mock jobs repository for post_job
    mock_jobs_repo.record_job.return_value = None

    # Mock jobs repository for get_jobs
    mock_job = Job(
      id=mock_job_id,
      document_s3_key="foo/file.pdf",
      contract_type_id="service-agreement",
      description=None,
      output_language="pt_BR",
      needs_review=False,
      guidelines_compliant=True,
      legislation_compliant=None,
      total_clause_types_by_risk={
        "high": {"quantity": 0, "threshold": None},
        "medium": {"quantity": 0, "threshold": None},
        "low": {"quantity": 0, "threshold": None},
        "none": {"quantity": 0}
      },
      total_compliance_by_impact={
        "high": {
          "compliant": {"quantity": 0, "risk": "high"},
          "non_compliant": {"quantity": 0, "risk": "high"},
          "missing": {"quantity": 0, "risk": "high"}
        },
        "medium": {
          "compliant": {"quantity": 0, "risk": "medium"},
          "non_compliant": {"quantity": 0, "risk": "medium"},
          "missing": {"quantity": 0, "risk": "medium"}
        },
        "low": {
          "compliant": {"quantity": 0, "risk": "low"},
          "non_compliant": {"quantity": 0, "risk": "low"},
          "missing": {"quantity": 0, "risk": "low"}
        }
      },
      unknown_total=0
    )
    mock_jobs_repo.get_jobs.return_value = [mock_job]

    get_jobs = jobs_index.get_jobs
    post_job = jobs_index.post_job
    PostJobRequest = jobs_index.PostJobRequest

    # given a job was started
    post_job(PostJobRequest(document_s3_key="foo/file.pdf", contract_type_id="service-agreement"))

    # when
    jobs = get_jobs()

    assert len(jobs) == 1

    assert jobs[0]["documentS3Key"] == "foo/file.pdf"
    assert jobs[0]["contractTypeId"] == "service-agreement"
    assert_datetime_near_now(jobs[0]["startDate"], tolerance_seconds=2)
    
    # Assert checks object structure
    assert "checks" in jobs[0]
    assert "guidelines" in jobs[0]["checks"]
    assert jobs[0]["checks"]["guidelines"]["compliant"] == True
    assert jobs[0]["checks"]["guidelines"]["processingStatus"] == "RUNNING"
    assert "metrics" in jobs[0]["checks"]["guidelines"]


def test_it_gets_a_single_job(jobs_table, jobs_table_name, sfn, state_machine, clauses_table, clauses_for,
                              faker: Faker, jobs_index):
  from unittest.mock import patch, MagicMock
  from model import ContractType, Job, Workflow
  from datetime import datetime, timezone

  # Mock contract type repository to return a valid active contract type
  with patch.object(jobs_index, 'contract_type_repository') as mock_contract_repo, \
       patch.object(jobs_index, 'workflows_repository') as mock_workflows_repo, \
       patch.object(jobs_index, 'jobs_repository') as mock_jobs_repo, \
       patch.object(jobs_index, 'clauses_repository') as mock_clauses_repo:

    mock_contract_type = ContractType(
      contract_type_id="service-agreement",
      name="Service Agreement",
      description="Service agreement contracts",
      company_party_type="Customer",
      other_party_type="Service Provider",
      is_active=True,
      created_at="2024-01-01T00:00:00Z",
      updated_at="2024-01-01T00:00:00Z"
    )
    mock_contract_repo.get_contract_type.return_value = mock_contract_type

    # Mock workflows repository for post_job
    mock_execution_id = "test-execution-id"
    mock_job_id = "test-job-id"
    mock_workflows_repo.start_execution.return_value = mock_execution_id
    mock_workflows_repo.to_job_id.return_value = mock_job_id
    mock_workflows_repo.to_execution_id.return_value = mock_execution_id

    # Mock execution details
    mock_start_date = datetime.now(timezone.utc)
    mock_execution_details = Workflow(
      id=mock_execution_id,
      state_machine_id="arn:aws:states:us-east-1:123456789012:stateMachine:test",
      status="RUNNING",
      start_date=mock_start_date,
      end_date=None
    )
    mock_workflows_repo.get_state_machine_execution_details.return_value = mock_execution_details

    # Mock jobs repository for post_job
    mock_jobs_repo.record_job.return_value = None

    get_job = jobs_index.get_job
    post_job = jobs_index.post_job
    PostJobRequest = jobs_index.PostJobRequest

    # given
    a_compliant_status = faker.boolean()
    an_analysis = faker.paragraph()

    # given a job was started
    response = post_job(PostJobRequest(document_s3_key="file.pdf", contract_type_id="service-agreement"))
    job_id = response["id"]

    # Mock the job for get_job
    mock_job = Job(
      id=job_id,
      document_s3_key="file.pdf",
      contract_type_id="service-agreement",
      description=None,
      output_language="pt_BR",
      guidelines_compliant=False,
      legislation_compliant=None,
      total_clause_types_by_risk={
        "high": {"quantity": 1, "threshold": 0},
        "medium": {"quantity": 1, "threshold": 1},
        "low": {"quantity": 1, "threshold": 3},
        "none": {"quantity": 0}
      },
      total_compliance_by_impact={
        "high": {
          "compliant": {"quantity": 1, "risk": "none"},
          "missing": {"quantity": 0, "risk": "high"},
          "non_compliant": {"quantity": 0, "risk": "high"}
        },
        "medium": {
          "compliant": {"quantity": 1, "risk": "none"},
          "missing": {"quantity": 0, "risk": "high"},
          "non_compliant": {"quantity": 0, "risk": "medium"}
        },
        "low": {
          "compliant": {"quantity": 1, "risk": "none"},
          "missing": {"quantity": 0, "risk": "medium"},
          "non_compliant": {"quantity": 0, "risk": "low"}
        }
      },
      unknown_total=0
    )
    mock_jobs_repo.get_job.return_value = mock_job

    # Mock clauses
    mock_clauses = clauses_for(job_id, _additional_checks=AdditionalChecks(
        legislation_check=LegislationCheck(compliant=a_compliant_status, analysis=an_analysis)))
    mock_clauses_repo.get_clauses.return_value = mock_clauses

    # when we get its details
    job = get_job(job_id)

    # then
    assert len(job["clauses"]) == 3
    assert sorted(job["clauses"][0].keys()) == ["additionalChecks", "clauseNumber", "jobId", "text", "types"]
    assert sorted(job["clauses"][0]["types"][0].keys()) == ["analysis", "classificationAnalysis", "compliant", "level",
                                                            "typeId", "typeName"]
    assert job["clauses"][0]["additionalChecks"]["legislationCheck"]["compliant"] == a_compliant_status
    assert job["clauses"][0]["additionalChecks"]["legislationCheck"]["analysis"] == an_analysis
    assert job["contractTypeId"] == "service-agreement"
    
    # Assert checks object structure
    assert "checks" in job
    assert "guidelines" in job["checks"]
    assert job["checks"]["guidelines"]["compliant"] == False
    assert job["checks"]["guidelines"]["processingStatus"] == "RUNNING"
    assert "metrics" in job["checks"]["guidelines"]
    assert job["checks"]["guidelines"]["metrics"]["totalClauseTypesByRisk"]["high"]["quantity"] == 1