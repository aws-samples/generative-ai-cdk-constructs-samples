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

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal, List, Optional, Dict, Any


class ResponseModel(BaseModel):
  model_config = ConfigDict(
    populate_by_name=True,
    from_attributes=True
  )


class LegislationCheck(BaseModel):
  LegislationId: str = Field(..., alias="legislationId")
  AgentArchitecture: Optional[Literal["Single"]] = Field("Single", alias="agentArchitecture")


class AdditionalChecks(BaseModel):
  model_config = ConfigDict(
    extra='forbid'
  )
  legislationCheck: Optional[LegislationCheck] = None


class LegislationCheckResponse(ResponseModel):
  compliant: bool
  analysis: Optional[str] = None


class AdditionalChecksResponse(ResponseModel):
  legislation_check: Optional[LegislationCheckResponse] = Field(None, alias="legislationCheck")

class ClauseTypeResponse(ResponseModel):
  type_id: str = Field(..., alias="typeId")
  level: Optional[str] = None
  type_name: Optional[str] = Field(None, alias="typeName")
  analysis: Optional[str] = None
  classification_analysis: Optional[str] = Field(None, alias="classificationAnalysis")
  compliant: Optional[bool] = None


class ClauseResponse(ResponseModel):
  job_id: str = Field(..., alias="jobId")
  clause_number: int = Field(..., alias="clauseNumber")
  text: str
  types: List[ClauseTypeResponse] = Field(default_factory=list)
  additional_checks: AdditionalChecksResponse = Field(default_factory=lambda: AdditionalChecksResponse(legislationCheck=None), alias="additionalChecks")


class PostJobRequest(ResponseModel):
  document_s3_key: str = Field(..., alias="documentS3Key")
  contract_type_id: str = Field(..., alias="contractTypeId")
  description: Optional[str] = Field(None, alias="jobDescription")
  output_language: Literal["pt_BR", "en", "es"] = Field("pt_BR", alias="outputLanguage")
  additional_checks: Optional[AdditionalChecks] = Field(None, alias="additionalChecks")


class StartWorkflowRequest(BaseModel):
  document_s3_path: str
  contract_type_id: str = Field(..., alias="ContractTypeId")
  output_language: Literal["pt_BR", "en", "es"] = Field("pt_BR", alias="OutputLanguage")
  additional_checks: Optional[AdditionalChecks] = Field(None, alias="AdditionalChecks")

  model_config = ConfigDict(
    populate_by_name=True,  # allow both 'id' and 'job_id' on input
    extra='forbid',  # example: whatever you had before
    validate_assignment=True  # example
  )


class PostJobResponse(ResponseModel):
  id: str
  document_s3_key: str = Field(..., alias="documentS3Key")
  contract_type_id: str = Field(..., alias="contractTypeId")
  start_date: str = Field(..., alias="startDate")


class RiskAttributes(BaseModel):
  quantity: int
  threshold: Optional[int]

class SimpleRiskAttributes(BaseModel):
  quantity: int

class TotalClauseTypesByRisk(BaseModel):
  high: RiskAttributes
  medium: RiskAttributes
  low: RiskAttributes
  none: SimpleRiskAttributes


class ComplianceAttributes(BaseModel):
    quantity: int
    risk: str

class ComplianceStatus(BaseModel):
    compliant: ComplianceAttributes
    missing: ComplianceAttributes
    non_compliant: ComplianceAttributes

class TotalComplianceByImpact(BaseModel):
    high: ComplianceStatus
    low: ComplianceStatus
    medium: ComplianceStatus


class GuidelinesMetrics(BaseModel):
  total_clause_types_by_risk: TotalClauseTypesByRisk = Field(..., alias="totalClauseTypesByRisk")
  total_compliance_by_impact: TotalComplianceByImpact = Field(..., alias="totalComplianceByImpact")
  unknown_total: int = Field(..., alias="unknownTotal")


class CheckResult(BaseModel):
  compliant: Optional[bool]
  processing_status: str = Field(..., alias="processingStatus")
  metrics: Optional[GuidelinesMetrics] = None


class ChecksResponse(BaseModel):
  guidelines: CheckResult
  legislation: Optional[CheckResult] = None


class BaseJobRespose(PostJobResponse):
  description: Optional[str] = Field(None, alias="jobDescription")
  end_date: Optional[str] = Field(None, alias="endDate")
  clauses: List[ClauseResponse] = Field(default_factory=list)
  checks: ChecksResponse


class GetJobResponse(BaseJobRespose):
  pass


class ContractTypeRequest(ResponseModel):
  name: str
  description: str
  company_party_type: str = Field(..., alias="companyPartyType")
  other_party_type: str = Field(..., alias="otherPartyType")
  high_risk_threshold: int = Field(0, alias="highRiskThreshold")
  medium_risk_threshold: int = Field(1, alias="mediumRiskThreshold")
  low_risk_threshold: int = Field(3, alias="lowRiskThreshold")
  is_active: bool = Field(True, alias="isActive")
  default_language: str = Field("en", alias="defaultLanguage")


