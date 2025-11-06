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

from model import ContractType
from repository.dynamo_db_contract_type_repository import DynamoDBContractTypeRepository


@pytest.fixture
def contract_types_table_name():
    return 'test-contract-types-table'


@pytest.fixture
def contract_types_table(dynamodb_resource, contract_types_table_name):
    """Get the session-scoped contract types table and clear it before each test"""
    table = dynamodb_resource.Table(contract_types_table_name)

    # Clear any existing items before each test
    scan_result = table.scan()
    with table.batch_writer() as batch:
        for item in scan_result.get('Items', []):
            batch.delete_item(Key={'contract_type_id': item['contract_type_id']})

    return table


@pytest.fixture
def sample_contract_type():
    return ContractType(
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
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )


def test_can_create_contract_type(ddb, contract_types_table, contract_types_table_name, sample_contract_type):
    """Test creating a new contract type"""
    # given
    repo = DynamoDBContractTypeRepository(table_name=contract_types_table_name)

    # when
    repo.create_contract_type(sample_contract_type)

    # then
    result = ddb.get_item(
        TableName=contract_types_table_name,
        Key={'contract_type_id': {'S': sample_contract_type.contract_type_id}}
    )

    assert "Item" in result
    retrieved_contract_type = result["Item"]
    assert retrieved_contract_type["contract_type_id"]["S"] == sample_contract_type.contract_type_id
    assert retrieved_contract_type["name"]["S"] == sample_contract_type.name
    assert retrieved_contract_type["description"]["S"] == sample_contract_type.description
    assert retrieved_contract_type["company_party_type"]["S"] == sample_contract_type.company_party_type
    assert retrieved_contract_type["other_party_type"]["S"] == sample_contract_type.other_party_type
    assert int(retrieved_contract_type["high_risk_threshold"]["N"]) == sample_contract_type.high_risk_threshold
    assert int(retrieved_contract_type["medium_risk_threshold"]["N"]) == sample_contract_type.medium_risk_threshold
    assert int(retrieved_contract_type["low_risk_threshold"]["N"]) == sample_contract_type.low_risk_threshold
    assert retrieved_contract_type["is_active"]["BOOL"] == sample_contract_type.is_active
    assert retrieved_contract_type["default_language"]["S"] == sample_contract_type.default_language


def test_create_contract_type_fails_if_already_exists(ddb, contract_types_table, contract_types_table_name, sample_contract_type):
    """Test that creating a contract type with existing ID fails"""
    # given
    repo = DynamoDBContractTypeRepository(table_name=contract_types_table_name)
    repo.create_contract_type(sample_contract_type)

    # when/then
    with pytest.raises(ValueError, match="Contract type with ID 'service-agreement' already exists"):
        repo.create_contract_type(sample_contract_type)


def test_can_get_contract_type(ddb, contract_types_table, contract_types_table_name, sample_contract_type):
    """Test retrieving a specific contract type"""
    # given
    repo = DynamoDBContractTypeRepository(table_name=contract_types_table_name)
    repo.create_contract_type(sample_contract_type)

    # when
    retrieved_contract_type = repo.get_contract_type(sample_contract_type.contract_type_id)

    # then
    assert retrieved_contract_type is not None
    assert retrieved_contract_type.contract_type_id == sample_contract_type.contract_type_id
    assert retrieved_contract_type.name == sample_contract_type.name
    assert retrieved_contract_type.description == sample_contract_type.description
    assert retrieved_contract_type.company_party_type == sample_contract_type.company_party_type
    assert retrieved_contract_type.other_party_type == sample_contract_type.other_party_type
    assert retrieved_contract_type.high_risk_threshold == sample_contract_type.high_risk_threshold
    assert retrieved_contract_type.medium_risk_threshold == sample_contract_type.medium_risk_threshold
    assert retrieved_contract_type.low_risk_threshold == sample_contract_type.low_risk_threshold
    assert retrieved_contract_type.is_active == sample_contract_type.is_active
    assert retrieved_contract_type.default_language == sample_contract_type.default_language


def test_get_contract_type_returns_none_if_not_found(contract_types_table, contract_types_table_name):
    """Test that getting a non-existent contract type returns None"""
    # given
    repo = DynamoDBContractTypeRepository(table_name=contract_types_table_name)

    # when
    result = repo.get_contract_type("non-existent-id")

    # then
    assert result is None


