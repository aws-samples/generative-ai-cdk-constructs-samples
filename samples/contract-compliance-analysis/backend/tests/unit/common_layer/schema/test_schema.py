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

from schema import PostJobRequest, ClauseResponse, StartWorkflowRequest, PostJobResponse, CheckResult, GuidelinesMetrics
from model import Job

def test_it_fails_loading_invalid_additional_checks():
  # given
  request = {
    "documentS3Key": "foo/bar.pdf",
    "additionalChecks": {
      "legislationId": "foo"
    }
  }

  with pytest.raises(ValueError):
    PostJobRequest.model_validate(request)

def test_it_loads_from_attributes(clause):
  clause_response = ClauseResponse.model_validate(clause)

  assert clause_response.job_id == clause.job_id
  assert clause_response.clause_number == clause.clause_number
  assert clause_response.text == clause.text
  assert len(clause_response.types) == len(clause.types)
  assert clause_response.types[0].type_id == clause.types[0].type_id
  assert clause_response.types[0].type_name == clause.types[0].type_name
  assert clause_response.types[0].analysis == clause.types[0].analysis
  assert clause_response.types[0].compliant == clause.types[0].compliant

  assert clause_response.model_dump(by_alias=True) == {
    "jobId": clause.job_id,
    "clauseNumber": clause.clause_number,
    "text": clause.text,
    "types": [
      {
        "typeId": type.type_id,
        "typeName": type.type_name,
        "analysis": type.analysis,
        "classificationAnalysis": type.classification_analysis,
        "level": type.level,
        "compliant": type.compliant
      }
      for type in clause.types
    ],
    "additionalChecks": {
      "legislationCheck": {
        "analysis": clause.additional_checks.legislation_check.analysis,
        "compliant": clause.additional_checks.legislation_check.compliant
      }
    }
  }


def test_check_result_with_metrics():
  """Test CheckResult with metrics field"""
  metrics_data = {
    "totalClauseTypesByRisk": {
      "high": {"quantity": 1, "threshold": 0},
      "medium": {"quantity": 0, "threshold": 1},
      "low": {"quantity": 0, "threshold": 3},
      "none": {"quantity": 0}
    },
    "totalComplianceByImpact": {
      "high": {"compliant": {"quantity": 0, "risk": "none"}, "missing": {"quantity": 1, "risk": "high"}, "non_compliant": {"quantity": 0, "risk": "high"}},
      "medium": {"compliant": {"quantity": 0, "risk": "none"}, "missing": {"quantity": 0, "risk": "high"}, "non_compliant": {"quantity": 0, "risk": "medium"}},
      "low": {"compliant": {"quantity": 0, "risk": "none"}, "missing": {"quantity": 0, "risk": "medium"}, "non_compliant": {"quantity": 0, "risk": "low"}}
    },
    "unknownTotal": 0
  }
  
  check_result = CheckResult(
    compliant=False,
    processingStatus="SUCCEEDED",
    metrics=GuidelinesMetrics.model_validate(metrics_data)
  )
  
  assert check_result.compliant == False
  assert check_result.processing_status == "SUCCEEDED"
  assert check_result.metrics is not None
  assert check_result.metrics.unknown_total == 0


def test_check_result_serialization_with_metrics():
  """Test CheckResult serialization with metrics using aliases"""
  metrics_data = {
    "totalClauseTypesByRisk": {
      "high": {"quantity": 1, "threshold": 0},
      "medium": {"quantity": 0, "threshold": 1},
      "low": {"quantity": 0, "threshold": 3},
      "none": {"quantity": 0}
    },
    "totalComplianceByImpact": {
      "high": {"compliant": {"quantity": 0, "risk": "none"}, "missing": {"quantity": 1, "risk": "high"}, "non_compliant": {"quantity": 0, "risk": "high"}},
      "medium": {"compliant": {"quantity": 0, "risk": "none"}, "missing": {"quantity": 0, "risk": "high"}, "non_compliant": {"quantity": 0, "risk": "medium"}},
      "low": {"compliant": {"quantity": 0, "risk": "none"}, "missing": {"quantity": 0, "risk": "medium"}, "non_compliant": {"quantity": 0, "risk": "low"}}
    },
    "unknownTotal": 0
  }
  
  check_result = CheckResult(
    compliant=True,
    processingStatus="SUCCEEDED",
    metrics=GuidelinesMetrics.model_validate(metrics_data)
  )
  
  serialized = check_result.model_dump(by_alias=True)
  
  assert serialized["compliant"] == True
  assert serialized["processingStatus"] == "SUCCEEDED"
  assert "metrics" in serialized
  assert serialized["metrics"]["totalClauseTypesByRisk"]["high"]["quantity"] == 1
  assert serialized["metrics"]["unknownTotal"] == 0


def test_check_result_without_metrics():
  """Test CheckResult without metrics (legislation check)"""
  check_result = CheckResult(
    compliant=True,
    processingStatus="SUCCEEDED"
  )
  
  assert check_result.compliant == True
  assert check_result.processing_status == "SUCCEEDED"
  assert check_result.metrics is None


