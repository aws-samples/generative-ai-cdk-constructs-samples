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


def test_contract_type_model_with_required_fields(contract_types_models):
    """Test ContractType model with only required fields"""
    contract_type = contract_types_models.ContractType(
        contract_type_id="service-agreement",
        name="Service Agreement",
        description="Standard service agreement contract",
        company_party_type="Customer",
        other_party_type="Service Provider",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )

    assert contract_type.contract_type_id == "service-agreement"
    assert contract_type.name == "Service Agreement"
    assert contract_type.description == "Standard service agreement contract"
    assert contract_type.company_party_type == "Customer"
    assert contract_type.other_party_type == "Service Provider"
    assert contract_type.high_risk_threshold == 0  # default value
    assert contract_type.medium_risk_threshold == 1  # default value
    assert contract_type.low_risk_threshold == 3  # default value
    assert contract_type.is_active is True  # default value
    assert contract_type.default_language == "en"  # default value
    assert contract_type.created_at == "2025-01-01T00:00:00Z"
    assert contract_type.updated_at == "2025-01-01T00:00:00Z"


def test_contract_type_model_with_all_fields(contract_types_models):
    """Test ContractType model with all fields specified"""
    contract_type = contract_types_models.ContractType(
        contract_type_id="employment-contract",
        name="Employment Contract",
        description="Standard employment agreement",
        company_party_type="Employer",
        other_party_type="Employee",
        high_risk_threshold=1,
        medium_risk_threshold=2,
        low_risk_threshold=4,
        is_active=False,
        default_language="pt_BR",
        created_at="2025-01-01T10:00:00Z",
        updated_at="2025-01-01T12:00:00Z"
    )

    assert contract_type.contract_type_id == "employment-contract"
    assert contract_type.name == "Employment Contract"
    assert contract_type.description == "Standard employment agreement"
    assert contract_type.company_party_type == "Employer"
    assert contract_type.other_party_type == "Employee"
    assert contract_type.high_risk_threshold == 1
    assert contract_type.medium_risk_threshold == 2
    assert contract_type.low_risk_threshold == 4
    assert contract_type.is_active is False
    assert contract_type.default_language == "pt_BR"
    assert contract_type.created_at == "2025-01-01T10:00:00Z"
    assert contract_type.updated_at == "2025-01-01T12:00:00Z"


def test_contract_type_model_missing_required_fields(contract_types_models):
    """Test that ContractType model raises validation error for missing required fields"""
    # Missing contract_type_id
    with pytest.raises(ValueError, match="Field required"):
        contract_types_models.ContractType(
            name="Service Agreement",
            description="Standard service agreement contract",
            company_party_type="Customer",
            other_party_type="Service Provider",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )

    # Missing name
    with pytest.raises(ValueError, match="Field required"):
        contract_types_models.ContractType(
            contract_type_id="service-agreement",
            description="Standard service agreement contract",
            company_party_type="Customer",
            other_party_type="Service Provider",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )

    # Missing description
    with pytest.raises(ValueError, match="Field required"):
        contract_types_models.ContractType(
            contract_type_id="service-agreement",
            name="Service Agreement",
            company_party_type="Customer",
            other_party_type="Service Provider",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )


def test_contract_type_model_serialization(contract_types_models):
    """Test ContractType model serialization to dict"""
    contract_type = contract_types_models.ContractType(
        contract_type_id="nda-contract",
        name="Non-Disclosure Agreement",
        description="Standard NDA contract",
        company_party_type="Disclosing Party",
        other_party_type="Receiving Party",
        high_risk_threshold=2,
        medium_risk_threshold=3,
        low_risk_threshold=5,
        is_active=True,
        default_language="es",
        created_at="2025-01-01T08:00:00Z",
        updated_at="2025-01-01T09:00:00Z"
    )

    serialized = contract_type.model_dump()

    expected = {
        "contract_type_id": "nda-contract",
        "name": "Non-Disclosure Agreement",
        "description": "Standard NDA contract",
        "company_party_type": "Disclosing Party",
        "other_party_type": "Receiving Party",
        "high_risk_threshold": 2,
        "medium_risk_threshold": 3,
        "low_risk_threshold": 5,
        "is_active": True,
        "default_language": "es",
        "created_at": "2025-01-01T08:00:00Z",
        "updated_at": "2025-01-01T09:00:00Z"
    }

    assert serialized == expected


def test_contract_type_model_deserialization(contract_types_models):
    """Test ContractType model deserialization from dict"""
    data = {
        "contract_type_id": "purchase-order",
        "name": "Purchase Order",
        "description": "Standard purchase order contract",
        "company_party_type": "Buyer",
        "other_party_type": "Seller",
        "high_risk_threshold": 1,
        "medium_risk_threshold": 2,
        "low_risk_threshold": 4,
        "is_active": True,
        "default_language": "en",
        "created_at": "2025-01-01T14:00:00Z",
        "updated_at": "2025-01-01T15:00:00Z"
    }

    contract_type = contract_types_models.ContractType.model_validate(data)

    assert contract_type.contract_type_id == "purchase-order"
    assert contract_type.name == "Purchase Order"
    assert contract_type.description == "Standard purchase order contract"
    assert contract_type.company_party_type == "Buyer"
    assert contract_type.other_party_type == "Seller"
    assert contract_type.high_risk_threshold == 1
    assert contract_type.medium_risk_threshold == 2
    assert contract_type.low_risk_threshold == 4
    assert contract_type.is_active is True
    assert contract_type.default_language == "en"
    assert contract_type.created_at == "2025-01-01T14:00:00Z"
    assert contract_type.updated_at == "2025-01-01T15:00:00Z"


def test_contract_type_model_risk_threshold_validation(contract_types_models):
    """Test that risk thresholds can be set to valid integer values"""
    contract_type = contract_types_models.ContractType(
        contract_type_id="test-contract",
        name="Test Contract",
        description="Test contract for validation",
        company_party_type="Party A",
        other_party_type="Party B",
        high_risk_threshold=0,  # Minimum value
        medium_risk_threshold=5,  # Middle value
        low_risk_threshold=10,  # Higher value
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )

    assert contract_type.high_risk_threshold == 0
    assert contract_type.medium_risk_threshold == 5
    assert contract_type.low_risk_threshold == 10