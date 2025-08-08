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
import os

from retrying import retry
from botocore.config import Config
from botocore.exceptions import ClientError
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

# Import Powertools Logger
from aws_lambda_powertools import Logger

CLAUDE_MODEL_ID = "amazon.nova-pro-v1:0"

# Initialize Powertools logger with shared service name
logger = Logger(service="contract-compliance-analysis")

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
def invoke_chain_with_retry(runnable):
    """Invoke Bedrock with retry logic for throttling and model errors"""
    try:
        return runnable.invoke({})
    except ClientError as exc:
        logger.warning(f"Bedrock ClientError: {exc}")

        if exc.response["Error"]["Code"] == "ThrottlingException":
            logger.warning("Bedrock throttling. Retrying...")
            raise BedrockRetryableError(str(exc))
        elif exc.response["Error"]["Code"] == "ModelTimeoutException":
            logger.warning("Bedrock ModelTimeoutException. Retrying...")
            raise BedrockRetryableError(str(exc))
        elif exc.response["Error"]["Code"] == "ModelErrorException":
            logger.warning("Bedrock ModelErrorException. Retrying...")
            raise BedrockRetryableError(str(exc))
        else:
            raise
    except bedrock_client.exceptions.ThrottlingException as throttlingExc:
        logger.warning("Bedrock ThrottlingException. Retrying...")
        raise BedrockRetryableError(str(throttlingExc))
    except bedrock_client.exceptions.ModelTimeoutException as timeoutExc:
        logger.warning("Bedrock ModelTimeoutException. Retrying...")
        raise BedrockRetryableError(str(timeoutExc))


def invoke_llm(prompt, model_id, temperature=0.5, top_k=None, top_p=None, max_new_tokens=4096, verbose=False, system_prompt=None, enable_caching=False):
    """
    Invoke LLM using LangChain ChatBedrock with prompt caching support.
    
    Args:
        prompt: The user prompt text
        model_id: Model identifier
        temperature: Sampling temperature
        top_k: Top-k sampling parameter
        top_p: Top-p sampling parameter
        max_new_tokens: Maximum tokens to generate
        verbose: Enable verbose logging
        system_prompt: System prompt text (cacheable if enable_caching=True)
        enable_caching: Whether to cache the system prompt
    """
    model_id = (model_id or CLAUDE_MODEL_ID)

    if verbose:
        logger.info(f"ModelId: {model_id}")
        if system_prompt:
            logger.info(f"System prompt (cache={enable_caching}): {system_prompt}...")
        logger.info(f"User prompt: {prompt}...")

    try:
        # Configure model parameters
        model_kwargs = {
            "max_tokens": max_new_tokens,
            "temperature": temperature,
        }
        if top_p is not None:
            model_kwargs["top_p"] = top_p
        if top_k is not None:
            model_kwargs["top_k"] = top_k

        # Initialize ChatBedrock
        chat = ChatBedrock(
            client=bedrock_client,
            model_id=model_id,
            model_kwargs=model_kwargs,
        )

        # Build messages with caching support
        messages = []
        
        # Add system message with optional caching
        if system_prompt:
            system_message = _build_cached_system_message(enable_caching, system_prompt, model_id)
            if system_message:
                messages.append(system_message)
                
                # User message must also be in raw format when mixing with cached system
                user_message = {
                    "role": "user", 
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
                messages.append(user_message)
            else:
                # No caching (either not requested or not supported), use standard format
                messages.append(("system", system_prompt))
                messages.append(("user", prompt))
        else:
            # No system prompt, just user message
            messages.append(("user", prompt))

        chain = RunnableLambda(lambda _: chat.invoke(messages))
        response = invoke_chain_with_retry(chain)
        
        if verbose:
            logger.info(f"Model response: {response}")

        # Extract usage data and cache metrics
        usage_data = getattr(response, 'usage_metadata', {})
        stop_reason = getattr(response, 'response_metadata', {}).get('stop_reason')

        if usage_data:
            input_token_details = usage_data.get('input_token_details', {})
            cache_read = (input_token_details.get('cache_read', 0))
            cache_write = (input_token_details.get('cache_creation', 0))
            
            if cache_read > 0:
                logger.info(f"✅ Cache read: {cache_read} tokens")
            if cache_write > 0:
                logger.info(f"✅ Cache created: {cache_write} tokens")

            token_usage_log = {
                "model_id": model_id,
                "input_tokens": usage_data.get('input_tokens', 0),
                "output_tokens": usage_data.get('output_tokens', 0),
                "cache_read_tokens": cache_read,
                "cache_write_tokens": cache_write
            }
            
            logger.info("LLM token usage", extra={
                "token_usage": token_usage_log
            })

        return response.content, usage_data, stop_reason
        
    except Exception as e:
        logger.error(f"Error invoking model: {str(e)}")
        raise


def _build_cached_system_message(enable_caching, system_prompt, model_id):
    """Build a cached system message if caching is enabled and model supports it, otherwise return None."""
    if not enable_caching or not supports_prompt_caching(model_id):
        return None
    
    base_content = {"type": "text", "text": system_prompt}
    
    if _is_nova_model(model_id):
        return {
            "role": "system",
            "content": [base_content, {"cachePoint": {"type": "default"}}]
        }
    elif _is_claude_model(model_id):
        base_content["cache_control"] = {"type": "ephemeral"}
        return {
            "role": "system", 
            "content": [base_content]
        }
    else:
        # Fallback for unknown model types - no caching
        return {
            "role": "system",
            "content": [base_content]
        }


def supports_prompt_caching(model_id):
    """Check if the model supports prompt caching."""
    supported_models = [
        'anthropic.claude-opus-4-20250514-v1:0',
        'anthropic.claude-sonnet-4-20250514-v1:0', 
        'anthropic.claude-3-7-sonnet-20250219-v1:0',
        'anthropic.claude-3-haiku-20240307-v1:0',
        'anthropic.claude-3-5-haiku-20241022-v1:0',
        'amazon.nova-micro-v1:0',
        'amazon.nova-lite-v1:0',
        'amazon.nova-pro-v1:0',
        'amazon.nova-premier-v1:0'
    ]
    
    # Remove region prefix if it exists (e.g., "us." or "eu.")
    if model_id.startswith('us.') or model_id.startswith('eu.'):
        model_id = model_id.split('.', 1)[1]
    
    return model_id in supported_models


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