def test_post_job_request_requires_contract_type_id():
  """Test that PostJobRequest requires contract_type_id field"""
  # Missing contract_type_id should raise validation error
  request_without_contract_type = {
    "documentS3Key": "foo/bar.pdf"
  }

  with pytest.raises(ValueError, match="Field required"):
    PostJobRequest.model_validate(request_without_contract_type)


def test_post_job_request_validates_with_contract_type_id():
  """Test that PostJobRequest validates correctly with contract_type_id"""
  request = {
    "documentS3Key": "foo/bar.pdf",
    "contractTypeId": "service-agreement"
  }

  validated_request = PostJobRequest.model_validate(request)

  assert validated_request.document_s3_key == "foo/bar.pdf"
  assert validated_request.contract_type_id == "service-agreement"
  assert validated_request.output_language == "pt_BR"  # default value


def test_post_job_request_with_all_fields():
  """Test PostJobRequest with all fields including contract_type_id"""
  request = {
    "documentS3Key": "foo/bar.pdf",
    "contractTypeId": "employment-contract",
    "jobDescription": "Test contract analysis",
    "outputLanguage": "en",
    "additionalChecks": {
      "legislationCheck": {
        "legislationId": "123"
      }
    }
  }

  validated_request = PostJobRequest.model_validate(request)

  assert validated_request.document_s3_key == "foo/bar.pdf"
  assert validated_request.contract_type_id == "employment-contract"
  assert validated_request.description == "Test contract analysis"
  assert validated_request.output_language == "en"
  assert validated_request.additional_checks.legislationCheck.LegislationId == "123"


def test_start_workflow_request_requires_contract_type_id():
  """Test that StartWorkflowRequest requires contract_type_id field"""
  # Missing contract_type_id should raise validation error
  request_without_contract_type = {
    "document_s3_path": "s3://bucket/file.pdf"
  }

  with pytest.raises(ValueError, match="Field required"):
    StartWorkflowRequest.model_validate(request_without_contract_type)


def test_start_workflow_request_validates_with_contract_type_id():
  """Test that StartWorkflowRequest validates correctly with contract_type_id"""
  request = {
    "document_s3_path": "s3://bucket/file.pdf",
    "ContractTypeId": "service-agreement"
  }

  validated_request = StartWorkflowRequest.model_validate(request)

  assert validated_request.document_s3_path == "s3://bucket/file.pdf"
  assert validated_request.contract_type_id == "service-agreement"
  assert validated_request.output_language == "pt_BR"  # default value


def test_start_workflow_request_with_all_fields():
  """Test StartWorkflowRequest with all fields including contract_type_id"""
  request = {
    "document_s3_path": "s3://bucket/file.pdf",
    "ContractTypeId": "nda-contract",
    "OutputLanguage": "es",
    "AdditionalChecks": {
      "legislationCheck": {
        "legislationId": "456"
      }
    }
  }

  validated_request = StartWorkflowRequest.model_validate(request)

  assert validated_request.document_s3_path == "s3://bucket/file.pdf"
  assert validated_request.contract_type_id == "nda-contract"
  assert validated_request.output_language == "es"
  assert validated_request.additional_checks.legislationCheck.LegislationId == "456"


def test_post_job_response_includes_contract_type_id():
  """Test that PostJobResponse includes contract_type_id in serialization"""
  response = PostJobResponse(
    id="job-123",
    document_s3_key="test.pdf",
    contract_type_id="service-agreement",
    start_date="2025-01-01T00:00:00Z"
  )

  serialized = response.model_dump(by_alias=True)

  assert serialized["id"] == "job-123"
  assert serialized["documentS3Key"] == "test.pdf"
  assert serialized["contractTypeId"] == "service-agreement"
  assert serialized["startDate"] == "2025-01-01T00:00:00Z"


def test_job_model_requires_contract_type_id():
  """Test that Job model requires contract_type_id field"""
  # Missing contract_type_id should raise validation error
  with pytest.raises(ValueError, match="Field required"):
    Job(
      id="job-123",
      document_s3_key="test.pdf"
    )


def test_job_model_validates_with_contract_type_id():
  """Test that Job model validates correctly with contract_type_id"""
  job = Job(
    id="job-123",
    document_s3_key="test.pdf",
    contract_type_id="service-agreement"
  )

  assert job.id == "job-123"
  assert job.document_s3_key == "test.pdf"
  assert job.contract_type_id == "service-agreement"
  assert job.description is None  # default value


def test_job_model_with_all_fields():
  """Test Job model with all fields including contract_type_id"""
  job = Job(
    id="job-123",
    document_s3_key="test.pdf",
    contract_type_id="employment-contract",
    description="Test job description"
  )

  assert job.id == "job-123"
  assert job.document_s3_key == "test.pdf"
  assert job.contract_type_id == "employment-contract"
  assert job.description == "Test job description"
