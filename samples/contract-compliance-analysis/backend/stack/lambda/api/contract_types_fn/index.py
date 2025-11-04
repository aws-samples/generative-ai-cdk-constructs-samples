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
import re
from datetime import datetime, timezone
from http import HTTPStatus
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig, Response
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.exceptions import NotFoundError, BadRequestError
from aws_lambda_powertools import Logger

# Import from common layer (will be available at runtime)
from model import ContractType, ImportJob
from schema import ContractTypeRequest, ContractTypeResponse, ImportContractTypeRequest, ImportJobStatusResponse
from repository.dynamo_db_contract_type_repository import DynamoDBContractTypeRepository
from repository.dynamo_db_import_jobs_repository import DynamoDBImportJobsRepository
from repository.dynamodb_guidelines_repository import DynamoDBGuidelinesRepository
from repository.sfn_import_workflows_repository import StepFunctionsImportWorkflowsRepository

cors_config = CORSConfig()
app = APIGatewayRestResolver(cors=cors_config, enable_validation=True)
logger = Logger()

# Initialize repositories
contract_type_repository = DynamoDBContractTypeRepository(
    table_name=os.getenv("CONTRACT_TYPES_TABLE", "test-contract-types-table")
)
import_jobs_repository = DynamoDBImportJobsRepository(
    table_name=os.getenv("IMPORT_JOBS_TABLE", "test-import-jobs-table")
)
guidelines_repository = DynamoDBGuidelinesRepository(
    table_name=os.getenv("GUIDELINES_TABLE", "test-guidelines-table")
)
import_workflows_repository = StepFunctionsImportWorkflowsRepository(
    state_machine_arn=os.getenv('IMPORT_STATE_MACHINE_ARN', "arn:aws:states:us-east-1:123456789012:stateMachine:test-import")
)

def _validate_contract_type_id(contract_type_id: str) -> None:
    """Validate contract type ID format (alphanumeric + hyphens only)"""
    if not re.match(r'^[a-zA-Z0-9-]+$', contract_type_id):
        raise BadRequestError("Contract type ID must contain only alphanumeric characters and hyphens")

def _slugify_name(name: str) -> str:
    """Convert name to URL-friendly slug"""
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
    slug = re.sub(r'[\s-]+', '-', slug)
    return slug.strip('-')

def _generate_unique_name_and_id(base_name: str, base_id: str) -> tuple[str, str]:
    """Generate unique name and ID by adding suffix if needed"""
    existing_types = contract_type_repository.get_contract_types()
    existing_names = {ct.name.lower() for ct in existing_types}
    existing_ids = {ct.contract_type_id.lower() for ct in existing_types}

    original_name = base_name
    original_id = base_id

    # If no conflict, return as-is
    if (base_name.lower() not in existing_names and base_id.lower() not in existing_ids):
        return base_name, base_id

    # Find unique suffix starting from 2 (since 1 would be the original)
    counter = 2
    while True:
        unique_suffix = str(counter)
        test_name = f"{original_name}-{unique_suffix}"
        test_id = f"{original_id}-{unique_suffix}"

        if (test_name.lower() not in existing_names and test_id.lower() not in existing_ids):
            return test_name, test_id

        counter += 1

# Function for testing that accepts repository as parameter
def _ensure_unique_contract_type_name_and_id(base_name: str, repository) -> tuple[str, str]:
    """Generate unique name and ID by adding suffix if needed (testable version)"""
    import uuid

    # Handle invalid input with fallback
    if not base_name or not base_name.strip() or _slugify_name(base_name) == "":
        base_name = "Contract Type"

    base_id = _slugify_name(base_name)
    existing_types = repository.get_contract_types()
    existing_names = {ct.name.lower() for ct in existing_types}
    existing_ids = {ct.contract_type_id.lower() for ct in existing_types}

    original_name = base_name
    original_id = base_id

    # If no conflict, return as-is
    if (base_name.lower() not in existing_names and base_id.lower() not in existing_ids):
        return base_name, base_id

    # Find unique suffix starting from 2 (since 1 would be the original)
    counter = 2
    max_attempts = 100  # Safety limit

    while counter <= max_attempts:
        unique_suffix = str(counter)
        test_name = f"{original_name}-{unique_suffix}"
        test_id = f"{original_id}-{unique_suffix}"

        if (test_name.lower() not in existing_names and test_id.lower() not in existing_ids):
            return test_name, test_id

        counter += 1

    # UUID fallback when too many conflicts
    uuid_suffix = str(uuid.uuid4())[:8]  # 8 character UUID
    return f"{original_name}-{uuid_suffix}", f"{original_id}-{uuid_suffix}"

