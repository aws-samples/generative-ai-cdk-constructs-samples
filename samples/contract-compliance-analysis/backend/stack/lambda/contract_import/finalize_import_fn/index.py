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
import uuid
import boto3
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger
try:
    from aws_lambda_powertools.logging import correlation_paths
except ImportError:
    # Fallback for testing or older versions
    class CorrelationPaths:
        STEP_FUNCTIONS = "stepFunctions"
    correlation_paths = CorrelationPaths()
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

logger = Logger()

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")


def _slugify_name(name: str) -> str:
    """Convert name to a valid contract type ID (consistent with API logic)"""
    import re
    # Convert to lowercase, replace spaces and special chars with hyphens
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def ensure_unique_contract_type_name_and_id(name: str, contract_types_table_name: str) -> tuple[str, str]:
    """
    Ensure contract type name and ID are unique, append suffix if needed.
    Returns tuple of (unique_name, unique_id)
    """
    original_name = name.strip()
    original_id = _slugify_name(original_name)

    # Validate the base ID format
    if not original_id or not re.match(r'^[a-zA-Z0-9-]+$', original_id):
        # Fallback for invalid names
        original_id = "contract-type"
        original_name = "Contract Type"

    # Get all existing contract types to check for conflicts
    table = dynamodb.Table(contract_types_table_name)
    try:
        response = table.scan()
        existing_items = response.get('Items', [])

        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            existing_items.extend(response.get('Items', []))

        existing_names_lower = {str(item['name']).lower() for item in existing_items if 'name' in item and isinstance(item['name'], str)}
        existing_ids_lower = {str(item['contract_type_id']).lower() for item in existing_items if 'contract_type_id' in item and isinstance(item['contract_type_id'], str)}

    except Exception as e:
        logger.warning(f"Failed to check existing contract types: {e}")
        existing_names_lower = set()
        existing_ids_lower = set()

    # If both name and ID are unique, return as-is
    if (original_name.lower() not in existing_names_lower and
        original_id.lower() not in existing_ids_lower):
        return original_name, original_id

    # Find next available suffix
    counter = 2
    while counter <= 100:  # Safety limit
        new_name = f"{original_name}-{counter}"
        new_id = f"{original_id}-{counter}"

        if (new_name.lower() not in existing_names_lower and
            new_id.lower() not in existing_ids_lower):
            return new_name, new_id

        counter += 1

    # Fallback to UUID if we can't find a unique name within reasonable attempts
    unique_suffix = str(uuid.uuid4())[:8]
    return f"{original_name}-{unique_suffix}", f"{original_id}-{unique_suffix}"


def create_contract_type(contract_type_info: Dict[str, Any],
                        contract_types_table_name: str,
                        document_s3_key: str) -> Dict[str, Any]:
    """Create a new contract type from extracted info"""

    # Ensure unique name and ID
    unique_name, unique_id = ensure_unique_contract_type_name_and_id(
        contract_type_info["contract_type_name"],
        contract_types_table_name
    )

    now = datetime.now(timezone.utc).isoformat()

    contract_type_item = {
        "contract_type_id": unique_id,
        "name": unique_name,
        "description": contract_type_info.get("description", ""),
        "company_party_type": contract_type_info.get("company_party_type", "Company"),
        "other_party_type": contract_type_info.get("other_party_type", "Other Party"),
        "high_risk_threshold": 0,
        "medium_risk_threshold": 1,
        "low_risk_threshold": 3,
        "is_active": False,  # Start as disabled for imported types
        "default_language": contract_type_info.get("language", "en"),
        "created_at": now,
        "updated_at": now,
        "is_imported": True,
        "import_source_document": document_s3_key
    }

    table = dynamodb.Table(contract_types_table_name)
    table.put_item(Item=contract_type_item)
    logger.info(f"Created contract type: {unique_id}")

    return contract_type_item


