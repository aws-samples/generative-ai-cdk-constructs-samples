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
import json
import logging
import re
from retrying import retry
from botocore.config import Config
from botocore.exceptions import ClientError

DEFAULT_MODEL_ID = "amazon.nova-pro-v1:0"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bedrock_runtime = boto3.client('bedrock-runtime', config=Config(
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
def invoke_llm(prompt, model_id, temperature=0.5, top_k=None, top_p=None, max_new_tokens=4096, verbose=False):
    """
    Invoke LLM using direct bedrock_runtime calls.

    Args:
        prompt: The user prompt text
        model_id: Model identifier
        temperature: Sampling temperature
        top_k: Top-k sampling parameter
        top_p: Top-p sampling parameter
        max_new_tokens: Maximum tokens to generate
        verbose: Enable verbose logging

    Returns:
        tuple: (response_content, usage_data, stop_reason)
    """
    model_id = (model_id or DEFAULT_MODEL_ID)

    if verbose:
        logger.info(f"ModelId: {model_id}")
        logger.info(f"User prompt: {prompt}...")

    # Build request body based on model type
    if _is_nova_model(model_id):
        # Amazon Nova models use messages-v1 schema
        body = {
            "schemaVersion": "messages-v1",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }],
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_new_tokens,
            }
        }

        # Add optional parameters to inferenceConfig if provided
        if top_p is not None:
            body["inferenceConfig"]["topP"] = top_p
        if top_k is not None:
            body["inferenceConfig"]["topK"] = top_k

    elif _is_claude_model(model_id):
        # Anthropic Claude models use anthropic_version structure
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }],
            "temperature": temperature,
            "max_tokens": max_new_tokens,
        }

        # Add optional parameters if provided
        if top_p is not None:
            body["top_p"] = top_p
        if top_k is not None:
            body["top_k"] = top_k
    else:
        raise ValueError(f"Unsupported model: {model_id}. Only Amazon Nova and Anthropic Claude models are supported.")

    try:
        response = bedrock_runtime.invoke_model(
            body=json.dumps(body),
            modelId=model_id
        )
    except ClientError as exc:
        logger.warning(f"Bedrock ClientError: {exc}")

        if exc.response['Error']['Code'] == 'ThrottlingException':
            logger.warning("Bedrock throttling. Retrying...")
            raise BedrockRetryableError(str(exc))
        elif exc.response['Error']['Code'] == 'ModelTimeoutException':
            logger.warning("Bedrock ModelTimeoutException. Retrying...")
            raise BedrockRetryableError(str(exc))
        elif exc.response['Error']['Code'] == 'ModelErrorException':
            logger.warning("Bedrock ModelErrorException. Retrying...")
            raise BedrockRetryableError(str(exc))
        else:
            raise
    except bedrock_runtime.exceptions.ThrottlingException as throttlingExc:
        logger.warning("Bedrock ThrottlingException. Retrying...")
        raise BedrockRetryableError(str(throttlingExc))
    except bedrock_runtime.exceptions.ModelTimeoutException as timeoutExc:
        logger.warning("Bedrock ModelTimeoutException. Retrying...")
        raise BedrockRetryableError(str(timeoutExc))

    # Parse response based on model type
    response_body = json.loads(response.get('body').read())

    if _is_nova_model(model_id):
        # Amazon Nova response format
        response_content = response_body['output']['message']['content'][0]['text']
        usage_data = response_body.get('usage', {})
        stop_reason = response_body.get('stopReason')
    elif _is_claude_model(model_id):
        # Anthropic Claude response format
        response_content = response_body['content'][0]['text']
        usage_data = response_body.get('usage', {})
        stop_reason = response_body.get('stop_reason')
    else:
        # This shouldn't happen due to earlier validation, but just in case
        raise ValueError(f"Unsupported model for response parsing: {model_id}")

    if verbose:
        logger.info(f"Model response: {response_content}")

    # Log token usage in consistent format
    if usage_data:
        token_usage_log = {
            "model_id": model_id,
            "input_tokens": usage_data.get('input_tokens', 0),
            "output_tokens": usage_data.get('output_tokens', 0)
        }

        logger.info(f"LLM token usage: {token_usage_log}")

    return response_content, usage_data, stop_reason


def _is_nova_model(model_id):
    """Check if the model is an Amazon Nova model."""
    # Remove region prefix if it exists (e.g., "us." or "eu.")
    if model_id.startswith('us.') or model_id.startswith('eu.'):
        model_id = model_id.split('.', 1)[1]

    return model_id.startswith('amazon.nova-')


def _is_claude_model(model_id):
    """Check if the model is an Anthropic Claude model."""
    # Remove region prefix if it exists (e.g., "us." or "eu.")
    if model_id.startswith('us.') or model_id.startswith('eu.'):
        model_id = model_id.split('.', 1)[1]

    return model_id.startswith('anthropic.claude-')


def extract_items_from_tagged_list(text, tag_name):
    """Extract items from XML-like tags in text"""
    opening_tag = f"<{tag_name}>"
    closing_tag = f"</{tag_name}>"

    regex = fr"{opening_tag}(.*?){closing_tag}"

    items = []
    for match in re.finditer(regex, text, re.DOTALL):
        finding = match.group(1).strip()

        # Find innermost nested opening tag, if any
        # To capture cases like where the model return something like:
        # alkjshdksajhdsakjd <tag> kjsdafkdjhf <tag> dsfkjsdfakjds </tag> dskjfhaksdjhfkdsjf

        innermost_tag_idx = finding.rfind(opening_tag)
        if innermost_tag_idx >= 0:
            finding = finding[innermost_tag_idx + len(opening_tag):].strip()

        if finding:
            items.append(finding)

    return items