@app.get("/contract-types")
def get_contract_types():
    """List all available contract types"""
    contract_types = contract_type_repository.get_contract_types()
    return [ContractTypeResponse.model_validate(ct.model_dump()).model_dump(by_alias=True) for ct in contract_types]

@app.get("/contract-types/<contract_type_id>")
def get_contract_type(contract_type_id: str):
    """Get specific contract type details"""
    _validate_contract_type_id(contract_type_id)

    contract_type = contract_type_repository.get_contract_type(contract_type_id)
    if not contract_type:
        raise NotFoundError(f"Contract type '{contract_type_id}' not found")

    return ContractTypeResponse.model_validate(contract_type.model_dump()).model_dump(by_alias=True)

@app.post("/contract-types")
def create_contract_type(request: ContractTypeRequest):
    """Create a new contract type (admin only)"""
    # Validate risk thresholds are non-negative
    if request.low_risk_threshold < 0 or request.medium_risk_threshold < 0 or request.high_risk_threshold < 0:
        raise BadRequestError("Risk thresholds must be non-negative integers")

    # Generate unique name and ID
    base_id = _slugify_name(request.name)
    unique_name, unique_id = _generate_unique_name_and_id(request.name, base_id)

    # Create new contract type
    now = datetime.now(timezone.utc).isoformat()
    contract_type = ContractType(
        contract_type_id=unique_id,
        name=unique_name,
        description=request.description,
        company_party_type=request.company_party_type,
        other_party_type=request.other_party_type,
        high_risk_threshold=request.high_risk_threshold,
        medium_risk_threshold=request.medium_risk_threshold,
        low_risk_threshold=request.low_risk_threshold,
        is_active=request.is_active,
        default_language=request.default_language,
        created_at=now,
        updated_at=now
    )

    try:
        contract_type_repository.create_contract_type(contract_type)
    except ValueError as e:
        raise BadRequestError(str(e))
    except RuntimeError as e:
        logger.error(f"Failed to create contract type: {e}")
        raise BadRequestError("Failed to create contract type")

    return ContractTypeResponse.model_validate(contract_type.model_dump()).model_dump(by_alias=True)

@app.put("/contract-types/<contract_type_id>")
def update_contract_type(contract_type_id: str, request: ContractTypeRequest):
    """Update an existing contract type (admin only)"""
    _validate_contract_type_id(contract_type_id)

    # Check if contract type exists
    existing_contract_type = contract_type_repository.get_contract_type(contract_type_id)
    if not existing_contract_type:
        raise NotFoundError(f"Contract type '{contract_type_id}' not found")

    # Validate risk thresholds are non-negative
    if request.low_risk_threshold < 0 or request.medium_risk_threshold < 0 or request.high_risk_threshold < 0:
        raise BadRequestError("Risk thresholds must be non-negative integers")

    # Update contract type
    updated_contract_type = ContractType(
        contract_type_id=contract_type_id,
        name=request.name,
        description=request.description,
        company_party_type=request.company_party_type,
        other_party_type=request.other_party_type,
        high_risk_threshold=request.high_risk_threshold,
        medium_risk_threshold=request.medium_risk_threshold,
        low_risk_threshold=request.low_risk_threshold,
        is_active=request.is_active,
        default_language=request.default_language,
        created_at=existing_contract_type.created_at,
        updated_at=datetime.now(timezone.utc).isoformat()
    )

    try:
        contract_type_repository.update_contract_type(updated_contract_type)
    except ValueError as e:
        raise BadRequestError(str(e))
    except RuntimeError as e:
        logger.error(f"Failed to update contract type: {e}")
        raise BadRequestError("Failed to update contract type")

    return ContractTypeResponse.model_validate(updated_contract_type.model_dump()).model_dump(by_alias=True)