def get_evaluation_questions_by_language(language: str) -> List[str]:
    """Get evaluation questions in the specified language"""
    questions = {
        "en": ["Is the language in this clause sufficiently specific and unambiguous?" ],
        "es": ["¿Es el lenguaje en esta cláusula suficientemente específico y sin ambigüedades?"],
        "pt": ["A linguagem nesta cláusula é suficientemente específica e sem ambiguidades?"]
    }

    # Default to English if language not supported
    return questions.get(language, questions["en"])


def create_basic_guidelines(contract_type_id: str,
                           clause_types: List[Dict[str, Any]],
                           guidelines_table_name: str,
                           language: str = "en") -> List[Dict[str, Any]]:
    """Create basic guidelines for each extracted clause type"""

    guidelines: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    table = dynamodb.Table(guidelines_table_name)

    for clause_type in clause_types:
        # Let the system auto-generate sequential numeric clause_type_id
        # by not providing one (it will be generated as "1", "2", "3", etc.)

        # Create basic guideline with minimal required fields
        guideline_item = {
            "contract_type_id": contract_type_id,
            # clause_type_id will be auto-generated as sequential number
            "name": clause_type["name"],
            "standard_wording": clause_type["standard_wording"],
            "level": clause_type["suggested_impact_level"],
            "evaluation_questions": get_evaluation_questions_by_language(language),  # Basic placeholder
            "examples": [],  # Empty for now, can be generated later
            "created_at": now,
            "updated_at": now
        }

        # We need to generate the clause_type_id manually here since we're not using the repository
        # Get the next sequential ID by querying existing guidelines
        try:
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('contract_type_id').eq(contract_type_id),
                ProjectionExpression='clause_type_id'
            )

            # Extract numeric clause_type_ids and find the maximum
            max_id = 0
            for item in response.get('Items', []):
                clause_id = item.get('clause_type_id', '0')
                try:
                    numeric_id = int(clause_id)
                    max_id = max(max_id, numeric_id)
                except ValueError:
                    # Skip non-numeric clause_type_ids (for backward compatibility)
                    continue

            clause_type_id = str(max_id + 1)
            guideline_item["clause_type_id"] = clause_type_id

        except Exception as e:
            logger.warning(f"Failed to generate clause_type_id, using fallback: {e}")
            # Fallback to simple sequential numbering based on current position
            clause_type_id = str(len(guidelines) + 1)
            guideline_item["clause_type_id"] = clause_type_id

        table.put_item(Item=guideline_item)
        guidelines.append(guideline_item)
        logger.info(f"Created guideline: {clause_type_id} for contract type: {contract_type_id}")

    return guidelines


def rollback_created_data(contract_type_id: Optional[str],
                         guideline_ids: List[str],
                         contract_types_table_name: str,
                         guidelines_table_name: str) -> None:
    """Rollback created contract type and guidelines on error"""

    # Delete guidelines first (due to foreign key relationship)
    guidelines_table = dynamodb.Table(guidelines_table_name)
    for clause_type_id in guideline_ids:
        try:
            if contract_type_id:
                guidelines_table.delete_item(
                    Key={
                        "contract_type_id": contract_type_id,
                        "clause_type_id": clause_type_id
                    }
                )
                logger.info(f"Rolled back guideline: {clause_type_id}")
        except Exception as e:
            logger.warning(f"Failed to rollback guideline {clause_type_id}: {e}")

    # Delete contract type
    if contract_type_id:
        try:
            contract_types_table = dynamodb.Table(contract_types_table_name)
            contract_types_table.delete_item(
                Key={"contract_type_id": contract_type_id}
            )
            logger.info(f"Rolled back contract type: {contract_type_id}")
        except Exception as e:
            logger.warning(f"Failed to rollback contract type {contract_type_id}: {e}")


