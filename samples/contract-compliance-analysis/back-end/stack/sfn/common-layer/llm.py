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

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

CLAUDE_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

bedrock_client = boto3.client('bedrock-runtime')


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

    response = chain.invoke({})
    content = response.content

    if verbose:
        logger.info(f"Model response: {content}")
        logger.info(f"Model usage: {response.response_metadata['usage']}")
        logger.info(f"Model stop_reason: {response.response_metadata['stop_reason']}")

    return content, response.response_metadata['usage'], response.response_metadata["stop_reason"]
