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
import json
import boto3
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())

bedrock_agent = boto3.client('bedrock-agent-runtime')

#CORS Headers
CORS_HEADERS = {
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': '*'
}

KB_ID = os.environ['KB_ID']

def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        logger.debug(f"Received event: {event}")

        # Parse request body
        body = json.loads(event['body'])
        question = body['question']
        model_id = body['model']

        # Get Account ID and region from lambda function arn in the context
        ACCOUNT_ID = _context.invoked_function_arn.split(":")[4]
        REGION = _context.invoked_function_arn.split(":")[3]

        # Convert model_id to modelArn based on whether it starts with 'us'
        if model_id.startswith('us'):
            # For models starting with 'us', use the inference-profile format
            model_arn = f'arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:inference-profile/{model_id}'
        else:
            # For other models, use the original format
            model_arn = f'arn:aws:bedrock:{REGION}:{ACCOUNT_ID}::foundation-model/{model_id}'

        # Construct prompt
        prompt = f"\n\nHuman: Please answer the following question using only the retrieved information. If you cannot answer based on the retrieved information, say so.\n\nQuestion: {question}\n\nAssistant:"

        # Use bedrock-agent-runtime to retrieve and generate
        response = bedrock_agent.retrieve_and_generate(
            input={
                'text': prompt
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KB_ID,
                    'modelArn': model_arn
                }
            }
        )

        logger.debug(f"Model response: {json.dumps(response, indent=2)}")

        # Get the response text
        text = response.get('output', {}).get('text', '')

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'answer': text
            })
        }

    except Exception as e:
        logger.exception("Error processing request")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'error': str(e)
            })
        }