def test_can_get_all_contract_types(ddb, contract_types_table, contract_types_table_name):
    """Test retrieving all contract types"""
    # given
    repo = DynamoDBContractTypeRepository(table_name=contract_types_table_name)

    contract_type_1 = ContractType(
        contract_type_id="service-agreement",
        name="Service Agreement",
        description="Standard service agreement",
        company_party_type="Customer",
        other_party_type="Service Provider",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )

    contract_type_2 = ContractType(
        contract_type_id="employment-contract",
        name="Employment Contract",
        description="Standard employment contract",
        company_party_type="Employer",
        other_party_type="Employee",
        created_at="2025-01-01T01:00:00Z",
        updated_at="2025-01-01T01:00:00Z"
    )

    repo.create_contract_type(contract_type_1)
    repo.create_contract_type(contract_type_2)

    # when
    contract_types = repo.get_contract_types()

    # then
    assert len(contract_types) == 2
    contract_type_ids = [ct.contract_type_id for ct in contract_types]
    assert "service-agreement" in contract_type_ids
    assert "employment-contract" in contract_type_ids


def test_can_update_contract_type(ddb, contract_types_table, contract_types_table_name, sample_contract_type):
    """Test updating an existing contract type"""
    # given
    repo = DynamoDBContractTypeRepository(table_name=contract_types_table_name)
    repo.create_contract_type(sample_contract_type)

    # Modify the contract type
    updated_contract_type = ContractType(
        contract_type_id=sample_contract_type.contract_type_id,
        name="Updated Service Agreement",
        description="Updated description",
        company_party_type="Updated Customer",
        other_party_type="Updated Service Provider",
        high_risk_threshold=1,
        medium_risk_threshold=2,
        low_risk_threshold=4,
        is_active=False,
        default_language="pt_BR",
        created_at=sample_contract_type.created_at,
        updated_at="2025-01-01T12:00:00Z"
    )

    # when
    repo.update_contract_type(updated_contract_type)

    # then
    retrieved = repo.get_contract_type(sample_contract_type.contract_type_id)
    assert retrieved is not None
    assert retrieved.name == "Updated Service Agreement"
    assert retrieved.description == "Updated description"
    assert retrieved.company_party_type == "Updated Customer"
    assert retrieved.other_party_type == "Updated Service Provider"
    assert retrieved.high_risk_threshold == 1
    assert retrieved.medium_risk_threshold == 2
    assert retrieved.low_risk_threshold == 4
    assert retrieved.is_active is False
    assert retrieved.default_language == "pt_BR"
    assert retrieved.updated_at == "2025-01-01T12:00:00Z"


def test_update_contract_type_fails_if_not_exists(contract_types_table, contract_types_table_name, sample_contract_type):
    """Test that updating a non-existent contract type fails"""
    # given
    repo = DynamoDBContractTypeRepository(table_name=contract_types_table_name)

    # when/then
    with pytest.raises(ValueError, match="Contract type with ID 'service-agreement' does not exist"):
        repo.update_contract_type(sample_contract_type)


def test_can_delete_contract_type(ddb, contract_types_table, contract_types_table_name, sample_contract_type):
    """Test deleting a contract type"""
    # given
    repo = DynamoDBContractTypeRepository(table_name=contract_types_table_name)
    repo.create_contract_type(sample_contract_type)

    # when
    repo.delete_contract_type(sample_contract_type.contract_type_id)

    # then
    result = repo.get_contract_type(sample_contract_type.contract_type_id)
    assert result is None


def test_delete_contract_type_fails_if_not_exists(contract_types_table, contract_types_table_name):
    """Test that deleting a non-existent contract type fails"""
    # given
    repo = DynamoDBContractTypeRepository(table_name=contract_types_table_name)

    # when/then
    with pytest.raises(ValueError, match="Contract type with ID 'non-existent-id' does not exist"):
        repo.delete_contract_type("non-existent-id")


def test_get_contract_types_returns_empty_list_when_no_data(contract_types_table, contract_types_table_name):
    """Test that getting contract types returns empty list when table is empty"""
    # given
    repo = DynamoDBContractTypeRepository(table_name=contract_types_table_name)

    # when
    contract_types = repo.get_contract_types()

    # then
    assert contract_types == []