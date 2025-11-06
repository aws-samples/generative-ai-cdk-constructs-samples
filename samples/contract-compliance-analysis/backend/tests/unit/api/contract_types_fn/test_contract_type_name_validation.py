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
from unittest.mock import Mock
from decimal import Decimal
import sys
import os

# Add the contract types function path to sys.path for imports
contract_types_fn_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'contract_types_fn')
common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer')
if contract_types_fn_path not in sys.path:
    sys.path.insert(0, contract_types_fn_path)
if common_layer_path not in sys.path:
    sys.path.insert(0, common_layer_path)

from model import ContractType


class TestContractTypeNameValidation:
    """Test contract type name validation and uniqueness logic"""

    @pytest.fixture
    def mock_contract_type_repository(self):
        """Mock contract type repository"""
        return Mock()

    @pytest.fixture
    def existing_contract_types(self):
        """Sample existing contract types for testing uniqueness"""
        return [
            ContractType(
                contract_type_id="service-agreement",
                name="Service Agreement",
                description="Standard service agreement",
                company_party_type="Customer",
                other_party_type="Service Provider",
                high_risk_threshold=0,
                medium_risk_threshold=1,
                low_risk_threshold=3,
                is_active=True,
                default_language="en",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00"
            ),
            ContractType(
                contract_type_id="employment-contract",
                name="Employment Contract",
                description="Standard employment contract",
                company_party_type="Employer",
                other_party_type="Employee",
                high_risk_threshold=0,
                medium_risk_threshold=1,
                low_risk_threshold=3,
                is_active=True,
                default_language="en",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00"
            ),
            ContractType(
                contract_type_id="nda-agreement",
                name="NDA Agreement",
                description="Non-disclosure agreement",
                company_party_type="Discloser",
                other_party_type="Recipient",
                high_risk_threshold=0,
                medium_risk_threshold=1,
                low_risk_threshold=3,
                is_active=True,
                default_language="en",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00"
            )
        ]

    def test_slugify_name_basic_cases(self, contract_types_index):
        """Test basic name slugification"""
        _slugify_name = contract_types_index._slugify_name

        # Basic cases
        assert _slugify_name("Service Agreement") == "service-agreement"
        assert _slugify_name("Employment Contract") == "employment-contract"
        assert _slugify_name("NDA & Confidentiality") == "nda-confidentiality"

    def test_slugify_name_special_characters(self, contract_types_index):
        """Test slugification with special characters"""
        _slugify_name = contract_types_index._slugify_name

        # Special characters
        assert _slugify_name("Purchase Order (PO)") == "purchase-order-po"
        assert _slugify_name("Contract #123") == "contract-123"
        assert _slugify_name("Service @ Company") == "service-company"
        assert _slugify_name("Multi-Level Agreement") == "multi-level-agreement"

    def test_slugify_name_whitespace_handling(self, contract_types_index):
        """Test slugification with various whitespace scenarios"""
        _slugify_name = contract_types_index._slugify_name

        # Whitespace handling
        assert _slugify_name("  Multiple   Spaces  ") == "multiple-spaces"
        assert _slugify_name("Single Space") == "single-space"
        assert _slugify_name("Already-Hyphenated") == "already-hyphenated"
        assert _slugify_name("Mixed   -  Separators") == "mixed-separators"

    def test_slugify_name_edge_cases(self, contract_types_index):
        """Test slugification edge cases"""
        _slugify_name = contract_types_index._slugify_name

        # Edge cases
        assert _slugify_name("") == ""
        assert _slugify_name("   ") == ""
        assert _slugify_name("---") == ""
        assert _slugify_name("123 Contract") == "123-contract"
        assert _slugify_name("Contract---Agreement") == "contract-agreement"

    def test_ensure_unique_name_no_conflicts(self, mock_contract_type_repository, contract_types_index):
        """Test unique name generation when no conflicts exist"""
        _ensure_unique_contract_type_name_and_id = contract_types_index._ensure_unique_contract_type_name_and_id

        # Setup mock - no existing contract types
        mock_contract_type_repository.get_contract_types.return_value = []

        # Test with new name
        unique_name, unique_id = _ensure_unique_contract_type_name_and_id(
            "New Contract Type",
            mock_contract_type_repository
        )

        assert unique_name == "New Contract Type"
        assert unique_id == "new-contract-type"

    def test_ensure_unique_name_with_name_conflict(self, mock_contract_type_repository, existing_contract_types, contract_types_index):
        """Test unique name generation when name conflicts exist"""
        _ensure_unique_contract_type_name_and_id = contract_types_index._ensure_unique_contract_type_name_and_id

        # Setup mock with existing contract types
        mock_contract_type_repository.get_contract_types.return_value = existing_contract_types

        # Test with conflicting name
        unique_name, unique_id = _ensure_unique_contract_type_name_and_id(
            "Service Agreement",
            mock_contract_type_repository
        )

        assert unique_name == "Service Agreement-2"
        assert unique_id == "service-agreement-2"

    def test_ensure_unique_name_with_id_conflict(self, mock_contract_type_repository, existing_contract_types, contract_types_index):
        """Test unique name generation when ID conflicts exist"""
        _ensure_unique_contract_type_name_and_id = contract_types_index._ensure_unique_contract_type_name_and_id

        # Setup mock with existing contract types
        mock_contract_type_repository.get_contract_types.return_value = existing_contract_types

        # Test with name that generates conflicting ID
        unique_name, unique_id = _ensure_unique_contract_type_name_and_id(
            "Employment-Contract",
            mock_contract_type_repository
        )

        # Should get suffix because the generated ID conflicts
        assert unique_name == "Employment-Contract-2"
        assert unique_id == "employment-contract-2"

    def test_ensure_unique_name_multiple_conflicts(self, mock_contract_type_repository, contract_types_index):
        """Test unique name generation with multiple sequential conflicts"""
        _ensure_unique_contract_type_name_and_id = contract_types_index._ensure_unique_contract_type_name_and_id

        # Create contract types with multiple suffixes
        conflicting_types = [
            ContractType(
                contract_type_id="test-contract",
                name="Test Contract",
                description="Test",
                company_party_type="Company",
                other_party_type="Other",
                high_risk_threshold=0,
                medium_risk_threshold=1,
                low_risk_threshold=3,
                is_active=True,
                default_language="en",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00"
            ),
            ContractType(
                contract_type_id="test-contract-2",
                name="Test Contract-2",
                description="Test",
                company_party_type="Company",
                other_party_type="Other",
                high_risk_threshold=0,
                medium_risk_threshold=1,
                low_risk_threshold=3,
                is_active=True,
                default_language="en",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00"
            ),
            ContractType(
                contract_type_id="test-contract-3",
                name="Test Contract-3",
                description="Test",
                company_party_type="Company",
                other_party_type="Other",
                high_risk_threshold=0,
                medium_risk_threshold=1,
                low_risk_threshold=3,
                is_active=True,
                default_language="en",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00"
            )
        ]

        mock_contract_type_repository.get_contract_types.return_value = conflicting_types

        # Test with conflicting name
        unique_name, unique_id = _ensure_unique_contract_type_name_and_id(
            "Test Contract",
            mock_contract_type_repository
        )

        # Should get the next available suffix
        assert unique_name == "Test Contract-4"
        assert unique_id == "test-contract-4"

    def test_ensure_unique_name_case_insensitive(self, mock_contract_type_repository, contract_types_index):
        """Test that uniqueness check is case-insensitive"""
        _ensure_unique_contract_type_name_and_id = contract_types_index._ensure_unique_contract_type_name_and_id

        # Create contract type with mixed case
        existing_type = ContractType(
            contract_type_id="service-agreement",
            name="Service Agreement",
            description="Test",
            company_party_type="Company",
            other_party_type="Other",
            high_risk_threshold=0,
            medium_risk_threshold=1,
            low_risk_threshold=3,
            is_active=True,
            default_language="en",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )

        mock_contract_type_repository.get_contract_types.return_value = [existing_type]

        # Test with different case
        unique_name, unique_id = _ensure_unique_contract_type_name_and_id(
            "SERVICE AGREEMENT",
            mock_contract_type_repository
        )

        # Should detect conflict and add suffix
        assert unique_name == "SERVICE AGREEMENT-2"
        assert unique_id == "service-agreement-2"

    def test_ensure_unique_name_invalid_input(self, mock_contract_type_repository, contract_types_index):
        """Test unique name generation with invalid input"""
        _ensure_unique_contract_type_name_and_id = contract_types_index._ensure_unique_contract_type_name_and_id

        # Setup mock - no existing contract types
        mock_contract_type_repository.get_contract_types.return_value = []

        # Test with empty/invalid names
        unique_name, unique_id = _ensure_unique_contract_type_name_and_id(
            "",
            mock_contract_type_repository
        )

        # Should use fallback
        assert unique_name == "Contract Type"
        assert unique_id == "contract-type"

        # Test with only special characters
        unique_name, unique_id = _ensure_unique_contract_type_name_and_id(
            "@#$%",
            mock_contract_type_repository
        )

        # Should use fallback
        assert unique_name == "Contract Type"
        assert unique_id == "contract-type"

    def test_ensure_unique_name_whitespace_only(self, mock_contract_type_repository, contract_types_index):
        """Test unique name generation with whitespace-only input"""
        _ensure_unique_contract_type_name_and_id = contract_types_index._ensure_unique_contract_type_name_and_id

        # Setup mock - no existing contract types
        mock_contract_type_repository.get_contract_types.return_value = []

        # Test with whitespace only
        unique_name, unique_id = _ensure_unique_contract_type_name_and_id(
            "   ",
            mock_contract_type_repository
        )

        # Should use fallback
        assert unique_name == "Contract Type"
        assert unique_id == "contract-type"

    def test_ensure_unique_name_uuid_fallback(self, mock_contract_type_repository, contract_types_index):
        """Test UUID fallback when too many conflicts exist"""
        _ensure_unique_contract_type_name_and_id = contract_types_index._ensure_unique_contract_type_name_and_id

        # Create many conflicting contract types (more than the safety limit)
        conflicting_types = []
        for i in range(1, 102):  # Create conflicts up to the safety limit
            if i == 1:
                suffix = ""
            else:
                suffix = f"-{i}"

            conflicting_types.append(ContractType(
                contract_type_id=f"test-contract{suffix}",
                name=f"Test Contract{suffix}",
                description="Test",
                company_party_type="Company",
                other_party_type="Other",
                high_risk_threshold=0,
                medium_risk_threshold=1,
                low_risk_threshold=3,
                is_active=True,
                default_language="en",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00"
            ))

        mock_contract_type_repository.get_contract_types.return_value = conflicting_types

        # Test with conflicting name
        unique_name, unique_id = _ensure_unique_contract_type_name_and_id(
            "Test Contract",
            mock_contract_type_repository
        )

        # Should use UUID fallback
        assert unique_name.startswith("Test Contract-")
        assert unique_id.startswith("test-contract-")
        assert len(unique_name.split("-")[-1]) == 8  # UUID suffix length
        assert len(unique_id.split("-")[-1]) == 8  # UUID suffix length

    def test_validate_contract_type_id_valid_cases(self, contract_types_index):
        """Test contract type ID validation with valid cases"""
        _validate_contract_type_id = contract_types_index._validate_contract_type_id

        # Valid IDs should not raise exceptions
        _validate_contract_type_id("service-agreement")
        _validate_contract_type_id("employment123")
        _validate_contract_type_id("nda-confidentiality-2024")
        _validate_contract_type_id("a")
        _validate_contract_type_id("123")
        _validate_contract_type_id("contract-type-1")

    def test_validate_contract_type_id_invalid_cases(self, contract_types_index):
        """Test contract type ID validation with invalid cases"""
        _validate_contract_type_id = contract_types_index._validate_contract_type_id
        from aws_lambda_powertools.event_handler.exceptions import BadRequestError

        # Invalid IDs should raise BadRequestError
        with pytest.raises(BadRequestError, match="alphanumeric characters and hyphens"):
            _validate_contract_type_id("invalid@id")

        with pytest.raises(BadRequestError, match="alphanumeric characters and hyphens"):
            _validate_contract_type_id("invalid.id")

        with pytest.raises(BadRequestError, match="alphanumeric characters and hyphens"):
            _validate_contract_type_id("invalid id")

        with pytest.raises(BadRequestError, match="alphanumeric characters and hyphens"):
            _validate_contract_type_id("invalid_id")

        with pytest.raises(BadRequestError, match="alphanumeric characters and hyphens"):
            _validate_contract_type_id("invalid/id")

        with pytest.raises(BadRequestError, match="alphanumeric characters and hyphens"):
            _validate_contract_type_id("invalid\\id")

    def test_integration_create_contract_type_with_duplicate_name(self, mock_contract_type_repository, existing_contract_types, contract_types_index):
        """Integration test: create contract type with duplicate name should get unique suffix"""
        app = contract_types_index.app
        import json
        from unittest.mock import patch

        # Setup mocks
        mock_contract_type_repository.get_contract_types.return_value = existing_contract_types
        mock_contract_type_repository.create_contract_type.return_value = None

        # Create request with duplicate name
        request_data = {
            "name": "Service Agreement",  # This already exists
            "description": "Another service agreement",
            "companyPartyType": "Customer",
            "otherPartyType": "Service Provider",
            "highRiskThreshold": 0,
            "mediumRiskThreshold": 1,
            "lowRiskThreshold": 3,
            "isActive": True,
            "defaultLanguage": "en"
        }

        # Create test event
        event = {
            "httpMethod": "POST",
            "path": "/contract-types",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(request_data)
        }

        # Execute with mocked dependencies
        with patch.object(contract_types_index, 'contract_type_repository', mock_contract_type_repository), \
             patch.object(contract_types_index, 'datetime') as mock_datetime:

            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T00:00:00"

            response = app.resolve(event, {})

        # Verify response
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # Should have unique name and ID with suffix
        assert body["name"] == "Service Agreement-2"
        assert body["contractTypeId"] == "service-agreement-2"

        # Verify repository was called with unique values
        mock_contract_type_repository.create_contract_type.assert_called_once()
        created_contract_type = mock_contract_type_repository.create_contract_type.call_args[0][0]
        assert created_contract_type.name == "Service Agreement-2"
        assert created_contract_type.contract_type_id == "service-agreement-2"