@app.delete("/contract-types/<contract_type_id>")
def delete_contract_type(contract_type_id: str):
    """Delete a contract type and all its associated guidelines (admin only)"""    

    _validate_contract_type_id(contract_type_id)

    # Check if contract type exists
    existing_contract_type = contract_type_repository.get_contract_type(contract_type_id)
    if not existing_contract_type:
        raise NotFoundError(f"Contract type '{contract_type_id}' not found")

    try:
        # Delete all guidelines for this contract type first
        deleted_guidelines_count = guidelines_repository.delete_all_guidelines_for_contract_type(contract_type_id)
        logger.info(f"Deleted {deleted_guidelines_count} guidelines for contract type '{contract_type_id}'")

        # Delete the contract type
        contract_type_repository.delete_contract_type(contract_type_id)
        logger.info(f"Successfully deleted contract type '{contract_type_id}' and {deleted_guidelines_count} associated guidelines")

        # Return success response with 204 No Content
        return Response(
            status_code=HTTPStatus.NO_CONTENT.value,
            content_type="application/json",
            body=""
        )

    except ValueError as e:
        raise BadRequestError(str(e))
    except RuntimeError as e:
        logger.error(f"Failed to delete contract type: {e}")
        raise BadRequestError("Failed to delete contract type")


@app.post("/import/contract-types")
def import_contract_type(request: ImportContractTypeRequest):
    """Start contract type import from reference document (admin only)"""
    import uuid

    try:
        # Generate unique import job ID
        import_job_id = f"import-{uuid.uuid4().hex}"

        # Create import job
        now = datetime.now(timezone.utc).isoformat()
        import_job = ImportJob(
            import_job_id=import_job_id,
            document_s3_key=request.document_s3_key,
            status="RUNNING",
            created_at=now,
            updated_at=now
        )

        import_jobs_repository.create_import_job(import_job)

        # Start import workflow
        from repository.sfn_import_workflows_repository import ImportWorkflowRequest
        workflow_request = ImportWorkflowRequest(
            document_s3_key=request.document_s3_key,
            import_job_id=import_job_id,
            description=request.description or ""
        )
        execution_id = import_workflows_repository.start_execution(workflow_request)

        return ImportJobStatusResponse(
            import_job_id=import_job_id,
            status="RUNNING",
            progress=0,
            contract_type_id=f"import-{import_job_id}",  # Generate contract type ID based on import job ID
            created_at=import_job.created_at,
            updated_at=import_job.created_at
        ).model_dump(by_alias=True)

    except ValueError as e:
        logger.error(f"Failed to start import: {e}")
        raise BadRequestError(str(e))
    except Exception as e:
        logger.error(f"Failed to start import: {e}")
        raise BadRequestError("Failed to start contract type import")

@app.get("/import/contract-types/<import_job_id>")
def get_import_status(import_job_id: str):
    """Get import job status and progress"""
    import_job = import_jobs_repository.get_import_job(import_job_id)
    if not import_job:
        raise NotFoundError(f"Import job '{import_job_id}' not found")

    # Check workflow status if job is still running and has execution_id
    if import_job.status == "RUNNING" and import_job.execution_id:
        try:
            workflow_status = import_workflows_repository.get_execution_status(import_job.execution_id)
            if workflow_status != import_job.status:
                # Update job status in database
                import_jobs_repository.update_import_job_status(
                    import_job_id=import_job_id,
                    status=workflow_status
                )
                # Update the job object for response
                import_job.status = workflow_status
        except Exception as e:
            logger.warning(f"Failed to get workflow status for {import_job_id}: {e}")

    return ImportJobStatusResponse.model_validate(import_job.model_dump()).model_dump(by_alias=True)

def handler(event, context: LambdaContext):
    return app.resolve(event, context)