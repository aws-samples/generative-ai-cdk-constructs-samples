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

import pytest
from datetime import datetime
from botocore.exceptions import ClientError

from model import ImportJob
from repository.dynamo_db_import_jobs_repository import DynamoDBImportJobsRepository


@pytest.fixture
def import_jobs_table_name():
    return 'test-import-jobs-table'


@pytest.fixture
def import_jobs_table(dynamodb_resource, import_jobs_table_name):
    """Get the session-scoped import jobs table and clear it before each test"""
    table = dynamodb_resource.Table(import_jobs_table_name)

    # Clear any existing items before each test
    scan_result = table.scan()
    with table.batch_writer() as batch:
        for item in scan_result.get('Items', []):
            batch.delete_item(Key={'import_job_id': item['import_job_id']})

    return table


@pytest.fixture
def sample_import_job():
    return ImportJob(
        import_job_id="import-123",
        execution_id="exec-456",
        document_s3_key="documents/contract.pdf",
        contract_type_id="service-agreement",
        status="RUNNING",
        current_step="initialize",
        progress=25,
        error_message=None,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )


def test_can_create_import_job(ddb, import_jobs_table, import_jobs_table_name, sample_import_job):
    """Test creating a new import job"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)

    # when
    repo.create_import_job(sample_import_job)

    # then
    result = ddb.get_item(
        TableName=import_jobs_table_name,
        Key={'import_job_id': {'S': sample_import_job.import_job_id}}
    )

    assert "Item" in result
    retrieved_job = result["Item"]
    assert retrieved_job["import_job_id"]["S"] == sample_import_job.import_job_id
    assert retrieved_job["execution_id"]["S"] == sample_import_job.execution_id
    assert retrieved_job["document_s3_key"]["S"] == sample_import_job.document_s3_key
    assert retrieved_job["contract_type_id"]["S"] == sample_import_job.contract_type_id
    assert retrieved_job["status"]["S"] == sample_import_job.status
    assert retrieved_job["current_step"]["S"] == sample_import_job.current_step
    assert int(retrieved_job["progress"]["N"]) == sample_import_job.progress
    # DynamoDB stores None as NULL, so check the actual value
    if "error_message" in retrieved_job:
        assert retrieved_job["error_message"]["NULL"] is True


def test_create_import_job_fails_if_already_exists(ddb, import_jobs_table, import_jobs_table_name, sample_import_job):
    """Test that creating an import job with existing ID fails"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)
    repo.create_import_job(sample_import_job)

    # when/then
    with pytest.raises(ValueError, match="Import job with ID 'import-123' already exists"):
        repo.create_import_job(sample_import_job)


def test_can_get_import_job(ddb, import_jobs_table, import_jobs_table_name, sample_import_job):
    """Test retrieving a specific import job"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)
    repo.create_import_job(sample_import_job)

    # when
    retrieved_job = repo.get_import_job(sample_import_job.import_job_id)

    # then
    assert retrieved_job is not None
    assert retrieved_job.import_job_id == sample_import_job.import_job_id
    assert retrieved_job.execution_id == sample_import_job.execution_id
    assert retrieved_job.document_s3_key == sample_import_job.document_s3_key
    assert retrieved_job.contract_type_id == sample_import_job.contract_type_id
    assert retrieved_job.status == sample_import_job.status
    assert retrieved_job.current_step == sample_import_job.current_step
    assert retrieved_job.progress == sample_import_job.progress
    assert retrieved_job.error_message == sample_import_job.error_message


def test_get_import_job_returns_none_if_not_found(import_jobs_table, import_jobs_table_name):
    """Test that getting a non-existent import job returns None"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)

    # when
    result = repo.get_import_job("non-existent-id")

    # then
    assert result is None


def test_can_update_import_job(ddb, import_jobs_table, import_jobs_table_name, sample_import_job):
    """Test updating an existing import job"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)
    repo.create_import_job(sample_import_job)

    # Modify the import job
    updated_job = ImportJob(
        import_job_id=sample_import_job.import_job_id,
        execution_id=sample_import_job.execution_id,
        document_s3_key=sample_import_job.document_s3_key,
        contract_type_id="updated-contract-type",
        status="SUCCEEDED",
        current_step="finalize",
        progress=100,
        error_message=None,
        created_at=sample_import_job.created_at,
        updated_at="2025-01-01T12:00:00Z"
    )

    # when
    repo.update_import_job(updated_job)

    # then
    retrieved = repo.get_import_job(sample_import_job.import_job_id)
    assert retrieved is not None
    assert retrieved.contract_type_id == "updated-contract-type"
    assert retrieved.status == "SUCCEEDED"
    assert retrieved.current_step == "finalize"
    assert retrieved.progress == 100
    # updated_at is automatically set by the repository, so just check it's different
    assert retrieved.updated_at != sample_import_job.updated_at


def test_update_import_job_fails_if_not_exists(import_jobs_table, import_jobs_table_name, sample_import_job):
    """Test that updating a non-existent import job fails"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)

    # when/then
    with pytest.raises(ValueError, match="Import job with ID 'import-123' does not exist"):
        repo.update_import_job(sample_import_job)