@logger.inject_lambda_context(correlation_id_path=getattr(correlation_paths, 'STEP_FUNCTIONS', 'stepFunctions'))
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Finalize import by creating contract type and basic guidelines
    """

    logger.info("Starting import finalization", extra={"event": event})

    # Extract required data from event
    import_job_id = event.get("ImportJobId")
    contract_type_info = event.get("ContractTypeInfo", {})
    clause_types = event.get("ClauseTypes", [])

    if not import_job_id:
        raise ValueError("ImportJobId is required")

    if not contract_type_info:
        raise ValueError("ContractTypeInfo is required")

    if not clause_types:
        raise ValueError("ClauseTypes is required")

    # Get table names from environment
    contract_types_table_name = os.environ["CONTRACT_TYPES_TABLE_NAME"]
    guidelines_table_name = os.environ["GUIDELINES_TABLE_NAME"]
    import_jobs_table_name = os.environ["IMPORT_JOBS_TABLE_NAME"]

    contract_type_id = None
    created_guideline_ids = []

    try:
        # Update import job status to indicate finalization started
        import_jobs_table = dynamodb.Table(import_jobs_table_name)
        current_time = datetime.utcnow().isoformat()

        import_jobs_table.update_item(
            Key={"import_job_id": import_job_id},
            UpdateExpression="SET #status = :status, current_step = :current_step, progress = :progress, updated_at = :updated_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "RUNNING",
                ":current_step": "Finalize Import",
                ":progress": 80,
                ":updated_at": current_time
            }
        )

        # Get import job to retrieve document S3 key
        response = import_jobs_table.get_item(Key={"import_job_id": import_job_id})
        import_job_item = response.get('Item')
        if not import_job_item:
            raise ValueError(f"Import job {import_job_id} not found")

        document_s3_key = import_job_item.get('document_s3_key', '')

        # Create contract type
        contract_type = create_contract_type(
            contract_type_info,
            contract_types_table_name,
            document_s3_key
        )
        contract_type_id = contract_type["contract_type_id"]

        # Create basic guidelines
        contract_language = contract_type_info.get("language", "en")
        guidelines = create_basic_guidelines(
            contract_type_id,
            clause_types,
            guidelines_table_name,
            contract_language
        )
        created_guideline_ids = [g["clause_type_id"] for g in guidelines if "clause_type_id" in g]

        # Update import job status to completed
        import_jobs_table.update_item(
            Key={"import_job_id": import_job_id},
            UpdateExpression="SET #status = :status, current_step = :current_step, progress = :progress, contract_type_id = :contract_type_id, updated_at = :updated_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "SUCCEEDED",
                ":current_step": "Completed",
                ":progress": 100,
                ":contract_type_id": contract_type_id,
                ":updated_at": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"Import finalization completed successfully", extra={
            "import_job_id": import_job_id,
            "contract_type_id": contract_type_id,
            "guidelines_created": len(guidelines)
        })

        return {
            "ImportJobId": import_job_id,
            "ContractTypeId": contract_type_id,
            "GuidelinesCreated": len(guidelines),
            "Status": "SUCCEEDED"
        }

    except Exception as e:
        error_message = f"Import finalization failed: {str(e)}"
        logger.error(error_message, extra={
            "import_job_id": import_job_id,
            "contract_type_id": contract_type_id,
            "error": str(e)
        })

        # Rollback created data
        rollback_created_data(
            contract_type_id,
            created_guideline_ids,
            contract_types_table_name,
            guidelines_table_name
        )

        # Update import job status to failed
        try:
            import_jobs_table = dynamodb.Table(import_jobs_table_name)
            import_jobs_table.update_item(
                Key={"import_job_id": import_job_id},
                UpdateExpression="SET #status = :status, error_message = :error_message, current_step = :current_step, updated_at = :updated_at",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": "FAILED",
                    ":error_message": error_message,
                    ":current_step": "Finalize Import",
                    ":updated_at": datetime.utcnow().isoformat()
                }
            )
        except Exception as update_error:
            logger.error(f"Failed to update import job status: {update_error}")

        # Return error response instead of raising to allow graceful handling
        return {
            "Error": "ImportFinalizationFailed",
            "Cause": error_message,
            "ImportJobId": import_job_id,
            "Status": "FAILED"
        }