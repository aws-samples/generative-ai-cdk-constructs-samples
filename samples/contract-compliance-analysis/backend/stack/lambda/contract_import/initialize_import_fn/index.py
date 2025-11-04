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

"""
Initialize Import Step Lambda Function

This function creates an import job record and validates input for the contract import process.
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

# Configure logging
logger = Logger(service="contract-import-initialization")

# Initialize AWS clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Environment variables
IMPORT_JOBS_TABLE_NAME = os.environ["IMPORT_JOBS_TABLE_NAME"]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Initialize import job and validate input

    Args:
        event: Step Functions event containing:
            - ExecutionName: Step Functions execution name
            - ImportJobId: Unique import job identifier
            - DocumentS3Key: S3 key of the document to import
            - Description: Optional description for the import

    Returns:
        Dict containing import job details and validation results
    """
    import_job_id = None

    try:
        logger.info("Starting import initialization", extra={"event": event})

        # Extract input parameters with better error handling
        execution_name = event.get("ExecutionName")
        import_job_id = event.get("ImportJobId")
        document_s3_key = event.get("DocumentS3Key")
        description = event.get("Description", "")

        # Validate required parameters with specific error messages
        validation_errors = []
        if not import_job_id:
            validation_errors.append("ImportJobId is required")
        if not document_s3_key:
            validation_errors.append("DocumentS3Key is required")
        if not execution_name:
            validation_errors.append("ExecutionName is required")

        if validation_errors:
            raise ValueError(f"Validation failed: {'; '.join(validation_errors)}")

        # Validate document exists in S3 with comprehensive error handling
        try:
            bucket_name = os.environ.get("CONTRACT_BUCKET_NAME")
            if not bucket_name:
                raise ValueError("CONTRACT_BUCKET_NAME environment variable not set")

            logger.info(f"Validating document exists in S3: {bucket_name}/{document_s3_key}")
            s3_client.head_object(Bucket=bucket_name, Key=document_s3_key)

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise ValueError(f"Document not found in S3: {document_s3_key}")
            elif error_code == 'NoSuchBucket':
                raise ValueError(f"S3 bucket not found: {bucket_name}")
            elif error_code == 'AccessDenied':
                raise ValueError(f"Access denied to S3 document: {document_s3_key}")
            else:
                raise ValueError(f"Failed to validate document in S3: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error validating S3 document: {str(e)}")

        # Create import job record with error handling
        try:
            current_time = datetime.utcnow().isoformat()

            # Get DynamoDB table
            table = dynamodb.Table(IMPORT_JOBS_TABLE_NAME)

            # Create import job item
            import_job_item = {
                "import_job_id": import_job_id,
                "execution_id": execution_name,
                "document_s3_key": document_s3_key,
                "status": "RUNNING",
                "current_step": "Initialize Import",
                "progress": 10,  # 10% complete after initialization
                "created_at": current_time,
                "updated_at": current_time
            }

            # Save to DynamoDB
            table.put_item(Item=import_job_item)

        except Exception as e:
            raise RuntimeError(f"Failed to create import job record: {str(e)}")

        # Return success response
        response = {
            "ImportJobId": import_job_id,
            "DocumentS3Key": document_s3_key,
            "Description": description,
            "Status": "INITIALIZED",
            "Progress": 10,
            "Timestamp": current_time
        }

        logger.info("Import initialization completed successfully", extra={"response": response})
        return response

    except Exception as e:
        error_message = f"Import initialization failed: {str(e)}"
        logger.error(error_message, extra={
            "import_job_id": import_job_id,
            "error_type": type(e).__name__,
            "event": event
        })

        # Update import job status to FAILED if we have the job ID
        if import_job_id:
            try:
                table = dynamodb.Table(IMPORT_JOBS_TABLE_NAME)
                current_time = datetime.utcnow().isoformat()

                table.update_item(
                    Key={"import_job_id": import_job_id},
                    UpdateExpression="SET #status = :status, error_message = :error_message, current_step = :current_step, updated_at = :updated_at",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":status": "FAILED",
                        ":error_message": str(e),
                        ":current_step": "Initialize Import",
                        ":updated_at": current_time
                    }
                )
                logger.info(f"Updated import job {import_job_id} status to FAILED")
            except Exception as update_error:
                logger.error(f"Failed to update import job status: {str(update_error)}")

        # Return error response for Step Functions to handle gracefully
        # Instead of raising, return an error response that can be handled by the state machine
        return {
            "Error": "ImportInitializationFailed",
            "Cause": error_message,
            "ImportJobId": import_job_id,
            "Status": "FAILED",
            "Progress": 0
        }