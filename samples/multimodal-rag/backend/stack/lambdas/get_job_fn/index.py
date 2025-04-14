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
from typing import Dict, List, Any, Optional
import boto3
from botocore.config import Config
import logging
import os
from decimal import Decimal
import json
from botocore.exceptions import ClientError
import datetime

# Constants
FILENAME_KEY = 'filename'
MODALITY_KEY = 'modality'
REQUESTED_BY_KEY = 'cognito:username'
MAX_ITEMS_PER_PAGE = 100  # DynamoDB recommended limit per page

# CORS Headers
CORS_HEADERS = {
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': '*'
}

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])

s3 = boto3.client('s3', config=Config(
    signature_version='s3v4',
    s3={'addressing_style': 'path'}
))


# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())

class OutputEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types from DynamoDB."""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a specific job from DynamoDB by its ID.
    
    Args:
        job_id: The unique identifier of the job
        
    Returns:
        Optional[Dict]: The job data if found, None otherwise
        
    Raises:
        ClientError: If there's an error communicating with DynamoDB
    """
    logger.info(f'Getting job {job_id} from DynamoDB')

    try:
        response = jobs_table.get_item(Key={'id': job_id})
        item = response.get('Item')
        
        if 'demo_metadata' in item:
                if 'file' in item['demo_metadata']:
                    file_info = item['demo_metadata']['file']
                    if isinstance(file_info, dict) and 's3_bucket' in file_info and 's3_key' in file_info:
                        try:
                            presigned_url = s3.generate_presigned_url(
                                'get_object',
                                Params={
                                    'Bucket': file_info['s3_bucket'],
                                    'Key': file_info['s3_key'],
                                    'ResponseContentType': 'application/octet-stream',
                                    'ResponseContentDisposition': f'attachment; filename="{file_info["s3_key"].split("/")[-1]}"'
                                },
                                ExpiresIn=3600  # 1 hour expiry
                            )
                            item['demo_metadata']['file']['presigned_url'] = presigned_url
                        except ClientError as e:
                            logger.warning(f"Failed to generate presigned URL for input file: {str(e)}")

                if 'result_file' in item['demo_metadata']:
                    result_file = item['demo_metadata']['result_file']
                    if isinstance(result_file, dict) and 's3_bucket' in result_file and 's3_key' in result_file:
                        try:
                            presigned_url = s3.generate_presigned_url(
                                'get_object',
                                Params={
                                    'Bucket': result_file['s3_bucket'],
                                    'Key': result_file['s3_key'],
                                    'ResponseContentType': 'application/octet-stream',
                                    'ResponseContentDisposition': f'attachment; filename="{result_file["s3_key"].split("/")[-1]}"'
                                },
                                ExpiresIn=3600  # 1 hour expiry
                            )
                            item['demo_metadata']['result_file']['presigned_url'] = presigned_url
                        except ClientError as e:
                            logger.warning(f"Failed to generate presigned URL for result file: {str(e)}")
                
                return item
    
    except ClientError as e:
        logger.error(f"DynamoDB error fetching job {job_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching job {job_id}: {str(e)}")
        raise

def validate_job_id(job_id: str) -> None:
    """Validate the job ID format and length.
    
    Args:
        job_id: The job ID to validate
        
    Raises:
        ValueError: If the job ID is invalid
    """
    if not job_id:
        raise ValueError("Job ID cannot be empty")
    if len(job_id) > 100:
        raise ValueError("Job ID exceeds maximum length of 100 characters")
    # Add additional validation if needed (e.g., format checking)

def create_response(status_code: int, body: Any = None) -> Dict[str, Any]:
    """Create a standardized API response.
    
    Args:
        status_code: HTTP status code
        body: Response body (optional)
        
    Returns:
        Dict containing the API response
    """
    response = {
        'statusCode': status_code,
        'headers': CORS_HEADERS
    }
    
    if body is not None:
        response['body'] = json.dumps(body, cls=OutputEncoder)
        
    return response

def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """Lambda handler for retrieving a specific job by ID.
    
    Args:
        event: Lambda event object containing the job ID in pathParameters
        _context: Lambda context object (unused)
        
    Returns:
        Dict containing the API Gateway response with:
        - statusCode: HTTP status code
        - headers: CORS headers
        - body: Job data (if found) or error message
        
    Response Status Codes:
        200: Job found and returned successfully
        400: Invalid job ID provided
        404: Job not found
        500: Internal server error
    """
    try:
        logger.debug(f"Received event: {event}")
        
        # Extract and validate job ID
        path_parameters = event.get('pathParameters', {})
        if not path_parameters or 'id' not in path_parameters:
            return create_response(400, {'error': 'Missing job ID'})
            
        job_id = path_parameters['id']
        validate_job_id(job_id)
        
        # Get job data
        result = get_job(job_id)

        if result:
            return create_response(200, result)
        else:
            return create_response(404, {'error': f'Job {job_id} not found'})
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return create_response(400, {'error': str(e)})
    except ClientError as e:
        logger.error(f"AWS service error: {str(e)}", exc_info=True)
        return create_response(500, {'error': 'Internal server error'})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_response(500, {'error': 'Internal server error'})
