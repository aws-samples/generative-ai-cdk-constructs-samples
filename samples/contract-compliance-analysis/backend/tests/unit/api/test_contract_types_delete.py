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
import sys
import os
from unittest.mock import Mock, patch
from aws_lambda_powertools.event_handler.exceptions import NotFoundError, BadRequestError

# Add the contract types function path to sys.path for imports
contract_types_fn_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'stack', 'lambda', 'api', 'contract_types_fn')
common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'stack', 'lambda', 'common_layer')
if contract_types_fn_path not in sys.path:
    sys.path.insert(0, contract_types_fn_path)
if common_layer_path not in sys.path:
    sys.path.insert(0, common_layer_path)

# Import models with temporary path setup
def _import_with_temp_path():
    """Import models with temporary sys.path setup"""
    import sys
    original_path = sys.path.copy()
    try:
        sys.path.insert(0, contract_types_fn_path)
        sys.path.insert(0, common_layer_path)
        from model import ContractType
        return ContractType
    finally:
        sys.path[:] = original_path

ContractType = _import_with_temp_path()

@pytest.fixture
def contract_types_delete_function():
    """Fixture to provide the delete_contract_type function"""
    # Mock the LLM import before importing the main module
    with patch.dict('sys.modules', {'llm': Mock()}):
        # Clear any cached index module to avoid conflicts
        if 'index' in sys.modules:
            del sys.modules['index']

        # Import specifically from contract types function
        import importlib.util
        contract_types_index_path = os.path.join(contract_types_fn_path, 'index.py')
        spec = importlib.util.spec_from_file_location("contract_types_index", contract_types_index_path)
        contract_types_index = importlib.util.module_from_spec(spec)

        # Add necessary paths to sys.path temporarily
        original_path = sys.path.copy()
        try:
            sys.path.insert(0, contract_types_fn_path)
            sys.path.insert(0, common_layer_path)
            spec.loader.exec_module(contract_types_index)
        finally:
            sys.path[:] = original_path

        return contract_types_index.delete_contract_type, contract_types_index


class TestDeleteContractType:
    """Test cases for the delete contract type API endpoint"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_contract_type_repository = Mock()
        self.mock_guidelines_repository = Mock()
        self.mock_jobs_repository = Mock()

        # Sample contract type
        self.sample_contract_type = ContractType(
            contract_type_id="test-contract",
            name="Test Contract",
            description="Test contract description",
            company_party_type="Company",
            other_party_type="Vendor",
            high_risk_threshold=0,
            medium_risk_threshold=1,
            low_risk_threshold=3,
            is_active=True,
            default_language="English",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

    def test_delete_contract_type_success(self, contract_types_delete_function):
        """Test successful contract type deletion"""
        delete_contract_type, contract_types_index = contract_types_delete_function

        # Setup mocks
        with patch.object(contract_types_index, 'contract_type_repository') as mock_contract_repo, \
             patch.object(contract_types_index, 'guidelines_repository') as mock_guidelines_repo:

            mock_contract_repo.get_contract_type.return_value = self.sample_contract_type
            mock_guidelines_repo.delete_all_guidelines_for_contract_type.return_value = 3
            mock_contract_repo.delete_contract_type.return_value = None

            # Call the function
            response = delete_contract_type("test-contract")

            # Verify calls
            mock_contract_repo.get_contract_type.assert_called_once_with("test-contract")
            mock_guidelines_repo.delete_all_guidelines_for_contract_type.assert_called_once_with("test-contract")
            mock_contract_repo.delete_contract_type.assert_called_once_with("test-contract")

            # Verify response
            assert response.status_code == 204
            assert response.body == ""

    def test_delete_contract_type_not_found(self, contract_types_delete_function):
        """Test deletion of non-existent contract type"""
        delete_contract_type, contract_types_index = contract_types_delete_function

        # Setup mock
        with patch.object(contract_types_index, 'contract_type_repository') as mock_contract_repo:
            mock_contract_repo.get_contract_type.return_value = None

            # Call the function and expect NotFoundError
            with pytest.raises(NotFoundError, match="Contract type 'nonexistent' not found"):
                delete_contract_type("nonexistent")

    def test_delete_contract_type_with_associated_jobs(self, contract_types_delete_function):
        """Test that deletion proceeds even with associated jobs (no job checking implemented)"""
        # Note: The current implementation does not check for associated jobs before deletion
        # This test verifies that the deletion proceeds successfully regardless
        delete_contract_type, contract_types_index = contract_types_delete_function

        # Setup mocks
        with patch.object(contract_types_index, 'contract_type_repository') as mock_contract_repo, \
             patch.object(contract_types_index, 'guidelines_repository') as mock_guidelines_repo:

            mock_contract_repo.get_contract_type.return_value = self.sample_contract_type
            mock_guidelines_repo.delete_all_guidelines_for_contract_type.return_value = 5
            mock_contract_repo.delete_contract_type.return_value = None

            # Call the function - should succeed even if jobs exist
            response = delete_contract_type("test-contract")

            # Verify the deletion proceeded
            mock_contract_repo.get_contract_type.assert_called_once_with("test-contract")
            mock_guidelines_repo.delete_all_guidelines_for_contract_type.assert_called_once_with("test-contract")
            mock_contract_repo.delete_contract_type.assert_called_once_with("test-contract")

            # Verify response
            assert response.status_code == 204
            assert response.body == ""

    def test_delete_contract_type_invalid_id(self, contract_types_delete_function):
        """Test deletion with invalid contract type ID"""
        delete_contract_type, contract_types_index = contract_types_delete_function

        # Call the function with invalid ID and expect BadRequestError
        with pytest.raises(BadRequestError, match="Contract type ID must contain only alphanumeric characters and hyphens"):
            delete_contract_type("invalid@id!")

    def test_delete_contract_type_repository_error(self, contract_types_delete_function):
        """Test deletion with repository error"""
        delete_contract_type, contract_types_index = contract_types_delete_function

        # Setup mocks
        with patch.object(contract_types_index, 'contract_type_repository') as mock_contract_repo, \
             patch.object(contract_types_index, 'guidelines_repository') as mock_guidelines_repo:

            mock_contract_repo.get_contract_type.return_value = self.sample_contract_type
            mock_guidelines_repo.delete_all_guidelines_for_contract_type.return_value = 0
            mock_contract_repo.delete_contract_type.side_effect = RuntimeError("Database error")

            # Call the function and expect BadRequestError
            with pytest.raises(BadRequestError, match="Failed to delete contract type"):
                delete_contract_type("test-contract")