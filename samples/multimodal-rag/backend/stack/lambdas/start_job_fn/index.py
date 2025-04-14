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
from datetime import datetime, timezone
from decimal import Decimal
import json
import uuid
from botocore.exceptions import ClientError

# Constants for keys
FILENAME_KEY = 'filename'
MODALITY_KEY = 'modality'
BDA_PROJECT_ARN_KEY = 'bda_project_arn'
REQUESTED_BY_KEY = 'cognito:username'
ENCRYPTION_KEY_ID_KEY = 'encryption_key_id'
ENCRYPTION_CONTEXT_KEY = 'encryption_context'
BLUEPRINTS_KEY = 'blueprints'
PROFILE_ARN_KEY = 'dataAutomationProfileArn'
TAGS_KEY = 'tags'

dynamodb = boto3.resource('dynamodb')
bda_runtime = boto3.client('bedrock-data-automation-runtime')
jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])

# env variables
input_bucket = os.environ['INPUT_BUCKET']
output_bucket = os.environ['OUTPUT_BUCKET']

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())

class OutputEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal and datetime objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def record_job(job):
    """Records a job in the DynamoDB jobs table."""
    logger.info('Recording job')
    jobs_table.put_item(Item=job)

def validate_body(body_obj: dict) -> None:
    """Validates the input body object for required fields and constraints."""
    if not body_obj or not isinstance(body_obj, dict):
        raise ValueError("Input must be a non-empty dictionary.")
    if FILENAME_KEY not in body_obj or len(body_obj[FILENAME_KEY]) > 200:
        raise ValueError(f"'{FILENAME_KEY}' is required and must be less than 200 characters.")
    if MODALITY_KEY not in body_obj or len(body_obj[MODALITY_KEY]) > 200:
        raise ValueError(f"'{MODALITY_KEY}' is required and must be less than 200 characters.")
    if BDA_PROJECT_ARN_KEY not in body_obj or len(body_obj[BDA_PROJECT_ARN_KEY]) > 200:
        raise ValueError(f"'{BDA_PROJECT_ARN_KEY}' is required and must be less than 200 characters.")
    
    # Optional parameters validation
    if ENCRYPTION_KEY_ID_KEY in body_obj and len(body_obj[ENCRYPTION_KEY_ID_KEY]) > 200:
        raise ValueError(f"'{ENCRYPTION_KEY_ID_KEY}' must be less than 200 characters.")
    if BLUEPRINTS_KEY in body_obj and not isinstance(body_obj[BLUEPRINTS_KEY], list):
        raise ValueError(f"'{BLUEPRINTS_KEY}' must be a list.")
    if PROFILE_ARN_KEY in body_obj and len(body_obj[PROFILE_ARN_KEY]) > 200:
        raise ValueError(f"'{PROFILE_ARN_KEY}' must be less than 200 characters.")
    if TAGS_KEY in body_obj and not isinstance(body_obj[TAGS_KEY], list):
        raise ValueError(f"'{TAGS_KEY}' must be a list.")

def validate_bda_response(response):
    """Validates the response from the Bedrock Data Automation invocation."""
    if 'invocationArn' not in response:
        raise RuntimeError("Response does not contain 'invocationArn'.")
    
    # Check the HTTP status code
    if 'ResponseMetadata' not in response or response['ResponseMetadata'].get('HTTPStatusCode') != 200:
        raise RuntimeError("Invalid response: HTTP status code is not 200.")

def handler(event, _context):
    """Main handler function for processing the incoming event."""
    response = {
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*'
        },
        'body': '',
        'statusCode': 500  # Default to 500 in case of an error
    }

    try:
        logger.debug(event)
        body_obj = json.loads(event['body'])
        validate_body(body_obj)
        filename = body_obj[FILENAME_KEY]
        modality = body_obj[MODALITY_KEY]
        bda_project_arn = body_obj[BDA_PROJECT_ARN_KEY]
        requested_by = event['requestContext']['authorizer']['claims']['cognito:username']
        input_document_s3_path = f"s3://{input_bucket}/{filename}"
        output_document_s3_path = f"s3://{output_bucket}"

        # Prepare the invoke parameters
        invoke_params = {
            'clientToken': str(uuid.uuid4()),
            'inputConfiguration': {
                's3Uri': input_document_s3_path
            },
            'outputConfiguration': {
                's3Uri': output_document_s3_path
            },
            'dataAutomationConfiguration': {
                'dataAutomationProjectArn': bda_project_arn,
                'stage': 'LIVE'
            },
            'notificationConfiguration': {
                'eventBridgeConfiguration': {
                    'eventBridgeEnabled': True
                }
            }
        }

        # Add optional encryption configuration if provided
        if ENCRYPTION_KEY_ID_KEY in body_obj:
            encryption_config = {
                'kmsKeyId': body_obj[ENCRYPTION_KEY_ID_KEY]
            }
            
            # Add encryption context if provided
            if ENCRYPTION_CONTEXT_KEY in body_obj:
                encryption_config['kmsEncryptionContext'] = body_obj[ENCRYPTION_CONTEXT_KEY]
                
            invoke_params['encryptionConfiguration'] = encryption_config

        # Add blueprints if provided
        if BLUEPRINTS_KEY in body_obj:
            invoke_params['blueprints'] = body_obj[BLUEPRINTS_KEY]

        # Add profile ARN if provided
        if PROFILE_ARN_KEY in body_obj:
            invoke_params['dataAutomationProfileArn'] = body_obj[PROFILE_ARN_KEY]

        # Add tags if provided
        if TAGS_KEY in body_obj:
            invoke_params['tags'] = body_obj[TAGS_KEY]

        # Invoke the BDA runtime
        bda_response = bda_runtime.invoke_data_automation_async(**invoke_params)

        logger.info(bda_response)

        validate_bda_response(bda_response)  # Validate the response

        invocation_arn = bda_response.get("invocationArn")
        job_id = invocation_arn.split('/')[-1]

        job = {
            "id": job_id,
            "demo_metadata": {
                "requested_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "file": {
                    "s3_bucket": input_bucket, 
                    "s3_key": filename,
                },
                "job_status": "PROCESSING",
                "requested_by": requested_by,
                "modality": modality,
            }
        }

        # Add optional parameters to job metadata if they were used
        if ENCRYPTION_KEY_ID_KEY in body_obj:
            job["demo_metadata"]["encryption_key_id"] = body_obj[ENCRYPTION_KEY_ID_KEY]
        if BLUEPRINTS_KEY in body_obj:
            job["demo_metadata"]["blueprints"] = body_obj[BLUEPRINTS_KEY]
        if PROFILE_ARN_KEY in body_obj:
            job["demo_metadata"]["profile_arn"] = body_obj[PROFILE_ARN_KEY]
        if TAGS_KEY in body_obj:
            job["demo_metadata"]["tags"] = body_obj[TAGS_KEY]

        record_job(job)
        response['body'] = json.dumps(job, cls=OutputEncoder)
        response['statusCode'] = 200

    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exception:
        logger.error("Input error: %s", exception)
        response['body'] = json.dumps({"error": str(exception)})
        response['statusCode'] = 400
    except (AssertionError, ClientError) as exception:
        logger.error("Server error: %s", exception)
        response['body'] = json.dumps({"error": "Internal server error."})
        response['statusCode'] = 500
    finally:
        logger.info("Response: %s", response)

    return response