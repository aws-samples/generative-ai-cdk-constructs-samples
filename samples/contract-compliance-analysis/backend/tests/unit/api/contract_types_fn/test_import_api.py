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
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import sys
import os

# Add the contract types function path to sys.path for imports
contract_types_fn_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'contract_types_fn')
common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer')
if contract_types_fn_path not in sys.path:
    sys.path.insert(0, contract_types_fn_path)
if common_layer_path not in sys.path:
    sys.path.insert(0, common_layer_path)

# Import will be handled via fixture
from model import ImportJob


class TestImportAPI:
    """Test cases for contract type import API endpoints"""

    def test_import_contract_type_success(self, contract_types_index):
        """Test successful contract type import initiation"""
        app = contract_types_index.app

        # Mock dependencies
        with patch.object(contract_types_index, 'import_jobs_repository') as mock_import_jobs_repo, \
             patch.object(contract_types_index, 'import_workflows_repository') as mock_import_workflows_repo, \
             patch('uuid.uuid4') as mock_uuid:

            # Setup mocks
            mock_uuid.return_value.hex = "abcd1234efgh5678"
            mock_import_workflows_repo.start_execution.return_value = "arn:aws:states:us-east-1:123456789012:execution:test-import:import-abcd1234efgh5678-12345678"

            # Test request
            event = {
                "httpMethod": "POST",
                "path": "/import/contract-types",
                "body": json.dumps({
                    "documentS3Key": "documents/test-contract.pdf",
                    "description": "Test contract import"
                }),
                "headers": {"Content-Type": "application/json"},
                "pathParameters": None,
                "queryStringParameters": None
            }

            # Execute
            response = app.resolve(event, {})

            # Verify response
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["importJobId"] == "import-abcd1234efgh5678"
            assert body["contractTypeId"] == "import-import-abcd1234efgh5678"
            assert body["status"] == "RUNNING"

            # Verify import job was created
            mock_import_jobs_repo.create_import_job.assert_called_once()
            created_job = mock_import_jobs_repo.create_import_job.call_args[0][0]
            assert created_job.import_job_id == "import-abcd1234efgh5678"
            assert created_job.document_s3_key == "documents/test-contract.pdf"
            assert created_job.status == "RUNNING"

            # Verify workflow was started
            mock_import_workflows_repo.start_execution.assert_called_once()
            workflow_request = mock_import_workflows_repo.start_execution.call_args[0][0]
            assert workflow_request.document_s3_key == "documents/test-contract.pdf"
            assert workflow_request.import_job_id == "import-abcd1234efgh5678"
            assert workflow_request.description == "Test contract import"

    def test_import_contract_type_invalid_request(self, contract_types_index):
        """Test import with invalid request data"""
        app = contract_types_index.app

        event = {
            "httpMethod": "POST",
            "path": "/import/contract-types",
            "body": json.dumps({
                "documentS3Key": "",  # Invalid empty key
                "description": "Test contract import"
            }),
            "headers": {"Content-Type": "application/json"},
            "pathParameters": None,
            "queryStringParameters": None
        }

        response = app.resolve(event, {})

        assert response["statusCode"] == 422  # Validation error
        body = json.loads(response["body"])
        assert "detail" in body
        assert body["detail"][0]["type"] == "string_too_short"

    def test_import_contract_type_repository_error(self, contract_types_index):
        """Test import when repository fails"""
        app = contract_types_index.app

        with patch.object(contract_types_index, 'import_jobs_repository') as mock_import_jobs_repo:
            mock_import_jobs_repo.create_import_job.side_effect = ValueError("Import job already exists")

            event = {
                "httpMethod": "POST",
                "path": "/import/contract-types",
                "body": json.dumps({
                    "documentS3Key": "documents/test-contract.pdf"
                }),
                "headers": {"Content-Type": "application/json"},
                "pathParameters": None,
                "queryStringParameters": None
            }

            response = app.resolve(event, {})

            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert "Import job already exists" in body["message"]

    def test_get_import_status_success(self, contract_types_index):
        """Test successful import status retrieval"""
        app = contract_types_index.app

        with patch.object(contract_types_index, 'import_jobs_repository') as mock_import_jobs_repo:
            # Setup mock import job
            mock_import_job = ImportJob(
                import_job_id="import-test123",
                execution_id="arn:aws:states:us-east-1:123456789012:execution:test-import:import-test123-12345678",
                document_s3_key="documents/test-contract.pdf",
                contract_type_id="service-agreement",
                status="SUCCEEDED",
                progress=100,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:05:00Z"
            )
            mock_import_jobs_repo.get_import_job.return_value = mock_import_job

            event = {
                "httpMethod": "GET",
                "path": "/import/contract-types/import-test123",
                "pathParameters": {"id": "import-test123"},
                "queryStringParameters": None
            }

            response = app.resolve(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["importJobId"] == "import-test123"
            assert body["status"] == "SUCCEEDED"
            assert body["progress"] == 100
            assert body["contractTypeId"] == "service-agreement"
            assert body["createdAt"] == "2024-01-01T00:00:00Z"
            assert body["updatedAt"] == "2024-01-01T00:05:00Z"

    def test_get_import_status_running_with_workflow_update(self, contract_types_index):
        """Test import status retrieval for running job with workflow status update"""
        app = contract_types_index.app

        with patch.object(contract_types_index, 'import_jobs_repository') as mock_import_jobs_repo, \
             patch.object(contract_types_index, 'import_workflows_repository') as mock_import_workflows_repo:

            # Setup mock import job (still running in DB)
            mock_import_job = ImportJob(
                import_job_id="import-test123",
                execution_id="arn:aws:states:us-east-1:123456789012:execution:test-import:import-test123-12345678",
                document_s3_key="documents/test-contract.pdf",
                status="RUNNING",
                progress=50,
                current_step="ExtractContractTypeInfo",
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:02:00Z"
            )
            mock_import_jobs_repo.get_import_job.return_value = mock_import_job

            # Mock workflow status as completed
            mock_import_workflows_repo.get_execution_status.return_value = "SUCCEEDED"

            event = {
                "httpMethod": "GET",
                "path": "/import/contract-types/import-test123",
                "pathParameters": {"id": "import-test123"},
                "queryStringParameters": None
            }

            response = app.resolve(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["importJobId"] == "import-test123"
            assert body["status"] == "SUCCEEDED"  # Updated from workflow
            assert body["progress"] == 50
            assert body["currentStep"] == "ExtractContractTypeInfo"

            # Verify status was updated in database
            mock_import_jobs_repo.update_import_job_status.assert_called_once_with(
                import_job_id="import-test123",
                status="SUCCEEDED"
            )

    def test_get_import_status_not_found(self, contract_types_index):
        """Test import status retrieval for non-existent job"""
        app = contract_types_index.app

        with patch.object(contract_types_index, 'import_jobs_repository') as mock_import_jobs_repo:
            mock_import_jobs_repo.get_import_job.return_value = None

            event = {
                "httpMethod": "GET",
                "path": "/import/contract-types/nonexistent",
                "pathParameters": {"id": "nonexistent"},
                "queryStringParameters": None
            }

            response = app.resolve(event, {})

            assert response["statusCode"] == 404
            body = json.loads(response["body"])
            assert "Import job 'nonexistent' not found" in body["message"]

    def test_get_import_status_with_error(self, contract_types_index):
        """Test import status retrieval for failed job"""
        app = contract_types_index.app

        with patch.object(contract_types_index, 'import_jobs_repository') as mock_import_jobs_repo:
            # Setup mock failed import job
            mock_import_job = ImportJob(
                import_job_id="import-test123",
                document_s3_key="documents/test-contract.pdf",
                status="FAILED",
                progress=25,
                error_message="Document processing failed: Invalid format",
                current_step="ExtractContractTypeInfo",
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:02:00Z"
            )
            mock_import_jobs_repo.get_import_job.return_value = mock_import_job

            event = {
                "httpMethod": "GET",
                "path": "/import/contract-types/import-test123",
                "pathParameters": {"id": "import-test123"},
                "queryStringParameters": None
            }

            response = app.resolve(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["importJobId"] == "import-test123"
            assert body["status"] == "FAILED"
            assert body["progress"] == 25
            assert body["errorMessage"] == "Document processing failed: Invalid format"
            assert body["currentStep"] == "ExtractContractTypeInfo"

    def test_import_contract_type_minimal_request(self, contract_types_index):
        """Test import with minimal required fields"""
        app = contract_types_index.app

        with patch.object(contract_types_index, 'import_jobs_repository') as mock_import_jobs_repo, \
             patch.object(contract_types_index, 'import_workflows_repository') as mock_import_workflows_repo, \
             patch('uuid.uuid4') as mock_uuid:

            mock_uuid.return_value.hex = "minimal123"
            mock_import_workflows_repo.start_execution.return_value = "arn:aws:states:us-east-1:123456789012:execution:test-import:import-minimal123-12345678"

            event = {
                "httpMethod": "POST",
                "path": "/import/contract-types",
                "body": json.dumps({
                    "documentS3Key": "documents/minimal-contract.pdf"
                    # No description provided
                }),
                "headers": {"Content-Type": "application/json"},
                "pathParameters": None,
                "queryStringParameters": None
            }

            response = app.resolve(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["importJobId"] == "import-minimal123"
            assert body["status"] == "RUNNING"

            # Verify workflow was started with empty description
            mock_import_workflows_repo.start_execution.assert_called_once()
            workflow_request = mock_import_workflows_repo.start_execution.call_args[0][0]
            assert workflow_request.description == ""

    def test_import_contract_type_workflow_start_failure(self, contract_types_index):
        """Test import when workflow fails to start"""
        app = contract_types_index.app

        with patch.object(contract_types_index, 'import_jobs_repository') as mock_import_jobs_repo, \
             patch.object(contract_types_index, 'import_workflows_repository') as mock_import_workflows_repo:

            # Mock workflow start failure
            mock_import_workflows_repo.start_execution.side_effect = RuntimeError("Failed to start workflow")

            event = {
                "httpMethod": "POST",
                "path": "/import/contract-types",
                "body": json.dumps({
                    "documentS3Key": "documents/test-contract.pdf"
                }),
                "headers": {"Content-Type": "application/json"},
                "pathParameters": None,
                "queryStringParameters": None
            }

            response = app.resolve(event, {})

            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert "Failed to start contract type import" in body["message"]

            # Verify import job was still created (for cleanup purposes)
            mock_import_jobs_repo.create_import_job.assert_called_once()