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

import json
import os
import boto3
import botocore
import requests
from requests_aws4auth import AWS4Auth
from enum import Enum
from bs4 import BeautifulSoup
from typing import Any, Dict
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

LOGGER = Logger(serialize_stacktrace=True, name="%(name)s")

class StreamStatus(str, Enum):
    STARTED = "STARTED"
    STREAMING = "STREAMING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
appsync = boto3.client('appsync')

def get_agent_secrets():
    """Retrieve secrets from AWS Secrets Manager"""
    secret_name = os.environ['AGENT_SECRET_NAME']
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager'
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        LOGGER.error(f"Error retrieving secrets: {str(e)}")
        raise e
    else:
        if 'SecretString' in get_secret_value_response:
            secret = json.loads(get_secret_value_response['SecretString'])
            return secret
        raise ValueError("No SecretString found in secret")

try:
    agent_secrets = get_agent_secrets()
    LOGGER.info("Agent credentials loaded from secrets manager")
    AGENT_ID = agent_secrets['AGENT_ID']
    AGENT_ALIAS_ID = agent_secrets['AGENT_ALIAS_ID']
    APPSYNC_API_ID = agent_secrets['APPSYNC_API_ID']
    APPSYNC_ENDPOINT = agent_secrets['APPSYNC_ENDPOINT']
    REGION =  agent_secrets['AWS_REGION']
except Exception as e:
    LOGGER.error(f"Error initializing services: {str(e)}")
    raise


def extract_answer(full_result_message: str):
    soup = BeautifulSoup(full_result_message, 'html.parser')
    # 1. First try to find content between <result> tags
    result_tag = soup.find('result')
    if result_tag:
        return result_tag.get_text().strip()
    
    # 2. If no result tags, look for <followup> tags
    followup_tag = soup.find('clarifying_query')
    if followup_tag:
        return followup_tag.get_text().strip()

    # 3. If no tags found, get text before first HTML tag
    first_tag = soup.find()  # Find first tag
    if first_tag and first_tag.previous_sibling:
        return first_tag.previous_sibling.strip()
    
    # Fallback: get the last text string
    return soup.find_all(string=True, recursive=True)[-1].strip()

def process_trace_step(trace: dict) -> dict[str, str]:
    if 'chunk' in trace and "bytes" in trace["chunk"]:
        full_result_message = trace["chunk"]["bytes"].decode()
        try:
            result_str = extract_answer(full_result_message)
        except Exception:
            result_str = full_result_message
        return {"Result": result_str}
    trace = trace.get("trace", {}).get("trace", {}).get("orchestrationTrace", {})
    if "rationale" in trace:
        return {"Rationale": trace["rationale"].get("text", "")}
    elif "invocationInput" in trace:
        return {"Invocation": trace["invocationInput"].get("actionGroupInvocationInput", "")}
    elif "observation" in trace:
        return {"Observation": trace["observation"]}
    return ""

def get_appsync_client():
    session = boto3.Session()
    credentials = session.get_credentials()
    
    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        'appsync',
        session_token=credentials.token
    )
    
    return auth


def publish_to_appsync(session_id: str, content: str, status: StreamStatus):
    mutation = """
    mutation PublishUpdate($sessionId: String!, $content: String, $status: StreamStatus!) {
        publishAgentUpdate(sessionId: $sessionId, content: $content, status: $status) {
            sessionId
            content
            status
        }
    }
    """
    
    variables = {
        'sessionId': session_id,
        'content': content,
        'status': status.value
    }
    auth = get_appsync_client()
    try:
        response = requests.post(
            APPSYNC_ENDPOINT,
            json={'query': mutation, 'variables': variables},
            headers={'Content-Type': 'application/json'},
            auth=auth,
            timeout=(3.05, 27)
        )
        response.raise_for_status()
        LOGGER.info("Response:", response.json())
    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors (4xx, 5xx)
        LOGGER.error(f"HTTP error occurred: {e}")
    except requests.exceptions.Timeout as e:
        # Handle timeout errors
        LOGGER.error(f"Request timed out: {e}")
    except requests.exceptions.RequestException as e:
        # Handle all other requests-related errors
        LOGGER.error(f"Request failed: {e}")
    except Exception as e:
        # Handle any other unexpected errors
        LOGGER.error(f"Unexpected error: {e}")

def _lambda_handler(event):
    try:
        session_id = event['sessionId']
        question = event['question']
        LOGGER.info(f"AGENT_ID: {AGENT_ID}")
        LOGGER.info(f"AGENT_ALIAS_ID: {AGENT_ALIAS_ID}")
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=question,
            enableTrace=True
        )

        stream = response['completion']
        for event in stream:
            parsed_step = process_trace_step(event)
            if parsed_step:
                publish_to_appsync(
                    session_id=session_id,
                    content=json.dumps(parsed_step, indent=2),
                    status=StreamStatus.COMPLETED if 'Result' in parsed_step else StreamStatus.STREAMING
                )
        return {'status': 'COMPLETED'}
    except Exception as e:
        LOGGER.error(f"Error in stream: {str(e)}")
        # Publish error status
        publish_to_appsync(
            session_id=session_id,
            content=str(e),
            status=StreamStatus.ERROR
        )
        return {'status': 'ERROR', 'error': str(e)}

@LOGGER.inject_lambda_context(clear_state=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    LOGGER.info(f"Received event: {event}")
    try:
        response = _lambda_handler(event=event)
    except botocore.exceptions.ClientError as error:
        op_name = error.operation_name
        err_name = error.response["Error"]["Code"]
        err_message = error.response["Error"]["Message"]
        message = f"Call to the {op_name} operation returned a {err_name} error: {err_message}"
        LOGGER.exception(f"AWS service-side error: {message}")
        error_message = f"Internal server error (AWS service-side error): {message}"
        raise Exception(error_message)
    except Exception as error:
        LOGGER.exception("Unhandled error")
        error_message = f"Unhandled internal server error ({type(error).__name__}): {error}"
        raise Exception(error_message)

    return response