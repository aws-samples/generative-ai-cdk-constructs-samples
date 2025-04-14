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

s3 = boto3.client('s3', config=Config(signature_version='s3v4'))

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())

class OutputEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types from DynamoDB."""
    
    def default(self, obj: Any) -> Any:
        """Convert Decimal objects to integers.
        
        Args:
            obj: The object to encode
            
        Returns:
            The encoded object
        """
        if isinstance(obj, Decimal):
            return int(obj)
        return json.JSONEncoder.default(self, obj)

def get_jobs(limit: Optional[int] = None, start_key: Optional[Dict] = None) -> Dict[str, Any]:
    """Retrieve jobs from DynamoDB with optional pagination.
    
    Args:
        limit: Maximum number of items to return (optional)
        start_key: Key to start scanning from for pagination (optional)
        
    Returns:
        Dict containing jobs and pagination information
    """
    logger.info('Getting jobs from DynamoDB')
    
    scan_kwargs = {
        'Limit': min(limit, MAX_ITEMS_PER_PAGE) if limit else MAX_ITEMS_PER_PAGE
    }
    
    if start_key:
        scan_kwargs['ExclusiveStartKey'] = start_key
        
    try:
        response = jobs_table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for item in items:
            if 'demo_metadata' in item:
                if 'file' in item['demo_metadata']:
                    file_info = item['demo_metadata']['file']
                    if isinstance(file_info, dict) and 's3_bucket' in file_info and 's3_key' in file_info:
                        try:
                            presigned_url = s3.generate_presigned_url(
                                'get_object',
                                Params={
                                    'Bucket': file_info['s3_bucket'],
                                    'Key': file_info['s3_key']
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
                                    'Key': result_file['s3_key']
                                },
                                ExpiresIn=3600  # 1 hour expiry
                            )
                            item['demo_metadata']['result_file']['presigned_url'] = presigned_url
                        except ClientError as e:
                            logger.warning(f"Failed to generate presigned URL for result file: {str(e)}")
        
        return {
            'items': items,
            'last_evaluated_key': response.get('LastEvaluatedKey'),
            'count': response.get('Count', 0)
        }
    except ClientError as e:
        logger.warning(f"Scanning DynamoDB table failed, propagating error: {str(e)}")
        raise

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
    """Lambda handler for retrieving jobs.
    
    Args:
        event: Lambda event object
        _context: Lambda context object
        
    Returns:
        API Gateway response object
    """
    try:
        logger.debug(f"Received event: {event}")
        
        # Extract pagination parameters if present
        query_parameters = event.get('queryStringParameters', {}) or {}
        limit = int(query_parameters.get('limit', MAX_ITEMS_PER_PAGE))
        start_key = query_parameters.get('start_key')
        
        if start_key:
            try:
                start_key = json.loads(start_key)
            except json.JSONDecodeError:
                return create_response(400, {'error': 'Invalid start_key format'})
        
        # Get jobs with pagination
        result = get_jobs(limit=limit, start_key=start_key)
        return create_response(200, result)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return create_response(400, {'error': str(e)})
    except ClientError as e:
        logger.error(f"AWS service error: {str(e)}", exc_info=True)
        return create_response(500, {'error': 'Internal server error'})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_response(500, {'error': 'Internal server error'})