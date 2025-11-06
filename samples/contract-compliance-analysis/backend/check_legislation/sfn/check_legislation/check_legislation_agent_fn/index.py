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
from typing import Any, Literal, Optional

from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import event_parser

import boto3
from botocore.config import Config

logger = Logger()

class LegislationCheckConfig(BaseModel):
    legislationId: str
    agentArchitecture: Optional[str] = "Single"

class SfnIteratorEvent(BaseModel):
    JobId: str
    ClauseNumber: int
    LegislationCheck: LegislationCheckConfig
    OutputLanguage: str
    ExecutionName: Optional[str] = None


class Evaluation(BaseModel):
  Status: Literal["OK", "ERROR"]


class CheckLegislationResponse(BaseModel):
  JobId: str
  ClauseNumber: int
  Evaluation: Evaluation


@logger.inject_lambda_context(log_event=True)
@event_parser(model=SfnIteratorEvent)  #type: ignore[misc]
def lambda_handler(event: SfnIteratorEvent, context: LambdaContext) -> dict[str, Any]:
    """
    Lambda function to invoke Bedrock AgentCore runtime.

    Args:
        event: The input event from Step Functions
        context: Lambda context object

    Returns:
        CheckLegislationResponse
    """

    # Get the agent runtime ARN from environment variable
    agent_runtime_arn = os.environ.get('AGENT_RUNTIME_ARN')
    if not agent_runtime_arn:
        raise ValueError("AGENT_RUNTIME_ARN environment variable is required")

    # Initialize the Bedrock AgentCore client
    client = boto3.client('bedrock-agentcore', config=Config(    # type: ignore
        connect_timeout=180,
        read_timeout=600,
        retries={
            "max_attempts": 50,
            "mode": "adaptive"
        },
    ))

    try:
        # Prepare the payload - encode the entire event as JSON
        payload_json = event.model_dump_json()

        # Generate a runtime session ID from the execution name if available
        runtime_session_id = event.ExecutionName or context.aws_request_id

        logger.info("Calling agent")

        invoke_agent_response = client.invoke_agent_runtime(
            agentRuntimeArn=agent_runtime_arn,
            runtimeSessionId=runtime_session_id,
            payload=payload_json,
            qualifier='DEFAULT'
        )

        agent_response = invoke_agent_response["response"].read()

        logger.info(f"Completed execution with agent response: {agent_response}")

        result = CheckLegislationResponse.model_validate_json(agent_response)

        # Log the full result object for debugging
        logger.info(f"Agent result: {result}")
        logger.info(f"Agent evaluation: {result.Evaluation}")        

        # Check if agent returned an error and fail the Lambda
        if result.Evaluation.Status == "ERROR":
            error_msg = getattr(result.Evaluation, 'Message', 'Agent error')
            logger.error(f"Agent returned error: {error_msg}")
            raise RuntimeError(f"Agent failed: {error_msg}")

        return result.model_dump()

    except Exception as e:
        print(f"Error invoking AgentCore runtime: {str(e)}")
        raise e


if __name__ == "__main__":
    from uuid import uuid4
    from types import SimpleNamespace

    response = lambda_handler({"JobId": str(uuid4()), "ClauseNumber": "3"}, SimpleNamespace({"aws_request_id": str(uuid4())}))
    print(response["body"]["response"].read())
