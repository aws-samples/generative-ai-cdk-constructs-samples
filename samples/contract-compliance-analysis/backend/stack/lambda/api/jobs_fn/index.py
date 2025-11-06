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

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from typing import Optional

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.exceptions import NotFoundError, BadRequestError
from aws_lambda_powertools import Logger

# Import from common layer (will be available at runtime)
from model import Job, Workflow
from schema import PostJobRequest, PostJobResponse, StartWorkflowRequest, BaseJobRespose, GetJobResponse, ClauseResponse
from repository.dynamo_db_jobs_repository import DynamoDBJobsRepository
from repository.dynamodb_clauses_repository import DynamoDBClausesRepository
from repository.dynamo_db_contract_type_repository import DynamoDBContractTypeRepository
from repository.sfn_workflows_repository import StepFunctionsWorkflowsRepository

cors_config = CORSConfig()
app = APIGatewayRestResolver(cors=cors_config, enable_validation=True)
logger = Logger()

# Initialize repositories
clauses_repository = DynamoDBClausesRepository(table_name=os.getenv("CLAUSES_TABLE", "test-clauses-table"))
jobs_repository = DynamoDBJobsRepository(table_name=os.getenv("JOBS_TABLE", "test-jobs-table"))
contract_type_repository = DynamoDBContractTypeRepository(table_name=os.getenv("CONTRACT_TYPES_TABLE", "test-contract-types-table"))
workflows_repository = StepFunctionsWorkflowsRepository(
    state_machine_arn=os.getenv('STATE_MACHINE_ARN', "arn:aws:states:us-east-1:123456789012:stateMachine:test")
)

def build_checks_object(job: Job, guidelines_workflow_status: str, legislation_workflow: Optional[Workflow] = None):
    """Build checks object for job response"""
    guidelines_check = {
        "compliant": job.guidelines_compliant,
        "processingStatus": guidelines_workflow_status,
    }
    
    # Only include metrics if they're available (job is complete)
    if job.total_clause_types_by_risk is not None:
        guidelines_check["metrics"] = {
            "totalClauseTypesByRisk": job.total_clause_types_by_risk,
            "totalComplianceByImpact": job.total_compliance_by_impact,
            "unknownTotal": job.unknown_total
        }

    legislation_check = None
    if legislation_workflow:
        legislation_check = {
            "compliant": job.legislation_compliant,
            "processingStatus": legislation_workflow.status
        }

    return {
        "guidelines": guidelines_check,
        "legislation": legislation_check
    }

def get_final_end_date(contract_workflow: Workflow, legislation_workflow: Optional[Workflow]) -> str | None:
    """Get the latest end date considering both contract analysis and legislation check workflows"""
    if not contract_workflow.end_date:
        return None
    
    # If no legislation check, return contract workflow end date
    if not legislation_workflow or not legislation_workflow.end_date:
        return str(contract_workflow.end_date)
    
    # Return the later of the two end dates
    return str(max(contract_workflow.end_date, legislation_workflow.end_date))

@app.get("/jobs")
def get_jobs(contract_type: Optional[str] = None):
    jobs = jobs_repository.get_jobs(contract_type_id=contract_type)

    def fill_job_details(job: Job) -> GetJobResponse:
        execution_id = workflows_repository.to_execution_id(job.id)
        if workflow := workflows_repository.get_state_machine_execution_details(execution_id):
            # Fetch legislation workflow once if it exists
            legislation_workflow = None
            if job.legislation_check_execution_arn:
                legislation_workflow = workflows_repository.get_state_machine_execution_details(job.legislation_check_execution_arn)
            
            return BaseJobRespose(
                id=job.id,
                description=job.description,
                document_s3_key=job.document_s3_key,
                contract_type_id=job.contract_type_id,
                start_date=str(workflow.start_date),
                end_date=get_final_end_date(workflow, legislation_workflow),
                checks=build_checks_object(job, workflow.status, legislation_workflow),
            )
        logger.warning(f"No workflow execution found for job {job.id}")
        return None

    # Fill workflow execution details
    jobs_with_workflow_details = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(fill_job_details, job) for job in jobs]
        jobs_with_workflow_details = [r.result() for r in as_completed(futures) if r.result()]

    return [j.model_dump(by_alias=True, exclude={'clauses'}) for j in jobs_with_workflow_details]

@app.get("/jobs/<job_id>")
def get_job(job_id: str):
    if job := jobs_repository.get_job(job_id):
        execution_id = workflows_repository.to_execution_id(job_id)
        if workflow := workflows_repository.get_state_machine_execution_details(execution_id):
            clauses = clauses_repository.get_clauses(job_id)

            # Fetch legislation workflow once if it exists
            legislation_workflow = None
            if job.legislation_check_execution_arn:
                legislation_workflow = workflows_repository.get_state_machine_execution_details(job.legislation_check_execution_arn)

            # Handle edge case for v2 job from v1 endpoint
            document_s3_key = job.document_s3_key if isinstance(job, Job) else job.document_s3_path

            return GetJobResponse(
                id=job_id,
                description=job.description,
                document_s3_key=document_s3_key,
                contract_type_id=job.contract_type_id,
                start_date=str(workflow.start_date),
                end_date=get_final_end_date(workflow, legislation_workflow),
                checks=build_checks_object(job, workflow.status, legislation_workflow),
                clauses=[ClauseResponse.model_validate(clause) for clause in clauses],
            ).model_dump(by_alias=True)

    raise NotFoundError

@app.post("/jobs")
def post_job(request: PostJobRequest):
    logger.info(f"Posting job with {request}")

    # Validate contract type exists and is active
    contract_type = contract_type_repository.get_contract_type(request.contract_type_id)
    if not contract_type:
        # Get available contract types for error message
        available_types = contract_type_repository.get_contract_types()
        available_type_ids = [ct.contract_type_id for ct in available_types if ct.is_active]
        raise BadRequestError(f"Invalid contract type '{request.contract_type_id}'. Available contract types: {available_type_ids}")

    if not contract_type.is_active:
        raise BadRequestError(f"Contract type '{request.contract_type_id}' is not active")

    start_workflow_request = StartWorkflowRequest(
        document_s3_path=f"s3://{os.getenv('DOCUMENTS_BUCKET', 'test-bucket')}/{request.document_s3_key}",
        contract_type_id=request.contract_type_id,
        output_language=request.output_language,
        additional_checks=request.additional_checks
    )

    execution_id = workflows_repository.start_execution(start_workflow_request)
    job_id = workflows_repository.to_job_id(execution_id)

    job = Job(
        id=job_id,
        document_s3_key=request.document_s3_key,
        contract_type_id=request.contract_type_id,
        description=request.description
    )
    jobs_repository.record_job(job)

    execution_details = workflows_repository.get_state_machine_execution_details(execution_id)

    response = PostJobResponse(
        id=job_id,
        document_s3_key=request.document_s3_key,
        contract_type_id=request.contract_type_id,
        start_date=str(execution_details.start_date)
    )

    return response.model_dump(by_alias=True)

def handler(event, context: LambdaContext):
    return app.resolve(event, context)