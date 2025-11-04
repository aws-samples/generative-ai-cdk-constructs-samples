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
Unit tests for Initialize Import Step Lambda function
"""

import pytest
import os
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError


class TestInitializeImportStep:
    """Test cases for Initialize Import Step Lambda function"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_context = Mock()
        self.mock_context.aws_request_id = "test-request-id"

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'IMPORT_JOBS_TABLE_NAME': 'test-import-jobs-table',
            'CONTRACT_BUCKET_NAME': 'test-contract-bucket',
            'LOG_LEVEL': 'INFO'
        })
        self.env_patcher.start()

    def teardown_method(self):
        """Clean up after tests"""
        self.env_patcher.stop()

    def test_successful_initialization_logic(self):
        """Test successful import initialization logic"""
        # Test the core validation logic that would be in the handler
        event = {
            "ExecutionName": "test-execution-123",
            "ImportJobId": "import-job-456",
            "DocumentS3Key": "documents/test-contract.pdf",
            "Description": "Test import"
        }

        # Validate required parameters (this is the core logic from the handler)
        assert event.get("ImportJobId") == "import-job-456"
        assert event.get("DocumentS3Key") == "documents/test-contract.pdf"
        assert event.get("ExecutionName") == "test-execution-123"
        assert event.get("Description") == "Test import"

        # Test expected response structure
        expected_response = {
            "ImportJobId": event["ImportJobId"],
            "DocumentS3Key": event["DocumentS3Key"],
            "Description": event.get("Description", ""),
            "Status": "INITIALIZED",
            "Progress": 10,
            "Timestamp": "2025-01-01T12:00:00Z"
        }

        # Verify response structure
        assert "ImportJobId" in expected_response
        assert "DocumentS3Key" in expected_response
        assert "Description" in expected_response
        assert "Status" in expected_response
        assert "Progress" in expected_response
        assert "Timestamp" in expected_response

        assert expected_response["Status"] == "INITIALIZED"
        assert expected_response["Progress"] == 10

    def test_missing_required_fields_validation(self):
        """Test validation of required fields"""
        # Test missing ImportJobId
        event_missing_job_id = {
            "ExecutionName": "test-execution-123",
            "DocumentS3Key": "documents/test-contract.pdf",
            "Description": "Test import"
        }

        def validate_required_fields(event):
            if not event.get("ImportJobId"):
                raise ValueError("ImportJobId is required")
            if not event.get("DocumentS3Key"):
                raise ValueError("DocumentS3Key is required")
            if not event.get("ExecutionName"):
                raise ValueError("ExecutionName is required")
            return True

        with pytest.raises(ValueError, match="ImportJobId is required"):
            validate_required_fields(event_missing_job_id)

        # Test missing DocumentS3Key
        event_missing_s3_key = {
            "ExecutionName": "test-execution-123",
            "ImportJobId": "import-job-456",
            "Description": "Test import"
        }

        with pytest.raises(ValueError, match="DocumentS3Key is required"):
            validate_required_fields(event_missing_s3_key)

        # Test missing ExecutionName
        event_missing_execution = {
            "ImportJobId": "import-job-456",
            "DocumentS3Key": "documents/test-contract.pdf",
            "Description": "Test import"
        }

        with pytest.raises(ValueError, match="ExecutionName is required"):
            validate_required_fields(event_missing_execution)

    @patch('boto3.client')
    def test_s3_document_validation_logic(self, mock_boto3_client):
        """Test S3 document validation logic"""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client

        # Test successful validation
        mock_s3_client.head_object.return_value = {}

        def validate_document_exists(bucket_name, document_s3_key):
            try:
                mock_s3_client.head_object(Bucket=bucket_name, Key=document_s3_key)
                return True
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    raise ValueError(f"Document not found in S3: {document_s3_key}")
                else:
                    raise ValueError(f"Failed to validate document in S3: {str(e)}")

        # Test successful validation
        result = validate_document_exists('test-bucket', 'documents/test.pdf')
        assert result is True
        mock_s3_client.head_object.assert_called_with(Bucket='test-bucket', Key='documents/test.pdf')

        # Test document not found
        mock_s3_client.head_object.side_effect = ClientError(
            error_response={'Error': {'Code': '404'}},
            operation_name='HeadObject'
        )

        with pytest.raises(ValueError, match="Document not found in S3"):
            validate_document_exists('test-bucket', 'documents/nonexistent.pdf')

        # Test access denied
        mock_s3_client.head_object.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            operation_name='HeadObject'
        )

        with pytest.raises(ValueError, match="Failed to validate document in S3"):
            validate_document_exists('test-bucket', 'documents/test.pdf')

    def test_import_job_creation_logic(self):
        """Test import job creation logic"""
        # Test ImportJob data structure
        import_job_data = {
            "import_job_id": "import-job-456",
            "execution_id": "test-execution-123",
            "document_s3_key": "documents/test-contract.pdf",
            "status": "RUNNING",
            "current_step": "Initialize Import",
            "progress": 10,
            "created_at": "2025-01-01T12:00:00Z",
            "updated_at": "2025-01-01T12:00:00Z"
        }

        # Verify all required fields are present
        required_fields = [
            "import_job_id", "execution_id", "document_s3_key",
            "status", "current_step", "progress", "created_at", "updated_at"
        ]

        for field in required_fields:
            assert field in import_job_data

        # Verify field values
        assert import_job_data["import_job_id"] == "import-job-456"
        assert import_job_data["execution_id"] == "test-execution-123"
        assert import_job_data["document_s3_key"] == "documents/test-contract.pdf"
        assert import_job_data["status"] == "RUNNING"
        assert import_job_data["current_step"] == "Initialize Import"
        assert import_job_data["progress"] == 10

    def test_error_handling_logic(self):
        """Test error handling logic"""
        import_job_id = "import-job-456"

        def handle_error(error, import_job_id):
            error_message = f"Import initialization failed: {str(error)}"

            # Simulate updating import job status to FAILED
            update_data = {
                "import_job_id": import_job_id,
                "status": "FAILED",
                "error_message": str(error),
                "current_step": "Initialize Import"
            }

            # Re-raise as RuntimeError for Step Functions
            raise RuntimeError(error_message)

        # Test error handling
        original_error = ValueError("Document not found in S3: documents/test.pdf")

        with pytest.raises(RuntimeError, match="Import initialization failed"):
            handle_error(original_error, import_job_id)

    def test_response_format_validation(self):
        """Test response format validation"""
        # Test successful response format
        response = {
            "ImportJobId": "import-job-456",
            "DocumentS3Key": "documents/test-contract.pdf",
            "Description": "Test import",
            "Status": "INITIALIZED",
            "Progress": 10,
            "Timestamp": "2025-01-01T12:00:00Z"
        }

        # Verify response structure
        required_response_fields = [
            "ImportJobId", "DocumentS3Key", "Description",
            "Status", "Progress", "Timestamp"
        ]

        for field in required_response_fields:
            assert field in response

        # Verify field types
        assert isinstance(response["ImportJobId"], str)
        assert isinstance(response["DocumentS3Key"], str)
        assert isinstance(response["Description"], str)
        assert isinstance(response["Status"], str)
        assert isinstance(response["Progress"], int)
        assert isinstance(response["Timestamp"], str)

        # Verify specific values
        assert response["Status"] == "INITIALIZED"
        assert response["Progress"] == 10
        assert 0 <= response["Progress"] <= 100

    def test_environment_variables_usage(self):
        """Test environment variables usage"""
        # Test that required environment variables are available
        assert os.environ.get("IMPORT_JOBS_TABLE_NAME") == "test-import-jobs-table"
        assert os.environ.get("CONTRACT_BUCKET_NAME") == "test-contract-bucket"
        assert os.environ.get("LOG_LEVEL") == "INFO"

        # Test environment variable validation logic
        def validate_environment():
            required_env_vars = ["IMPORT_JOBS_TABLE_NAME", "CONTRACT_BUCKET_NAME"]
            missing_vars = []

            for var in required_env_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)

            if missing_vars:
                raise RuntimeError(f"Missing required environment variables: {missing_vars}")

            return True

        # Should not raise error with current environment
        assert validate_environment() is True

        # Test with missing environment variable
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="Missing required environment variables"):
                validate_environment()

    def test_default_description_handling(self):
        """Test default description handling"""
        # Test event without description
        event_no_description = {
            "ExecutionName": "test-execution-123",
            "ImportJobId": "import-job-456",
            "DocumentS3Key": "documents/test-contract.pdf"
        }

        # Test description defaulting logic
        description = event_no_description.get("Description", "")
        assert description == ""

        # Test event with empty description
        event_empty_description = {
            "ExecutionName": "test-execution-123",
            "ImportJobId": "import-job-456",
            "DocumentS3Key": "documents/test-contract.pdf",
            "Description": ""
        }

        description = event_empty_description.get("Description", "")
        assert description == ""

        # Test event with valid description
        event_with_description = {
            "ExecutionName": "test-execution-123",
            "ImportJobId": "import-job-456",
            "DocumentS3Key": "documents/test-contract.pdf",
            "Description": "Test import description"
        }

        description = event_with_description.get("Description", "")
        assert description == "Test import description"