class ContractTypeResponse(ResponseModel):
  contract_type_id: str = Field(..., alias="contractTypeId")
  name: str
  description: str
  company_party_type: str = Field(..., alias="companyPartyType")
  other_party_type: str = Field(..., alias="otherPartyType")
  high_risk_threshold: int = Field(..., alias="highRiskThreshold")
  medium_risk_threshold: int = Field(..., alias="mediumRiskThreshold")
  low_risk_threshold: int = Field(..., alias="lowRiskThreshold")
  is_active: bool = Field(..., alias="isActive")
  default_language: str = Field(..., alias="defaultLanguage")
  created_at: str = Field(..., alias="createdAt")
  updated_at: str = Field(..., alias="updatedAt")
  # Import-related fields
  is_imported: Optional[bool] = Field(None, alias="isImported")
  import_source_document: Optional[str] = Field(None, alias="importSourceDocument")


# Guidelines API Schema Models
class GuidelineResponse(ResponseModel):
  contract_type_id: str = Field(..., alias="contractTypeId")
  clause_type_id: str = Field(..., alias="clauseTypeId")
  name: str
  standard_wording: str = Field(..., alias="standardWording")
  level: Literal["low", "medium", "high"]
  evaluation_questions: List[str] = Field(..., alias="evaluationQuestions")
  examples: List[str]
  created_at: Optional[str] = Field(None, alias="createdAt")
  updated_at: Optional[str] = Field(None, alias="updatedAt")


class CreateGuidelineRequest(ResponseModel):
  contract_type_id: str = Field(..., alias="contractTypeId")
  # clause_type_id is now auto-generated, so it's not included in the request
  name: str = Field(..., min_length=1, max_length=200)
  standard_wording: str = Field(..., alias="standardWording", min_length=1, max_length=2000)
  level: Literal["low", "medium", "high"]
  evaluation_questions: List[str] = Field(..., alias="evaluationQuestions", min_length=1, max_length=10)
  examples: List[str] = Field(default_factory=list, max_length=20)

  @field_validator('name', 'standard_wording')
  @classmethod
  def validate_text_fields(cls, v: str) -> str:
    """Validate and normalize text fields"""
    if not v or not v.strip():
      raise ValueError("Field cannot be empty")
    return v.strip()

  @field_validator('evaluation_questions')
  @classmethod
  def validate_evaluation_questions(cls, v: List[str]) -> List[str]:
    """Validate evaluation questions"""
    validated_questions = []
    for i, question in enumerate(v):
      if not question or not question.strip():
        raise ValueError(f"Evaluation question {i + 1} cannot be empty")

      question = question.strip()
      if len(question) > 500:
        raise ValueError(f"Evaluation question {i + 1} must be 500 characters or less")

      validated_questions.append(question)

    return validated_questions

  @field_validator('examples')
  @classmethod
  def validate_examples(cls, v: List[str]) -> List[str]:
    """Validate and filter examples"""
    validated_examples = []
    for i, example in enumerate(v):
      if example and example.strip():  # Skip empty examples
        example = example.strip()
        if len(example) > 1000:
          raise ValueError(f"Example {i + 1} must be 1000 characters or less")
        validated_examples.append(example)

    return validated_examples


class UpdateGuidelineRequest(ResponseModel):
  name: Optional[str] = Field(None, min_length=1, max_length=200)
  standard_wording: Optional[str] = Field(None, alias="standardWording", min_length=1, max_length=2000)
  level: Optional[Literal["low", "medium", "high"]] = None
  evaluation_questions: Optional[List[str]] = Field(None, alias="evaluationQuestions", min_length=1, max_length=10)
  examples: Optional[List[str]] = Field(None, max_length=20)

  @field_validator('name', 'standard_wording')
  @classmethod
  def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
    """Validate and normalize text fields"""
    if v is not None:
      if not v.strip():
        raise ValueError("Field cannot be empty")
      return v.strip()
    return v

  @field_validator('evaluation_questions')
  @classmethod
  def validate_evaluation_questions(cls, v: Optional[List[str]]) -> Optional[List[str]]:
    """Validate evaluation questions"""
    if v is not None:
      if not v:
        raise ValueError("At least one evaluation question is required")

      validated_questions = []
      for i, question in enumerate(v):
        if not question or not question.strip():
          raise ValueError(f"Evaluation question {i + 1} cannot be empty")

        question = question.strip()
        if len(question) > 500:
          raise ValueError(f"Evaluation question {i + 1} must be 500 characters or less")

        validated_questions.append(question)

      return validated_questions
    return v

  @field_validator('examples')
  @classmethod
  def validate_examples(cls, v: Optional[List[str]]) -> Optional[List[str]]:
    """Validate and filter examples"""
    if v is not None:
      validated_examples = []
      for i, example in enumerate(v):
        if example and example.strip():  # Skip empty examples
          example = example.strip()
          if len(example) > 1000:
            raise ValueError(f"Example {i + 1} must be 1000 characters or less")
          validated_examples.append(example)

      return validated_examples
    return v


