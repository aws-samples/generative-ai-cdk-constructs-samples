#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"


class RuleFinding(BaseModel):
    rule: str = Field(..., description="Rule ID")
    file: str = Field(..., description="File that the finding applies to.")
    snippet: str = Field(..., description="The non-compliant section of code")
    description: str = Field(..., description="Description of how the code violates the rule")
    suggestion: str = Field(..., description="Suggestion for fixing the issue")


class RuleEvaluation(BaseModel):
    complianceStatus: ComplianceStatus = Field(..., description="Whether the file is compliant with the rule or not.")
    findings: Optional[list[RuleFinding]] = Field(
        default_factory=list,
        description="List each non-compliant finding. Only include this section if there are non-compliant findings.",
    )


class EvaluationError(BaseModel):
    file: str = Field(..., description="File that the finding applies to.")
    error: str = Field(..., description="Error message")
    rules: Optional[list[str]] = Field(
        default_factory=list,
        description="List of rules that were evaluated when the error occurred.",
    )