def test_can_update_import_job_status_with_all_fields(ddb, import_jobs_table, import_jobs_table_name, sample_import_job):
    """Test updating import job status with all optional fields"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)
    repo.create_import_job(sample_import_job)

    # when
    repo.update_import_job_status(
        import_job_id=sample_import_job.import_job_id,
        status="FAILED",
        error_message="Processing failed",
        progress=50,
        current_step="extract_contract_info",
        contract_type_id="new-contract-type"
    )

    # then
    retrieved = repo.get_import_job(sample_import_job.import_job_id)
    assert retrieved is not None
    assert retrieved.status == "FAILED"
    assert retrieved.error_message == "Processing failed"
    assert retrieved.progress == 50
    assert retrieved.current_step == "extract_contract_info"
    assert retrieved.contract_type_id == "new-contract-type"
    # updated_at should be automatically set
    assert retrieved.updated_at != sample_import_job.updated_at


def test_can_update_import_job_status_with_minimal_fields(ddb, import_jobs_table, import_jobs_table_name, sample_import_job):
    """Test updating import job status with only required fields"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)
    repo.create_import_job(sample_import_job)

    # when
    repo.update_import_job_status(
        import_job_id=sample_import_job.import_job_id,
        status="SUCCEEDED"
    )

    # then
    retrieved = repo.get_import_job(sample_import_job.import_job_id)
    assert retrieved is not None
    assert retrieved.status == "SUCCEEDED"
    # Other fields should remain unchanged
    assert retrieved.error_message == sample_import_job.error_message
    assert retrieved.progress == sample_import_job.progress
    assert retrieved.current_step == sample_import_job.current_step
    assert retrieved.contract_type_id == sample_import_job.contract_type_id


def test_update_import_job_status_fails_if_not_exists(import_jobs_table, import_jobs_table_name):
    """Test that updating status of a non-existent import job fails"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)

    # when/then
    with pytest.raises(ValueError, match="Import job with ID 'non-existent-id' does not exist"):
        repo.update_import_job_status("non-existent-id", "FAILED")


def test_create_import_job_with_minimal_fields(ddb, import_jobs_table, import_jobs_table_name):
    """Test creating an import job with only required fields"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)
    minimal_job = ImportJob(
        import_job_id="minimal-import",
        document_s3_key="documents/minimal.pdf",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )

    # when
    repo.create_import_job(minimal_job)

    # then
    retrieved = repo.get_import_job("minimal-import")
    assert retrieved is not None
    assert retrieved.import_job_id == "minimal-import"
    assert retrieved.document_s3_key == "documents/minimal.pdf"
    assert retrieved.execution_id is None
    assert retrieved.contract_type_id is None
    assert retrieved.status == "RUNNING"  # default value
    assert retrieved.current_step is None
    assert retrieved.progress == 0  # default value
    assert retrieved.error_message is None


def test_create_import_job_with_error_message(ddb, import_jobs_table, import_jobs_table_name):
    """Test creating an import job with an error message"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)
    error_job = ImportJob(
        import_job_id="error-import",
        document_s3_key="documents/error.pdf",
        status="FAILED",
        error_message="Document processing failed",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )

    # when
    repo.create_import_job(error_job)

    # then
    retrieved = repo.get_import_job("error-import")
    assert retrieved is not None
    assert retrieved.status == "FAILED"
    assert retrieved.error_message == "Document processing failed"


def test_update_import_job_status_sets_error_message(ddb, import_jobs_table, import_jobs_table_name):
    """Test that updating status can set error message"""
    # given
    repo = DynamoDBImportJobsRepository(table_name=import_jobs_table_name)
    job = ImportJob(
        import_job_id="set-error",
        document_s3_key="documents/set.pdf",
        status="RUNNING",
        error_message=None,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )
    repo.create_import_job(job)

    # when - set error_message
    repo.update_import_job_status(
        import_job_id="set-error",
        status="FAILED",
        error_message="New error occurred"
    )

    # then
    retrieved = repo.get_import_job("set-error")
    assert retrieved is not None
    assert retrieved.status == "FAILED"
    assert retrieved.error_message == "New error occurred"


def test_repository_handles_dynamodb_errors_gracefully(import_jobs_table, import_jobs_table_name, sample_import_job):
    """Test that repository handles DynamoDB errors gracefully"""
    # given
    repo = DynamoDBImportJobsRepository(table_name="non-existent-table")

    # when/then - should raise RuntimeError for DynamoDB issues
    with pytest.raises(RuntimeError, match="Failed to create import job in DynamoDB"):
        repo.create_import_job(sample_import_job)