class GuidelinesListResponse(ResponseModel):
  guidelines: List[GuidelineResponse]
  last_evaluated_key: Optional[str] = Field(None, alias="lastEvaluatedKey")
  total_count: Optional[int] = Field(None, alias="totalCount")


# Import API Schema Models
class ImportContractTypeRequest(ResponseModel):
  document_s3_key: str = Field(..., alias="documentS3Key", min_length=1)
  description: Optional[str] = Field(None, max_length=500)

  @field_validator('document_s3_key')
  @classmethod
  def validate_document_s3_key(cls, v: str) -> str:
    """Validate S3 key format"""
    if not v or not v.strip():
      raise ValueError("Document S3 key is required")

    # Basic S3 key validation
    v = v.strip()
    if v.startswith('/') or v.endswith('/'):
      raise ValueError("S3 key cannot start or end with '/'")

    return v

  @field_validator('description')
  @classmethod
  def validate_description(cls, v: Optional[str]) -> Optional[str]:
    """Validate and normalize description"""
    if v is not None:
      v = v.strip()
      if not v:
        return None
      return v
    return v


class ImportContractTypeResponse(ResponseModel):
  import_job_id: str = Field(..., alias="importJobId")
  contract_type_id: str = Field(..., alias="contractTypeId")
  status: Literal["RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]

  @field_validator('status', mode='before')
  @classmethod
  def validate_status(cls, v: Optional[str]) -> str:
    """Validate and normalize status, providing default for None values"""
    if v is None:
      return "RUNNING"  # Default status for None values from legacy data
    return v


class ImportJobStatusResponse(ResponseModel):
  import_job_id: str = Field(..., alias="importJobId")
  status: Literal["RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]
  progress: int = Field(..., ge=0, le=100)
  contract_type_id: Optional[str] = Field(None, alias="contractTypeId")
  error_message: Optional[str] = Field(None, alias="errorMessage")
  current_step: Optional[str] = Field(None, alias="currentStep")
  created_at: str = Field(..., alias="createdAt")
  updated_at: str = Field(..., alias="updatedAt")

  @field_validator('status', mode='before')
  @classmethod
  def validate_status(cls, v: Optional[str]) -> str:
    """Validate and normalize status, providing default for None values"""
    if v is None:
      return "RUNNING"  # Default status for None values from legacy data
    return v


# AI Content Generation Schema Models
class GenerateQuestionsRequest(ResponseModel):
  standard_wording: str = Field(..., alias="standardWording", min_length=1, max_length=2000)
  contract_context: Optional[Dict[str, Any]] = Field(None, alias="contractContext")

  @field_validator('standard_wording')
  @classmethod
  def validate_standard_wording(cls, v: str) -> str:
    """Validate and normalize standard wording"""
    if not v or not v.strip():
      raise ValueError("Standard wording is required")
    return v.strip()


class GenerateQuestionsResponse(ResponseModel):
  questions: List[str] = Field(..., min_length=1, max_length=10)

  @field_validator('questions')
  @classmethod
  def validate_questions(cls, v: List[str]) -> List[str]:
    """Validate generated questions"""
    if not v:
      raise ValueError("At least one question must be generated")

    validated_questions = []
    for i, question in enumerate(v):
      if not question or not question.strip():
        raise ValueError(f"Generated question {i + 1} cannot be empty")

      question = question.strip()
      if len(question) > 500:
        raise ValueError(f"Generated question {i + 1} must be 500 characters or less")

      validated_questions.append(question)

    return validated_questions


class GenerateExamplesRequest(ResponseModel):
  standard_wording: str = Field(..., alias="standardWording", min_length=1, max_length=2000)
  contract_context: Optional[Dict[str, Any]] = Field(None, alias="contractContext")

  @field_validator('standard_wording')
  @classmethod
  def validate_standard_wording(cls, v: str) -> str:
    """Validate and normalize standard wording"""
    if not v or not v.strip():
      raise ValueError("Standard wording is required")
    return v.strip()


class GenerateExamplesResponse(ResponseModel):
  examples: List[str] = Field(..., min_length=2, max_length=4)

  @field_validator('examples')
  @classmethod
  def validate_examples(cls, v: List[str]) -> List[str]:
    """Validate generated examples"""
    if not v or len(v) < 2:
      raise ValueError("At least 2 examples must be generated")

    validated_examples = []
    for i, example in enumerate(v):
      if not example or not example.strip():
        raise ValueError(f"Generated example {i + 1} cannot be empty")

      example = example.strip()
      if len(example) > 1000:
        raise ValueError(f"Generated example {i + 1} must be 1000 characters or less")

      validated_examples.append(example)

    return validated_examples
