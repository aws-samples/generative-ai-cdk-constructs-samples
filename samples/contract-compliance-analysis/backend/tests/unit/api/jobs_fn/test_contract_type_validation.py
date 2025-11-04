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
from unittest.mock import Mock, patch
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
import sys
import os

# Import models with temporary path setup
def _import_with_temp_path():
    """Import models with temporary sys.path setup"""
    import sys
    jobs_fn_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'jobs_fn')
    common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer')

    original_path = sys.path.copy()
    try:
        sys.path.insert(0, jobs_fn_path)
        sys.path.insert(0, common_layer_path)
        from model import ContractType
        from schema import PostJobRequest
        return ContractType, PostJobRequest
    finally:
        sys.path[:] = original_path

ContractType, PostJobRequest = _import_with_temp_path()


def test_post_job_with_valid_active_contract_type_succeeds(jobs_index):
    """Test that posting a job with a valid active contract type succeeds"""
    post_job = jobs_index.post_job

    # Mock contract type repository
    with patch.object(jobs_index, 'contract_type_repository') as mock_repo:
        # Setup mock contract type
        mock_contract_type = ContractType(
            contract_type_id="service-agreement",
            name="Service Agreement",
            description="Service agreement contracts",
            company_party_type="Customer",
            other_party_type="Service Provider",
            is_active=True,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        mock_repo.get_contract_type.return_value = mock_contract_type

        # Mock workflows repository
        with patch.object(jobs_index, 'workflows_repository') as mock_workflows:
            mock_workflows.start_execution.return_value = "execution-123"
            mock_workflows.to_job_id.return_value = "job-123"
            mock_workflows.get_state_machine_execution_details.return_value = Mock(
                status="RUNNING",
                start_date="2024-01-01T00:00:00Z"
            )

            # Mock jobs repository
            with patch.object(jobs_index, 'jobs_repository') as mock_jobs:
                mock_jobs.record_job.return_value = None

                # Create request
                request = PostJobRequest(
                    document_s3_key="test-doc.pdf",
                    contract_type_id="service-agreement",
                    description="Test job",
                    output_language="en"
                )

                # Execute
                response = post_job(request)

                # Verify
                assert response["contractTypeId"] == "service-agreement"
                mock_repo.get_contract_type.assert_called_once_with("service-agreement")


def test_post_job_with_invalid_contract_type_raises_bad_request(jobs_index):
    """Test that posting a job with an invalid contract type raises BadRequestError"""
    post_job = jobs_index.post_job

    # Mock contract type repository
    with patch.object(jobs_index, 'contract_type_repository') as mock_repo:
        # Setup mock to return None (contract type not found)
        mock_repo.get_contract_type.return_value = None

        # Setup mock available contract types
        available_types = [
            ContractType(
                contract_type_id="service-agreement",
                name="Service Agreement",
                description="Service agreement contracts",
                company_party_type="Customer",
                other_party_type="Service Provider",
                is_active=True,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z"
            ),
            ContractType(
                contract_type_id="employment-contract",
                name="Employment Contract",
                description="Employment contracts",
                company_party_type="Employer",
                other_party_type="Employee",
                is_active=True,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z"
            )
        ]
        mock_repo.get_contract_types.return_value = available_types

        # Create request with invalid contract type
        request = PostJobRequest(
            document_s3_key="test-doc.pdf",
            contract_type_id="invalid-type",
            description="Test job",
            output_language="en"
        )

        # Execute and verify exception
        with pytest.raises(BadRequestError) as exc_info:
            post_job(request)

        assert "Invalid contract type 'invalid-type'" in str(exc_info.value)
        assert "service-agreement" in str(exc_info.value)
        assert "employment-contract" in str(exc_info.value)
        mock_repo.get_contract_type.assert_called_once_with("invalid-type")


def test_post_job_with_inactive_contract_type_raises_bad_request(jobs_index):
    """Test that posting a job with an inactive contract type raises BadRequestError"""
    post_job = jobs_index.post_job

    # Mock contract type repository
    with patch.object(jobs_index, 'contract_type_repository') as mock_repo:
        # Setup mock inactive contract type
        mock_contract_type = ContractType(
            contract_type_id="inactive-type",
            name="Inactive Type",
            description="Inactive contract type",
            company_party_type="Customer",
            other_party_type="Service Provider",
            is_active=False,  # Inactive
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        mock_repo.get_contract_type.return_value = mock_contract_type

        # Create request with inactive contract type
        request = PostJobRequest(
            document_s3_key="test-doc.pdf",
            contract_type_id="inactive-type",
            description="Test job",
            output_language="en"
        )

        # Execute and verify exception
        with pytest.raises(BadRequestError) as exc_info:
            post_job(request)

        assert "Contract type 'inactive-type' is not active" in str(exc_info.value)
        mock_repo.get_contract_type.assert_called_once_with("inactive-type")


def test_get_jobs_with_contract_type_filter(jobs_index):
    """Test that get_jobs endpoint supports contract type filtering"""
    get_jobs = jobs_index.get_jobs

    # Mock jobs repository
    with patch.object(jobs_index, 'jobs_repository') as mock_repo:
        # Mock filtered jobs
        mock_repo.get_jobs.return_value = []

        # Mock workflows repository for job details
        with patch.object(jobs_index, 'workflows_repository') as mock_workflows:
            mock_workflows.to_execution_id.return_value = "execution-123"
            mock_workflows.get_state_machine_execution_details.return_value = None

            # Execute with contract type filter
            result = get_jobs(contract_type="service-agreement")

            # Verify
            mock_repo.get_jobs.assert_called_once_with(contract_type_id="service-agreement")
            assert result == []


def test_get_jobs_without_contract_type_filter(jobs_index):
    """Test that get_jobs endpoint works without contract type filtering"""
    get_jobs = jobs_index.get_jobs

    # Mock jobs repository
    with patch.object(jobs_index, 'jobs_repository') as mock_repo:
        # Mock all jobs
        mock_repo.get_jobs.return_value = []

        # Mock workflows repository for job details
        with patch.object(jobs_index, 'workflows_repository') as mock_workflows:
            mock_workflows.to_execution_id.return_value = "execution-123"
            mock_workflows.get_state_machine_execution_details.return_value = None

            # Execute without contract type filter
            result = get_jobs()

            # Verify
            mock_repo.get_jobs.assert_called_once_with(contract_type_id=None)
            assert result == []