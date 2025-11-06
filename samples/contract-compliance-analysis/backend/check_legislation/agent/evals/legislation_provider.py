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

#!/usr/bin/env python3

"""
This file is the bridge between promptfoo and our agent that is running locally on port 8080.

All it does is call it with the same payload our agent will be called in production, and then
it evaluates the response.
"""

import json
import requests
import sys
from typing import Optional, Dict, Any, List, Union, TypedDict

class Prompt(str):
    """
    A simple string: "What is the capital of France?"
    A JSON-encoded conversation: '[{"role": "user", "content": "Hello"}]'
    """
    ...

class ProviderOptions(TypedDict):
    id: Optional[str]
    config: Optional[Dict[str, Any]]

class CallApiContextParams(TypedDict):
    vars: Dict[str, str]

class TokenUsage(TypedDict):
    total: int
    prompt: int
    completion: int

class ProviderResponse(TypedDict, total=False):
    output: Optional[Union[str, Dict[str, Any]]]
    error: Optional[str]
    tokenUsage: Optional[TokenUsage]
    cost: Optional[float]
    cached: Optional[bool]
    logProbs: Optional[List[float]]

class ProviderEmbeddingResponse(TypedDict):
    embedding: List[float]
    tokenUsage: Optional[TokenUsage]
    cached: Optional[bool]

class ProviderClassificationResponse(TypedDict):
    classification: Dict[str, Any]
    tokenUsage: Optional[TokenUsage]
    cached: Optional[bool]

def call_api(prompt: Prompt, options: ProviderOptions, context: CallApiContextParams) -> ProviderResponse | ProviderEmbeddingResponse | ProviderClassificationResponse:
    """
    Custom promptfoo provider that calls the legislation agent API
    """
    # Extract variables from context
    vars = context.get('vars', {})
    job_id = vars.get('job_id', 'default-job-id')
    clause_number = vars.get('clause_number', 1)
    legislation_id = vars.get('legislation_id', 'cdc')

    # Agent API endpoint
    url = "http://localhost:8080/invocations"

    # Prepare the request payload
    payload = {
        "JobId": job_id,
        "ClauseNumber": clause_number,
        "LegislationCheck": {
            "agentArchitecture": "Single",
            "legislationId": legislation_id,
        },
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        # Make the API call
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        # Return the response
        result = response.json()

        print(f"RESULT:{result}\n\n\n", flush=True, file=sys.stderr)
        return {
            "output": json.dumps(result, indent=2),
            "tokenUsage": {
                "total": 1,
                "prompt": 1,
                "completion": 0
            }
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": f"API call failed: {str(e)}",
            "output": f"Error: {str(e)}"
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "output": f"Error: {str(e)}"
        }

if __name__ == "__main__":
    # Read input from stdin
    input_data = json.loads(sys.stdin.read())

    prompt = input_data.get("prompt", "")
    options = input_data.get("options", {})
    context = input_data.get("context", {})

    result = call_api(prompt, options, context)
    print(json.dumps(result))
