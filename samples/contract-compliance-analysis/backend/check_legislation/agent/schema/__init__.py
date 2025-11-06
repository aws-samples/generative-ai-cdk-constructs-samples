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

from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, Field, field_validator

type AgentArchitecture = Literal["Single", "Graph"]

class LegislationCheckConfig(BaseModel):
  law_id: str = Field(..., alias="legislationId")
  agent_architecture: Optional[AgentArchitecture] = Field("Single", alias="agentArchitecture")

  @field_validator("agent_architecture", mode="before")
  @classmethod
  def default_if_none_or_empty(cls, v):
    if v is None or (isinstance(v, str) and v.strip() == ""):
      return "Single"
    return v

class CheckLegislationRequest(BaseModel):
  job_id: str = Field(..., alias="JobId")
  clause_number: int = Field(..., alias="ClauseNumber")

  legislation_check_config: LegislationCheckConfig = Field(..., alias="LegislationCheck")

  # Optional fields
  language: str = Field("pt_BR", alias="OutputLanguage")

  @field_validator("language", mode="before")
  @classmethod
  def default_if_none_or_empty(cls, v):
    if v is None or (isinstance(v, str) and v.strip() == ""):
      return "pt_BR"
    return v

class Evaluation(BaseModel):
  Status: Literal["OK", "ERROR"]
  Message: Optional[str] = None
  Compliant: Optional[bool] = None
  Analysis: Optional[str] = None

class CheckLegislationResponse(BaseModel):
  JobId: str
  ClauseNumber: int
  Evaluation: Evaluation

class CheckLegislationResponseDict(TypedDict):
  JobId: str
  ClauseNumber: int
  Evaluation: Evaluation
