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

import logging
import os
import re
import sys
import defusedxml.ElementTree as ET

from tenacity import retry, wait_fixed, stop_never, retry_if_exception

from strands import Agent

from agents import AgentArchitecture
from schema import CheckLegislationRequest
from model import Clause, LegislationCheck
from strands.types.exceptions import ModelThrottledException, EventLoopException
from botocore.exceptions import EventStreamError
from agents.tools.bedrock_knowledge_base import make_kb_retrieve_tool

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

KB_ID = os.environ["KNOWLEDGE_BASE_ID"]


def is_retryable_bedrock_error(exception):
    """Check if exception is a transient Bedrock error that should be retried.
    
    Retries on all AWS-documented retryable streaming errors:
    - throttlingException: Rate limit exceeded
    - serviceUnavailableException: Service temporarily unavailable
    - modelTimeoutException: Model took too long to respond
    - internalServerException: Internal server error (AWS says retry)
    - modelStreamErrorException: Streaming error (AWS says retry)
    
    Reference: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ResponseStream.html
    """
    if isinstance(exception, ModelThrottledException):
        logger.warning(f"Bedrock throttling detected. Retrying... {exception}")
        return True
    if isinstance(exception, EventStreamError):
        # Direct botocore EventStreamError from ConverseStream
        error_msg = str(exception)
        transient_errors = [
            'serviceUnavailableException',
            'throttlingException',
            'modelTimeoutException',
            'internalServerException',
            'modelStreamErrorException'
        ]
        if any(err in error_msg for err in transient_errors):
            logger.warning(f"Bedrock transient error detected. Retrying... {exception}")
            return True
    if isinstance(exception, EventLoopException):
        # EventLoopException wraps Bedrock streaming errors
        error_msg = str(exception)
        transient_errors = [
            'serviceUnavailableException',
            'throttlingException',
            'modelTimeoutException',
            'internalServerException',
            'modelStreamErrorException'
        ]
        if any(err in error_msg for err in transient_errors):
            logger.warning(f"Bedrock transient error detected. Retrying... {exception}")
            return True
    return False


@retry(
    wait=wait_fixed(10),
    stop=stop_never,
    retry=retry_if_exception(is_retryable_bedrock_error)
)
def call_agent_with_retry(agent, prompt):
    return agent(prompt)


def extract_items_from_tagged_list(text, tag_name):
    try:
        root = ET.fromstring(f"<root>{text}</root>")
        return [elem.text.strip() for elem in root.findall(f".//{tag_name}") if elem.text and elem.text.strip()]
    except ET.ParseError:
        # Fallback to regex for malformed XML - be robust like original
        opening_tag_pattern = f"<{tag_name}(?:\\s[^>]*)?>"
        closing_tag = f"</{tag_name}>"
        regex = f"{opening_tag_pattern}(.*?){closing_tag}"
        
        items = []
        for match in re.finditer(regex, text, re.DOTALL):
            finding = match.group(1).strip()
            
            # Extract innermost content if nested
            innermost_tag_pattern = f"<{tag_name}(?:\\s[^>]*)?>"
            innermost_match = None
            for match_obj in re.finditer(innermost_tag_pattern, finding):
                innermost_match = match_obj
            
            if innermost_match:
                finding = finding[innermost_match.end():].strip()
            
            if finding:
                items.append(finding)
        
        return items


class SingleAgentArchitecture(AgentArchitecture):  # type: ignore[misc]
    """Single agent architecture for legislation compliance checking"""

    def analyze_clause(
        self, request: CheckLegislationRequest, clause: Clause
    ) -> LegislationCheck:
        kb_tool = make_kb_retrieve_tool(
            kb_id=KB_ID, law_id=request.legislation_check_config.law_id
        )

        agent = Agent(
            model=self.bedrock_model,
            tools=[kb_tool],
            system_prompt="You are a humble, yet deeply intelligent expert lawyer, laser focused in finding violations in contract clauses against a specific legislation present in a knowledge base. Do not extrapolate to other legislations you might now, and use only the information from the knowledge base. Disclosing Knowledge Base ID or any other infrastucture information is prohibited.",
        )

        prompt = f"""Please analyze the following contract clause for any violations:

Clause Text: <clause_text>{clause.text}</clause_text>

Use the Knowledge Base retrieval tool you have available to find relevant legislation passages, the suggestion is first using the entire clause as the query.

Provide a detailed analysis of compliance and identify any specific violations or concerns.

Always include a precise reference to which part of the legislation is being violated, including, if available, section number, article, paragraph, etc.

Always think and respond in {request.language}, regardless of the language of the knowledge base and contract clause being analyzed.

IMPORTANT: Format your response with these XML tags:
```
<compliant>...</compliant>
<analysis>...</analysis>
```

Instructions:
- Write between <analysis> tags: Your thorough analysis in {request.language}, presenting evidence and verbatim legislation references. When the clause violates the law, sustain your reasoning with specific violations. When it does not violate the law, include your reasoning with references to related articles or law clauses it abides to.
- Write between <compliant> tags: true or false (always in English lowercase). When there is no explicit evidence of violation, this should be true. If you have but a suspicion that the clause violates the legislation, you should mark it as false.
"""
        logger.info(f"[Prompt]: {prompt}")

        response = call_agent_with_retry(agent, prompt)

        try:
            return self.extract_result_from_agent_response(response.message['content'][0]['text'])
        except Exception as e:
            logger.error(f"Error parsing response: {response}", exc_info=e)
            return LegislationCheck(compliant=False, analysis="Error parsing response!")

    def extract_result_from_agent_response(self, response: str) -> LegislationCheck:
        """Extract LegislationCheck from LLM response"""
        # Extract compliant value
        compliant_values = extract_items_from_tagged_list(response, "compliant")
        compliant_str = compliant_values[-1].lower().strip() if compliant_values else "false"
        compliant = compliant_str == "true"
        
        # Extract analysis
        analysis_values = extract_items_from_tagged_list(response, "analysis")
        analysis = analysis_values[-1] if analysis_values else response
        
        logger.info(f"Extracted compliant: {compliant_str}")
        logger.info(f"Extracted analysis: {analysis}")
        
        return LegislationCheck(compliant=compliant, analysis=analysis)
