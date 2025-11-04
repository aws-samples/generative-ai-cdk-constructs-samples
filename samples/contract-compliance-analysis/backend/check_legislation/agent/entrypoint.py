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

import os
import logging
import sys
from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.telemetry import StrandsTelemetry

from schema import CheckLegislationRequest, CheckLegislationResponse, Evaluation, CheckLegislationResponseDict
from model import Clause, CheckedClause, LegislationCheck, AdditionalChecks
from repository import ClauseRepository
from repository.factory import RepositoryFactory
from agents import AgentArchitecture
from agents.factory import AgentFactory


strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_console_exporter()

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

CLAUSES_TABLE_NAME = os.environ["CLAUSES_TABLE_NAME"]

app = BedrockAgentCoreApp()

def _invoke(clauses_repository: ClauseRepository, agent_architecture: AgentArchitecture,
            request: CheckLegislationRequest) -> CheckLegislationResponse:
  try:
    logger.info(f"Starting legislation check for job {request.job_id}, clause {request.clause_number}")
    
    clause: Clause = clauses_repository.get_clause(job_id=request.job_id, clause_number=request.clause_number)
    logger.info(f"Retrieved clause: {clause.text[:100]}...")

    result: LegislationCheck = agent_architecture.analyze_clause(request, clause)
    logger.info(f"Analysis complete - compliant: {result.compliant}")

    checked_clause = CheckedClause(
      job_id=request.job_id,
      clause_number=int(request.clause_number),
      text=clause.text,
      additional_checks=AdditionalChecks(
        legislation_check=LegislationCheck(compliant=result.compliant, analysis=result.analysis)
      )
    )

    logger.info(f"Updating DynamoDB for job {request.job_id}, clause {request.clause_number}")
    clauses_repository.update_legislation_checks(checked_clause)
    logger.info("DynamoDB update successful")

    if os.getenv("TEST_LOCAL"):
      # when running locally we will augment the return with evals data
      return CheckLegislationResponse(
        JobId=request.job_id, ClauseNumber=request.clause_number,
        Evaluation=Evaluation(
          Status="OK",
          Compliant=result.compliant,
          Analysis=result.analysis,
        )
      )

    return CheckLegislationResponse(
      JobId=request.job_id, ClauseNumber=request.clause_number,
      Evaluation=Evaluation(Status="OK")
    )

  except Exception as e:
    logger.exception("Error processing request", exc_info=e)

    return CheckLegislationResponse(
      JobId=request.job_id, ClauseNumber=request.clause_number,
      Evaluation=Evaluation(Status="ERROR", Message=str(e))
    )


@app.entrypoint
def invoke(payload: Any) -> CheckLegislationResponseDict:
    """Process user input and return a response"""
    logger.info("Received check legislation request")
    logger.debug(f"Payload: {payload}")

    request = CheckLegislationRequest.model_validate(payload)

    # Create repository instances using factory
    clauses_repository = RepositoryFactory.create_clause_repository(CLAUSES_TABLE_NAME)

    agent_architecture = AgentFactory.create_agent_architecture(request.legislation_check_config.agent_architecture)

    response = _invoke(clauses_repository, agent_architecture, request)

    logger.info(
    f"Agent completed for job {request.job_id} clause {request.clause_number} and legislation {request.legislation_check_config.law_id}")

    return response.model_dump()


if __name__ == "__main__":
  app.run()
