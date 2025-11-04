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
import sys
import os
from unittest.mock import Mock

def get_contract_types_module():
    """Get the contract types module with isolated imports"""
    import importlib.util
    import sys
    from unittest.mock import Mock

    # Clear any cached modules to avoid conflicts
    modules_to_clear = [k for k in sys.modules.keys() if k.startswith('contract_types_index') or (k == 'index' and 'contract_types_fn' in str(sys.modules.get(k, '')))]
    for module in modules_to_clear:
        del sys.modules[module]

    # Set up paths
    contract_types_path = os.path.join(os.path.dirname(__file__), '..', '..', 'stack', 'lambda', 'api', 'contract_types_fn')
    common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', 'stack', 'lambda', 'common_layer')

    # Import with temporary path setup and mocked dependencies
    original_path = sys.path.copy()
    original_modules = {}

    # Store original modules that we'll temporarily mock
    mock_modules = [
        'repository.dynamo_db_contract_type_repository',
        'repository.dynamodb_guidelines_repository',
        'repository.dynamo_db_import_jobs_repository',
        'repository.sfn_import_workflows_repository',
        'model',
        'schema'
    ]

    for module_name in mock_modules:
        if module_name in sys.modules:
            original_modules[module_name] = sys.modules[module_name]
        sys.modules[module_name] = Mock()

    try:
        sys.path.insert(0, contract_types_path)
        sys.path.insert(0, common_layer_path)

        contract_types_index_path = os.path.join(contract_types_path, 'index.py')
        spec = importlib.util.spec_from_file_location("contract_types_index", contract_types_index_path)
        contract_types_index = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(contract_types_index)

        return contract_types_index
    finally:
        sys.path[:] = original_path
        # Restore original modules
        for module_name in mock_modules:
            if module_name in original_modules:
                sys.modules[module_name] = original_modules[module_name]
            else:
                sys.modules.pop(module_name, None)

@pytest.fixture
def contract_types_module():
    """Fixture to provide the contract types module"""
    return get_contract_types_module()


