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

import boto3
import logging
import os

from retrying import retry
from botocore.config import Config
from botocore.exceptions import ClientError
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

CLAUDE_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

bedrock_client = boto3.client('bedrock-runtime', config=Config(
    connect_timeout=180,
    read_timeout=180,
    retries={
        "max_attempts": 50,
        "mode": "adaptive",
    },
))

class BedrockRetryableError(Exception):
    """Custom exception for retryable Bedrock errors"""
    pass

@retry(
    wait_fixed=10000,  # 10 seconds between retries
    stop_max_attempt_number=None,  # Keep retrying indefinitely
    retry_on_exception=lambda ex: isinstance(ex, BedrockRetryableError),
)
def invoke_chain_with_retry(chain):
    """Invoke Bedrock with retry logic for throttling"""
    try:
        return chain.invoke({})
    except ClientError as exc:
        logger.warning(f"Bedrock ClientError: {exc}")

        if exc.response["Error"]["Code"] == "ThrottlingException":
            logger.warning("Bedrock throttling. Retrying...")
            raise BedrockRetryableError(str(exc))
        elif exc.response["Error"]["Code"] == "ModelTimeoutException":
            logger.warning("Bedrock ModelTimeoutException. Retrying...")
            raise BedrockRetryableError(str(exc))
        else:
            raise
    except bedrock_client.exceptions.ThrottlingException as throttlingExc:
        logger.warning("Bedrock ThrottlingException. Retrying...")
        raise BedrockRetryableError(str(throttlingExc))
    except bedrock_client.exceptions.ModelTimeoutException as timeoutExc:
        logger.warning("Bedrock ModelTimeoutException. Retrying...")
        raise BedrockRetryableError(str(timeoutExc))

def invoke_llm(prompt, model_id, temperature=0.5, top_k=None, top_p=0.8, max_new_tokens=4096, verbose=False):
    model_id = (model_id or CLAUDE_MODEL_ID)

    if verbose:
        logger.info(f"ModelId: {model_id}")
        logger.info(f"Prompt:\n{prompt}")

    model_kwargs = {
        'anthropic_version': 'bedrock-2023-05-31',
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_new_tokens,
    }
    if top_k:
        model_kwargs["top_k"] = top_k
    chat = ChatBedrock(
        client=bedrock_client,
        model_id=model_id,
        model_kwargs=model_kwargs,
    )

    human_message = [{
        'type': 'text',
        'text': prompt,
    }]
    prompt = ChatPromptTemplate.from_messages([
        HumanMessage(content=human_message)
    ])
    chain = prompt | chat

    response = invoke_chain_with_retry(chain)
    content = response.content

    usage_data = None
    stop_reason = None

    if ('anthropic' in model_id):
        usage_data = response.response_metadata['usage']
        stop_reason = response.response_metadata['stop_reason'] 
    elif('amazon.nova' in model_id):
        usage_data = response.usage_metadata 
        stop_reason = response.response_metadata['stopReason']

    if verbose:
        logger.info(f"Model response: {content}")
        logger.info(f"Model usage: {usage_data}")
        logger.info(f"Model stop_reason: {stop_reason}")

    return content, usage_data, stop_reason