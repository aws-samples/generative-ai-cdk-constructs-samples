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
from model import ImportJob


def test_import_job_model_with_required_fields():
    """Test ImportJob model with only required fields"""
    import_job = ImportJob(
        import_job_id="import-123",
        document_s3_key="documents/contract.pdf",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )

    assert import_job.import_job_id == "import-123"
    assert import_job.document_s3_key == "documents/contract.pdf"
    assert import_job.execution_id is None  # default value
    assert import_job.contract_type_id is None  # default value
    assert import_job.status == "RUNNING"  # default value
    assert import_job.current_step is None  # default value
    assert import_job.progress == 0  # default value
    assert import_job.error_message is None  # default value
    assert import_job.created_at == "2025-01-01T00:00:00Z"
    assert import_job.updated_at == "2025-01-01T00:00:00Z"


def test_import_job_model_with_all_fields():
    """Test ImportJob model with all fields specified"""
    import_job = ImportJob(
        import_job_id="import-456",
        execution_id="exec-789",
        document_s3_key="documents/service-agreement.docx",
        contract_type_id="service-agreement",
        status="SUCCEEDED",
        current_step="finalize",
        progress=100,
        error_message=None,
        created_at="2025-01-01T10:00:00Z",
        updated_at="2025-01-01T12:00:00Z"
    )

    assert import_job.import_job_id == "import-456"
    assert import_job.execution_id == "exec-789"
    assert import_job.document_s3_key == "documents/service-agreement.docx"
    assert import_job.contract_type_id == "service-agreement"
    assert import_job.status == "SUCCEEDED"
    assert import_job.current_step == "finalize"
    assert import_job.progress == 100
    assert import_job.error_message is None
    assert import_job.created_at == "2025-01-01T10:00:00Z"
    assert import_job.updated_at == "2025-01-01T12:00:00Z"


def test_import_job_model_with_error():
    """Test ImportJob model with error state"""
    import_job = ImportJob(
        import_job_id="import-error",
        document_s3_key="documents/invalid.pdf",
        status="FAILED",
        current_step="extract_contract_info",
        progress=25,
        error_message="Document format not supported",
        created_at="2025-01-01T08:00:00Z",
        updated_at="2025-01-01T08:30:00Z"
    )

    assert import_job.import_job_id == "import-error"
    assert import_job.status == "FAILED"
    assert import_job.current_step == "extract_contract_info"
    assert import_job.progress == 25
    assert import_job.error_message == "Document format not supported"


def test_import_job_model_missing_required_fields():
    """Test that ImportJob model raises validation error for missing required fields"""
    # Missing import_job_id
    with pytest.raises(ValueError, match="Field required"):
        ImportJob(
            document_s3_key="documents/contract.pdf",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )

    # Missing document_s3_key
    with pytest.raises(ValueError, match="Field required"):
        ImportJob(
            import_job_id="import-123",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )

    # Missing created_at
    with pytest.raises(ValueError, match="Field required"):
        ImportJob(
            import_job_id="import-123",
            document_s3_key="documents/contract.pdf",
            updated_at="2025-01-01T00:00:00Z"
        )


def test_import_job_id_validation():
    """Test import job ID validation"""
    # Valid import job IDs
    valid_ids = ["import-123", "import_456", "IMPORT-789", "import123"]
    for job_id in valid_ids:
        import_job = ImportJob(
            import_job_id=job_id,
            document_s3_key="documents/contract.pdf",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )
        assert import_job.import_job_id == job_id

    # Invalid import job IDs
    invalid_ids = ["", "  ", "import@123", "import 123", "import/123"]
    for job_id in invalid_ids:
        with pytest.raises(ValueError):
            ImportJob(
                import_job_id=job_id,
                document_s3_key="documents/contract.pdf",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z"
            )


def test_document_s3_key_validation():
    """Test document S3 key validation"""
    # Valid S3 keys
    valid_keys = ["documents/contract.pdf", "folder/subfolder/file.docx", "simple.txt"]
    for s3_key in valid_keys:
        import_job = ImportJob(
            import_job_id="import-123",
            document_s3_key=s3_key,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )
        assert import_job.document_s3_key == s3_key

    # Invalid S3 keys
    invalid_keys = ["", "  ", "   "]
    for s3_key in invalid_keys:
        with pytest.raises(ValueError):
            ImportJob(
                import_job_id="import-123",
                document_s3_key=s3_key,
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z"
            )


