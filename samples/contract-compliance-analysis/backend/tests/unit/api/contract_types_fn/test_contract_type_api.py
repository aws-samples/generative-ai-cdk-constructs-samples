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
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch

from aws_lambda_powertools.event_handler.exceptions import NotFoundError, BadRequestError

class TestContractTypeAPI:
    """Test contract type management API endpoints"""

    @pytest.fixture
    def mock_contract_type_repository(self):
        """Mock contract type repository"""
        return Mock()

    @pytest.fixture
    def sample_contract_type(self, contract_types_models):
        """Sample contract type for testing"""
        return contract_types_models.ContractType(
            contract_type_id="service-agreement",
            name="Service Agreement",
            description="Standard service agreement contract",
            company_party_type="Customer",
            other_party_type="Service Provider",
            high_risk_threshold=0,
            medium_risk_threshold=1,
            low_risk_threshold=3,
            is_active=True,
            default_language="en",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )

    @pytest.fixture
    def sample_contract_type_request(self):
        """Sample contract type request for testing"""
        return {
            "name": "Service Agreement",
            "description": "Standard service agreement contract",
            "companyPartyType": "Customer",
            "otherPartyType": "Service Provider",
            "highRiskThreshold": 0,
            "mediumRiskThreshold": 1,
            "lowRiskThreshold": 3,
            "isActive": True,
            "defaultLanguage": "en"
        }

    def test_get_contract_types_success(self, sample_contract_type, contract_types_index):
        """Test successful retrieval of all contract types"""
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo:
            app = contract_types_index.app

            # Setup mock
            mock_repo.get_contract_types.return_value = [sample_contract_type]

            # Create test event
            event = {
                "httpMethod": "GET",
                "path": "/contract-types",
                "headers": {},
                "body": None
            }

            # Execute
            response = app.resolve(event, {})

            # Verify
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert len(body) == 1
            assert body[0]["contractTypeId"] == "service-agreement"
            assert body[0]["name"] == "Service Agreement"
            mock_repo.get_contract_types.assert_called_once()

    def test_get_contract_types_empty(self, contract_types_index):
        """Test retrieval when no contract types exist"""
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo:
            app = contract_types_index.app

            # Setup mock
            mock_repo.get_contract_types.return_value = []

            # Create test event
            event = {
                "httpMethod": "GET",
                "path": "/contract-types",
                "headers": {},
                "body": None
            }

            # Execute
            response = app.resolve(event, {})

            # Verify
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body == []

    def test_get_contract_type_success(self, sample_contract_type, contract_types_index):
        """Test successful retrieval of specific contract type"""
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo:
            app = contract_types_index.app

            # Setup mock
            mock_repo.get_contract_type.return_value = sample_contract_type

            # Create test event
            event = {
                "httpMethod": "GET",
                "path": "/contract-types/service-agreement",
                "pathParameters": {"contract_type_id": "service-agreement"},
                "headers": {},
                "body": None
            }

            # Execute
            response = app.resolve(event, {})

            # Verify
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["contractTypeId"] == "service-agreement"
            assert body["name"] == "Service Agreement"
            mock_repo.get_contract_type.assert_called_once_with("service-agreement")

    def test_get_contract_type_not_found(self, contract_types_index):
        """Test retrieval of non-existent contract type"""
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo:
            app = contract_types_index.app

            # Setup mock
            mock_repo.get_contract_type.return_value = None

            # Create test event
            event = {
                "httpMethod": "GET",
                "path": "/contract-types/non-existent",
                "pathParameters": {"contract_type_id": "non-existent"},
                "headers": {},
                "body": None
            }

            # Execute
            response = app.resolve(event, {})

            # Verify
            assert response["statusCode"] == 404
            body = json.loads(response["body"])
            assert "not found" in body["message"].lower()

    def test_get_contract_type_invalid_id(self, contract_types_index):
        """Test retrieval with invalid contract type ID format"""
        app = contract_types_index.app

        # Create test event with invalid ID (contains special characters)
        event = {
            "httpMethod": "GET",
            "path": "/contract-types/invalid@id",
            "pathParameters": {"contract_type_id": "invalid@id"},
            "headers": {},
            "body": None
        }

        # Execute
        response = app.resolve(event, {})

        # Verify
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "alphanumeric characters and hyphens" in body["message"]

    def test_create_contract_type_success(self, sample_contract_type_request, contract_types_index):
        """Test successful creation of contract type"""
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo, \
             patch.object(contract_types_index, 'datetime') as mock_datetime:

            app = contract_types_index.app

            # Setup mocks
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T00:00:00"
            mock_repo.get_contract_types.return_value = []  # No existing contract types
            mock_repo.create_contract_type.return_value = None

            # Create test event
            event = {
                "httpMethod": "POST",
                "path": "/contract-types",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(sample_contract_type_request)
            }

            # Execute
            response = app.resolve(event, {})

            # Verify
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["contractTypeId"] == "service-agreement"
            assert body["name"] == "Service Agreement"
            assert body["createdAt"] == "2024-01-01T00:00:00"
            assert body["updatedAt"] == "2024-01-01T00:00:00"

            # Verify repository calls - now uses get_contract_types for uniqueness check
            mock_repo.get_contract_types.assert_called_once()
            mock_repo.create_contract_type.assert_called_once()

    def test_create_contract_type_with_duplicate_name_gets_suffix(self, sample_contract_type_request, sample_contract_type, contract_types_index):
        """Test creation when contract type name already exists - should get unique suffix"""
        app = contract_types_index.app

        # Setup mocks
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo, \
             patch.object(contract_types_index, 'datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T00:00:00"
            mock_repo.get_contract_types.return_value = [sample_contract_type]  # Existing contract type
            mock_repo.create_contract_type.return_value = None

            # Create test event
            event = {
                "httpMethod": "POST",
                "path": "/contract-types",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(sample_contract_type_request)
            }

            # Execute
            response = app.resolve(event, {})

            # Verify - should succeed with unique suffix
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["contractTypeId"] == "service-agreement-2"
            assert body["name"] == "Service Agreement-2"

            # Verify repository calls
            mock_repo.get_contract_types.assert_called_once()
            mock_repo.create_contract_type.assert_called_once()

            # Verify the created contract type has unique values
            created_contract_type = mock_repo.create_contract_type.call_args[0][0]
            assert created_contract_type.name == "Service Agreement-2"
            assert created_contract_type.contract_type_id == "service-agreement-2"

    def test_create_contract_type_invalid_risk_thresholds(self, contract_types_index):
        """Test creation with invalid risk thresholds (negative values)"""
        app = contract_types_index.app

        # Create request with invalid thresholds (negative values)
        invalid_request = {
            "name": "Test Contract",
            "description": "Test description",
            "companyPartyType": "Customer",
            "otherPartyType": "Provider",
            "highRiskThreshold": -1,  # Invalid: negative value
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
            "body": json.dumps(invalid_request)
        }

        # Execute
        response = app.resolve(event, {})

        # Verify
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "non-negative" in body["message"]

    def test_create_contract_type_repository_error(self, sample_contract_type_request, contract_types_index):
        """Test creation when repository raises an error"""
        app = contract_types_index.app

        # Setup mock - repository raises ValueError
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo:
            mock_repo.get_contract_types.return_value = []
            mock_repo.create_contract_type.side_effect = ValueError("Database error")

            # Create test event
            event = {
                "httpMethod": "POST",
                "path": "/contract-types",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(sample_contract_type_request)
            }

            # Execute
            response = app.resolve(event, {})

            # Verify
            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert "Database error" in body["message"]

    def test_update_contract_type_success(self, sample_contract_type_request, sample_contract_type, contract_types_index):
        """Test successful update of contract type"""
        app = contract_types_index.app

        # Setup mocks
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo, \
             patch.object(contract_types_index, 'datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-02T00:00:00"
            mock_repo.get_contract_type.return_value = sample_contract_type
            mock_repo.update_contract_type.return_value = None

            # Create updated request
            updated_request = sample_contract_type_request.copy()
            updated_request["name"] = "Updated Service Agreement"

            # Create test event
            event = {
                "httpMethod": "PUT",
                "path": "/contract-types/service-agreement",
                "pathParameters": {"contract_type_id": "service-agreement"},
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(updated_request)
            }

            # Execute
            response = app.resolve(event, {})

            # Verify
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["contractTypeId"] == "service-agreement"
            assert body["name"] == "Updated Service Agreement"
            assert body["createdAt"] == "2024-01-01T00:00:00"  # Preserved
            assert body["updatedAt"] == "2024-01-02T00:00:00"  # Updated

            # Verify repository calls
            mock_repo.get_contract_type.assert_called_once_with("service-agreement")
            mock_repo.update_contract_type.assert_called_once()

    def test_update_contract_type_not_found(self, sample_contract_type_request, contract_types_index):
        """Test update of non-existent contract type"""
        app = contract_types_index.app

        # Setup mock - contract type doesn't exist
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo:
            mock_repo.get_contract_type.return_value = None

            # Create test event
            event = {
                "httpMethod": "PUT",
                "path": "/contract-types/non-existent",
                "pathParameters": {"contract_type_id": "non-existent"},
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(sample_contract_type_request)
            }

            # Execute
            response = app.resolve(event, {})

            # Verify
            assert response["statusCode"] == 404
            body = json.loads(response["body"])
            assert "not found" in body["message"].lower()

    def test_update_contract_type_invalid_id(self, sample_contract_type_request, contract_types_index):
        """Test update with invalid contract type ID format"""
        app = contract_types_index.app

        # Create test event with invalid ID
        event = {
            "httpMethod": "PUT",
            "path": "/contract-types/invalid@id",
            "pathParameters": {"contract_type_id": "invalid@id"},
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(sample_contract_type_request)
        }

        # Execute
        response = app.resolve(event, {})

        # Verify
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "alphanumeric characters and hyphens" in body["message"]

    def test_update_contract_type_invalid_risk_thresholds(self, sample_contract_type, contract_types_index):
        """Test update with invalid risk thresholds (negative values)"""
        app = contract_types_index.app

        # Setup mock
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo:
            mock_repo.get_contract_type.return_value = sample_contract_type

            # Create request with invalid thresholds (negative value)
            invalid_request = {
                "name": "Updated Contract",
                "description": "Updated description",
                "companyPartyType": "Customer",
                "otherPartyType": "Provider",
                "highRiskThreshold": 0,
                "mediumRiskThreshold": -1,  # Invalid: negative value
                "lowRiskThreshold": 3,
                "isActive": True,
                "defaultLanguage": "en"
            }

            # Create test event
            event = {
                "httpMethod": "PUT",
                "path": "/contract-types/service-agreement",
                "pathParameters": {"contract_type_id": "service-agreement"},
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(invalid_request)
            }

            # Execute
            response = app.resolve(event, {})

            # Verify
            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert "non-negative" in body["message"]

    def test_slugify_name_function(self, contract_types_index):
        """Test the _slugify_name helper function"""
        _slugify_name = contract_types_index._slugify_name

        # Test cases
        assert _slugify_name("Service Agreement") == "service-agreement"
        assert _slugify_name("Employment Contract") == "employment-contract"
        assert _slugify_name("NDA & Confidentiality") == "nda-confidentiality"
        assert _slugify_name("Purchase Order (PO)") == "purchase-order-po"
        assert _slugify_name("  Multiple   Spaces  ") == "multiple-spaces"
        assert _slugify_name("Special@#$Characters") == "specialcharacters"
        assert _slugify_name("Already-Hyphenated") == "already-hyphenated"

    def test_validate_contract_type_id_function(self, contract_types_index):
        """Test the _validate_contract_type_id helper function"""
        _validate_contract_type_id = contract_types_index._validate_contract_type_id

        # Valid IDs should not raise exceptions
        _validate_contract_type_id("service-agreement")
        _validate_contract_type_id("employment123")
        _validate_contract_type_id("nda-confidentiality-2024")

        # Invalid IDs should raise BadRequestError
        with pytest.raises(BadRequestError):
            _validate_contract_type_id("invalid@id")

        with pytest.raises(BadRequestError):
            _validate_contract_type_id("invalid.id")

        with pytest.raises(BadRequestError):
            _validate_contract_type_id("invalid id")

        with pytest.raises(BadRequestError):
            _validate_contract_type_id("invalid_id")

    def test_create_contract_type_missing_required_fields(self, contract_types_index):
        """Test creation with missing required fields"""
        app = contract_types_index.app

        # Create request missing required fields
        incomplete_request = {
            "name": "Test Contract"
            # Missing other required fields
        }

        # Create test event
        event = {
            "httpMethod": "POST",
            "path": "/contract-types",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(incomplete_request)
        }

        # Execute
        response = app.resolve(event, {})

        # Verify validation error
        assert response["statusCode"] == 422  # Validation error

    def test_update_contract_type_missing_required_fields(self, sample_contract_type, contract_types_index):
        """Test update with missing required fields"""
        app = contract_types_index.app

        # Setup mock
        with patch.object(contract_types_index, 'contract_type_repository') as mock_repo:
            mock_repo.get_contract_type.return_value = sample_contract_type

            # Create request missing required fields
            incomplete_request = {
                "name": "Updated Contract"
                # Missing other required fields
            }

            # Create test event
            event = {
                "httpMethod": "PUT",
                "path": "/contract-types/service-agreement",
                "pathParameters": {"contract_type_id": "service-agreement"},
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(incomplete_request)
            }

            # Execute
            response = app.resolve(event, {})

            # Verify validation error
            assert response["statusCode"] == 422  # Validation error