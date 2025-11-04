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

from pydantic import BaseModel, Field


class LegislationCheck(BaseModel):
  """
  Checks if a given contract clause violates a given Legislation.

  When the contract clause violates one or more items of the law, it will be marked non-compliant (i.e. compliant == False).
  """
  compliant: bool = Field(...,
                          description="Indicates whether the contract clause is compliant with the legislation it's being checked against. When there is no explicit evidence of violation, this should be True. If you have but a suspicion that the clause violates the legislation, you should mark it as False.")
  analysis: str = Field(...,
                        description="A thorough analysis, presenting evidence and verbatim legislation references, sustaining that the clause under evaluation violates the law. This might contain multiple violations. When it does not violate the law, then also include your reasoning with the references of related articles or law clauses it abides to that you think are relevant.")


class Clause(BaseModel):
  job_id: str
  clause_number: int
  text: str


class AdditionalChecks(BaseModel):
  legislation_check: LegislationCheck


class CheckedClause(Clause):
  additional_checks: AdditionalChecks = Field(default_factory=AdditionalChecks)