def test_progress_validation():
    """Test progress field validation"""
    # Valid progress values
    valid_progress = [0, 25, 50, 75, 100]
    for progress in valid_progress:
        import_job = ImportJob(
            import_job_id="import-123",
            document_s3_key="documents/contract.pdf",
            progress=progress,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )
        assert import_job.progress == progress

    # Invalid progress values
    invalid_progress = [-1, 101, 150]
    for progress in invalid_progress:
        with pytest.raises(ValueError):
            ImportJob(
                import_job_id="import-123",
                document_s3_key="documents/contract.pdf",
                progress=progress,
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z"
            )


def test_status_validation():
    """Test status field validation"""
    # Valid status values
    valid_statuses = ["RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]
    for status in valid_statuses:
        import_job = ImportJob(
            import_job_id="import-123",
            document_s3_key="documents/contract.pdf",
            status=status,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )
        assert import_job.status == status

    # Invalid status values
    invalid_statuses = ["PENDING", "COMPLETED", "ERROR", "invalid"]
    for status in invalid_statuses:
        with pytest.raises(ValueError):
            ImportJob(
                import_job_id="import-123",
                document_s3_key="documents/contract.pdf",
                status=status,
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z"
            )


def test_error_message_validation():
    """Test error message validation and truncation"""
    # Valid error message
    import_job = ImportJob(
        import_job_id="import-123",
        document_s3_key="documents/contract.pdf",
        error_message="Short error message",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )
    assert import_job.error_message == "Short error message"

    # Long error message should be truncated
    long_message = "x" * 1500  # 1500 characters
    import_job = ImportJob(
        import_job_id="import-123",
        document_s3_key="documents/contract.pdf",
        error_message=long_message,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )
    assert len(import_job.error_message) == 1000  # Should be truncated to 1000 chars
    assert import_job.error_message.endswith("...")

    # Empty error message should be None
    import_job = ImportJob(
        import_job_id="import-123",
        document_s3_key="documents/contract.pdf",
        error_message="   ",  # Only whitespace
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )
    assert import_job.error_message is None


def test_import_job_model_serialization():
    """Test ImportJob model serialization to dict"""
    import_job = ImportJob(
        import_job_id="import-serialize",
        execution_id="exec-serialize",
        document_s3_key="documents/test.pdf",
        contract_type_id="test-contract",
        status="RUNNING",
        current_step="initialize",
        progress=10,
        error_message=None,
        created_at="2025-01-01T08:00:00Z",
        updated_at="2025-01-01T08:05:00Z"
    )

    serialized = import_job.model_dump()

    expected = {
        "import_job_id": "import-serialize",
        "execution_id": "exec-serialize",
        "document_s3_key": "documents/test.pdf",
        "contract_type_id": "test-contract",
        "status": "RUNNING",
        "current_step": "initialize",
        "progress": 10,
        "error_message": None,
        "created_at": "2025-01-01T08:00:00Z",
        "updated_at": "2025-01-01T08:05:00Z"
    }

    assert serialized == expected


def test_import_job_model_deserialization():
    """Test ImportJob model deserialization from dict"""
    data = {
        "import_job_id": "import-deserialize",
        "execution_id": "exec-deserialize",
        "document_s3_key": "documents/deserialize.docx",
        "contract_type_id": "deserialize-contract",
        "status": "SUCCEEDED",
        "current_step": "finalize",
        "progress": 100,
        "error_message": None,
        "created_at": "2025-01-01T14:00:00Z",
        "updated_at": "2025-01-01T15:00:00Z"
    }

    import_job = ImportJob.model_validate(data)

    assert import_job.import_job_id == "import-deserialize"
    assert import_job.execution_id == "exec-deserialize"
    assert import_job.document_s3_key == "documents/deserialize.docx"
    assert import_job.contract_type_id == "deserialize-contract"
    assert import_job.status == "SUCCEEDED"
    assert import_job.current_step == "finalize"
    assert import_job.progress == 100
    assert import_job.error_message is None
    assert import_job.created_at == "2025-01-01T14:00:00Z"
    assert import_job.updated_at == "2025-01-01T15:00:00Z"