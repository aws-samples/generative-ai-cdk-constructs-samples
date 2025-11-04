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

from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal, List, Optional, Dict
import re


class ContractType(BaseModel):
  contract_type_id: str
  name: str
  description: str
  company_party_type: str
  other_party_type: str
  high_risk_threshold: int = 0
  medium_risk_threshold: int = 1
  low_risk_threshold: int = 3
  is_active: bool = True
  default_language: str = "en"
  created_at: str
  updated_at: str


class CommonJobAttributes(BaseModel):
  total_clause_types_by_risk: Any | None = None
  total_compliance_by_impact: Any | None = None
  unknown_total: int | None = None
  guidelines_compliant: bool | None = None
  legislation_compliant: bool | None = None


class Job(CommonJobAttributes):
  id: str
  document_s3_key: str
  contract_type_id: str
  description: Optional[str] = None
  legislation_check_execution_arn: Optional[str] = None


class Workflow(BaseModel):
  state_machine_id: str  # this is an abstraction for the state machine ARN
  id: str  # this is an abstraction for the execution ARN
  status: Literal[
    "ABORTED", "FAILED", "PENDING_REDRIVE", "RUNNING", "SUCCEEDED", "TIMED_OUT"
  ]
  start_date: datetime

  end_date: Optional[datetime] = None
  input_data: Optional[Dict[str, Any]] = None


WorkflowId = str  # this is an abstraction for the execution arn


class ClauseType(BaseModel):
  type_id: str
  level: Optional[str] = None
  type_name: Optional[str] = None
  analysis: Optional[str] = None
  classification_analysis: Optional[str] = None
  compliant: Optional[bool] = None


class Check(BaseModel):
  compliant: bool
  analysis: Optional[str] = None


class LegislationCheck(Check): ...

class AdditionalChecks(BaseModel):
  legislation_check: Optional[LegislationCheck] = None
  # eventually we can have other types of checks


class Clause(BaseModel):
  job_id: str
  clause_number: int
  text: str
  types: List[ClauseType] = Field(default_factory=list)
  additional_checks: AdditionalChecks = Field(default_factory=AdditionalChecks)


class ImportJob(BaseModel):
  import_job_id: str
  execution_id: Optional[str] = None  # Step Functions execution ID
  document_s3_key: str
  contract_type_id: Optional[str] = None  # Set after contract type is created
  status: Literal["RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"] = "RUNNING"
  current_step: Optional[str] = None  # Current step in the state machine
  progress: int = Field(default=0, ge=0, le=100)  # 0-100
  error_message: Optional[str] = None
  created_at: str
  updated_at: str

  @field_validator('status', mode='before')
  @classmethod
  def validate_status(cls, v: Optional[str]) -> str:
    """Validate and normalize status, providing default for None values"""
    if v is None:
      return "RUNNING"  # Default status for None values from legacy data
    return v

  @field_validator('import_job_id')
  @classmethod
  def validate_import_job_id(cls, v: str) -> str:
    """Validate import job ID format"""
    if not v or not v.strip():
      raise ValueError("Import job ID is required")

    # Basic format validation - should be a valid identifier
    if not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
      raise ValueError("Import job ID must contain only alphanumeric characters, hyphens, and underscores")

    return v.strip()

  @field_validator('document_s3_key')
  @classmethod
  def validate_document_s3_key(cls, v: str) -> str:
    """Validate S3 key format"""
    if not v or not v.strip():
      raise ValueError("Document S3 key is required")

    return v.strip()

  @field_validator('error_message')
  @classmethod
  def validate_error_message(cls, v: Optional[str]) -> Optional[str]:
    """Validate and truncate error message if needed"""
    if v is None:
      return v

    v = v.strip()
    if not v:
      return None

    # Truncate long error messages to prevent DynamoDB item size issues
    if len(v) > 1000:
      return v[:997] + "..."

    return v


class Guideline(BaseModel):
  contract_type_id: str
  clause_type_id: Optional[str] = Field(None, max_length=50)
  name: str = Field(..., min_length=1, max_length=200)
  standard_wording: str = Field(..., min_length=1, max_length=2000)
  level: Literal["low", "medium", "high"]
  evaluation_questions: List[str] = Field(..., min_length=1, max_length=10)
  examples: List[str] = Field(default_factory=list, max_length=20)
  created_at: Optional[str] = None
  updated_at: Optional[str] = None

  @field_validator('clause_type_id')
  @classmethod
  def validate_clause_type_id(cls, v: Optional[str]) -> Optional[str]:
    """Validate clause type ID format (positive integers as strings)"""
    # Allow None or empty string for auto-generation
    if not v:
      return v

    # Check if it's a valid positive integer string
    try:
      int_value = int(v)
      if int_value <= 0:
        raise ValueError("Clause type ID must be a positive integer")
    except ValueError:
      raise ValueError("Clause type ID must be a positive integer")

    return v

  @field_validator('name')
  @classmethod
  def validate_name(cls, v: str) -> str:
    """Validate and normalize guideline name"""
    if not v or not v.strip():
      raise ValueError("Guideline name is required")

    return v.strip()

  @field_validator('standard_wording')
  @classmethod
  def validate_standard_wording(cls, v: str) -> str:
    """Validate and normalize standard wording"""
    if not v or not v.strip():
      raise ValueError("Standard wording is required")

    return v.strip()

  @field_validator('evaluation_questions')
  @classmethod
  def validate_evaluation_questions(cls, v: List[str]) -> List[str]:
    """Validate evaluation questions"""
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