# Mock contract type for testing
class MockContractType:
    def __init__(self, contract_type_id, name, **kwargs):
        self.contract_type_id = contract_type_id
        self.name = name
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestFinalizeImportNameValidation:
    """Test name validation logic in import finalize step"""

    @pytest.fixture
    def mock_contract_type_repository(self):
        """Mock contract type repository"""
        return Mock()

    @pytest.fixture
    def existing_contract_types(self):
        """Sample existing contract types for testing uniqueness"""
        return [
            MockContractType(
                contract_type_id="service-agreement",
                name="Service Agreement"
            ),
            MockContractType(
                contract_type_id="employment-contract",
                name="Employment Contract"
            )
        ]

    def test_slugify_name_consistency_with_api(self, contract_types_module):
        """Test that import slugification is consistent with API slugification"""
        # Test various names to ensure consistency
        test_names = [
            "Service Agreement",
            "Employment Contract",
            "NDA & Confidentiality",
            "Purchase Order (PO)",
            "Multi-Level Agreement",
            "  Multiple   Spaces  ",
            "Already-Hyphenated"
        ]

        for name in test_names:
            import_slug = contract_types_module._slugify_name(name)

            # Simulate API slugification (from the API module)
            import re
            api_slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
            api_slug = re.sub(r'\s+', '-', api_slug)
            api_slug = re.sub(r'-+', '-', api_slug)
            api_slug = api_slug.strip('-')

            assert import_slug == api_slug, f"Inconsistent slugification for '{name}': import='{import_slug}', api='{api_slug}'"

    def test_ensure_unique_name_no_conflicts(self, contract_types_module, mock_contract_type_repository):
        """Test unique name generation when no conflicts exist in import"""
        # Setup mock - no existing contract types
        mock_contract_type_repository.get_contract_types.return_value = []

        # Test with new name
        unique_name, unique_id = contract_types_module._ensure_unique_contract_type_name_and_id(
            "New Contract Type",
            mock_contract_type_repository
        )

        assert unique_name == "New Contract Type"
        assert unique_id == "new-contract-type"

    def test_ensure_unique_name_with_name_conflict(self, contract_types_module, mock_contract_type_repository, existing_contract_types):
        """Test unique name generation when name conflicts exist in import"""
        # Setup mock with existing contract types
        mock_contract_type_repository.get_contract_types.return_value = existing_contract_types

        # Test with conflicting name
        unique_name, unique_id = contract_types_module._ensure_unique_contract_type_name_and_id(
            "Service Agreement",
            mock_contract_type_repository
        )

        assert unique_name == "Service Agreement-2"
        assert unique_id == "service-agreement-2"

    def test_ensure_unique_name_with_id_conflict(self, contract_types_module, mock_contract_type_repository, existing_contract_types):
        """Test unique name generation when ID conflicts exist in import"""
        # Setup mock with existing contract types
        mock_contract_type_repository.get_contract_types.return_value = existing_contract_types

        # Test with name that generates conflicting ID
        unique_name, unique_id = contract_types_module._ensure_unique_contract_type_name_and_id(
            "Employment-Contract",
            mock_contract_type_repository
        )

        # Should get suffix because the generated ID conflicts
        assert unique_name == "Employment-Contract-2"
        assert unique_id == "employment-contract-2"

    def test_ensure_unique_name_case_insensitive(self, contract_types_module, mock_contract_type_repository):
        """Test that uniqueness check is case-insensitive in import"""
        # Create contract type with mixed case
        existing_type = MockContractType(
            contract_type_id="service-agreement",
            name="Service Agreement"
        )

        mock_contract_type_repository.get_contract_types.return_value = [existing_type]

        # Test with different case
        unique_name, unique_id = contract_types_module._ensure_unique_contract_type_name_and_id(
            "SERVICE AGREEMENT",
            mock_contract_type_repository
        )

        # Should detect conflict and add suffix
        assert unique_name == "SERVICE AGREEMENT-2"
        assert unique_id == "service-agreement-2"

    def test_ensure_unique_name_invalid_input(self, contract_types_module, mock_contract_type_repository):
        """Test unique name generation with invalid input in import"""
        # Setup mock - no existing contract types
        mock_contract_type_repository.get_contract_types.return_value = []

        # Test with empty/invalid names
        unique_name, unique_id = contract_types_module._ensure_unique_contract_type_name_and_id(
            "",
            mock_contract_type_repository
        )

        # Should use fallback
        assert unique_name == "Contract Type"
        assert unique_id == "contract-type"

        # Test with only special characters
        unique_name, unique_id = contract_types_module._ensure_unique_contract_type_name_and_id(
            "@#$%",
            mock_contract_type_repository
        )

        # Should use fallback
        assert unique_name == "Contract Type"
        assert unique_id == "contract-type"

    def test_ensure_unique_name_multiple_conflicts(self, contract_types_module, mock_contract_type_repository):
        """Test unique name generation with multiple sequential conflicts in import"""
        # Create contract types with multiple suffixes
        conflicting_types = [
            MockContractType(
                contract_type_id="test-contract",
                name="Test Contract"
            ),
            MockContractType(
                contract_type_id="test-contract-2",
                name="Test Contract-2"
            ),
            MockContractType(
                contract_type_id="test-contract-3",
                name="Test Contract-3"
            )
        ]

        mock_contract_type_repository.get_contract_types.return_value = conflicting_types

        # Test with conflicting name
        unique_name, unique_id = contract_types_module._ensure_unique_contract_type_name_and_id(
            "Test Contract",
            mock_contract_type_repository
        )

        # Should get the next available suffix
        assert unique_name == "Test Contract-4"
        assert unique_id == "test-contract-4"


if __name__ == "__main__":
    pytest.main([__file__])