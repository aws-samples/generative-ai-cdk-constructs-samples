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
Integration tests for JSON-based guidelines loading functionality.

This test suite has been updated to work with the new JSON-only load_guidelines.py script.
The script now supports:
- JSON format only (no Excel support)
- Automatic contract type creation/updating
- Bulk processing of all contract types in a single JSON file
- Enhanced validation and error handling
"""

import pytest
import boto3
import json
import tempfile
import os
from moto import mock_aws
from decimal import Decimal
from datetime import datetime

# Import the classes and functions we want to test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from load_guidelines import (
    GuidelinesJSONImporter,
    GuidelineValidator,
    GuidelinesImportError,
    VALID_LEVELS
)


@pytest.fixture
def mock_aws_services():
    """Set up mock AWS services"""
    with mock_aws():
        yield


@pytest.fixture
def dynamodb_tables(mock_aws_services, dynamodb_resource):
    """Use session-scoped DynamoDB tables and clear them for testing"""
    # Get the existing tables
    guidelines_table = dynamodb_resource.Table('test-guidelines-table')
    contract_types_table = dynamodb_resource.Table('test-contract-types-table')

    # Clear all tables
    for table in [guidelines_table, contract_types_table]:
        scan_result = table.scan()
        with table.batch_writer() as batch:
            for item in scan_result.get('Items', []):
                # Get the key schema for this table
                key_names = [key['AttributeName'] for key in table.key_schema]
                key = {name: item[name] for name in key_names}
                batch.delete_item(Key=key)

    return guidelines_table, contract_types_table


@pytest.fixture
def cloudformation_stack(mock_aws_services):
    """Create mock CloudFormation stack with outputs"""
    import json
    cf_client = boto3.client('cloudformation', region_name='us-east-1')
    stack_name = 'TestBackendStack'

    # Delete stack if it already exists
    try:
        cf_client.delete_stack(StackName=stack_name)
    except:
        pass

    # Create a simple template with outputs
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "DummyResource": {
                "Type": "AWS::CloudFormation::WaitConditionHandle"
            }
        },
        "Outputs": {
            "GuidelinesTableName": {
                "Value": "test-guidelines-table"
            },
            "ContractTypesTableName": {
                "Value": "test-contract-types-table"
            }
        }
    }

    cf_client.create_stack(
        StackName=stack_name,
        TemplateBody=json.dumps(template)
    )

    yield stack_name

    # Cleanup
    try:
        cf_client.delete_stack(StackName=stack_name)
    except:
        pass


@pytest.fixture
def sample_contract_types(dynamodb_tables):
    """Create sample contract types in the database"""
    _, contract_types_table = dynamodb_tables

    # Active contract type
    contract_types_table.put_item(Item={
        'contract_type_id': 'service-agreement',
        'name': 'Service Agreement',
        'description': 'Standard service agreement contract',
        'company_party_type': 'Customer',
        'other_party_type': 'Service Provider',
        'high_risk_threshold': Decimal('0.8'),
        'medium_risk_threshold': Decimal('0.5'),
        'low_risk_threshold': Decimal('0.2'),
        'is_active': True,
        'default_language': 'en',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    })

    # Inactive contract type
    contract_types_table.put_item(Item={
        'contract_type_id': 'employment-contract',
        'name': 'Employment Contract',
        'description': 'Employment agreement contract',
        'company_party_type': 'Employer',
        'other_party_type': 'Employee',
        'high_risk_threshold': Decimal('0.8'),
        'medium_risk_threshold': Decimal('0.5'),
        'low_risk_threshold': Decimal('0.2'),
        'is_active': False,
        'default_language': 'en',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    })


@pytest.fixture
def sample_guidelines_json():
    """Create a sample guidelines JSON file"""
    # Create sample data in the new JSON format
    guidelines_data = {
        "contract_types": {
            "service-agreement": {
                "name": "Service Agreement",
                "description": "Standard service agreement contract",
                "guidelines": [
                    {
                        "clause_type_id": "CLAUSE_001",
                        "name": "Payment Terms",
                        "standard_wording": "Payment shall be made within 30 days",
                        "level": "medium",
                        "evaluation_questions": [
                            "Are payment terms clearly defined?",
                            "Is the payment period reasonable?"
                        ],
                        "examples": [
                            "Payment due within 30 calendar days of invoice",
                            "Net 30 payment terms apply"
                        ]
                    },
                    {
                        "clause_type_id": "CLAUSE_002",
                        "name": "Liability",
                        "standard_wording": "Liability is limited to contract value",
                        "level": "high",
                        "evaluation_questions": [
                            "Is liability appropriately limited?",
                            "Are exclusions clearly stated?"
                        ],
                        "examples": [
                            "Maximum liability shall not exceed the total contract value"
                        ]
                    },
                    {
                        "clause_type_id": "CLAUSE_003",
                        "name": "Termination",
                        "standard_wording": "Either party may terminate with 30 days notice",
                        "level": "low",
                        "evaluation_questions": [
                            "Are termination conditions fair?",
                            "Is notice period adequate?"
                        ],
                        "examples": []
                    }
                ]
            },
            "employment-contract": {
                "name": "Employment Contract",
                "description": "Employment agreement contract",
                "guidelines": [
                    {
                        "clause_type_id": "EMP_001",
                        "name": "Compensation",
                        "standard_wording": "Employee shall receive base salary as specified",
                        "level": "high",
                        "evaluation_questions": [
                            "Is base salary clearly specified?",
                            "Are benefits outlined?"
                        ],
                        "examples": [
                            "Annual salary of $75,000 paid bi-weekly"
                        ]
                    }
                ]
            }
        }
    }

    # Create temporary JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        json.dump(guidelines_data, tmp_file, indent=2)
        tmp_file.flush()
        yield tmp_file.name

    # Cleanup
    os.unlink(tmp_file.name)


class TestGuidelinesJSONImporter:
    """Test suite for JSON-based guidelines loading"""

    def test_get_table_names_success(self, cloudformation_stack):
        """Test successful retrieval of table names from CloudFormation"""
        importer = GuidelinesJSONImporter(region='us-east-1')
        guidelines_table, contract_types_table = importer.get_table_names(cloudformation_stack)

        assert guidelines_table == 'test-guidelines-table'
        assert contract_types_table == 'test-contract-types-table'

    def test_get_table_names_missing_stack(self, mock_aws_services):
        """Test error when CloudFormation stack doesn't exist"""
        importer = GuidelinesJSONImporter(region='us-east-1')
        with pytest.raises(GuidelinesImportError):
            importer.get_table_names('NonExistentStack')

    def test_create_contract_type_new(self, dynamodb_tables):
        """Test creating a new contract type"""
        _, contract_types_table = dynamodb_tables
        importer = GuidelinesJSONImporter(region='us-east-1')

        contract_type_data = {
            "name": "Test Contract",
            "description": "Test contract description"
        }

        result = importer.create_or_update_contract_type(
            'test-contract',
            contract_type_data,
            'test-contract-types-table'
        )

        assert result['contract_type_id'] == 'test-contract'
        assert result['name'] == 'Test Contract'
        assert result['description'] == 'Test contract description'
        assert result['is_active'] is True
        assert 'created_at' in result
        assert 'updated_at' in result

    def test_create_contract_type_update_existing(self, dynamodb_tables, sample_contract_types):
        """Test updating an existing contract type"""
        _, contract_types_table = dynamodb_tables
        importer = GuidelinesJSONImporter(region='us-east-1')

        contract_type_data = {
            "name": "Updated Service Agreement",
            "description": "Updated description"
        }

        result = importer.create_or_update_contract_type(
            'service-agreement',
            contract_type_data,
            'test-contract-types-table'
        )

        assert result['contract_type_id'] == 'service-agreement'
        assert result['name'] == 'Updated Service Agreement'
        assert result['description'] == 'Updated description'
        assert result['is_active'] is True

    def test_load_json_file_success(self, sample_guidelines_json):
        """Test successful JSON file loading"""
        importer = GuidelinesJSONImporter(region='us-east-1')
        data = importer.load_json_file(sample_guidelines_json)

        assert 'contract_types' in data
        assert 'service-agreement' in data['contract_types']
        assert 'employment-contract' in data['contract_types']

    def test_load_json_file_not_found(self):
        """Test error when JSON file doesn't exist"""
        importer = GuidelinesJSONImporter(region='us-east-1')
        with pytest.raises(GuidelinesImportError, match="JSON file not found"):
            importer.load_json_file('nonexistent.json')

    def test_extract_contract_types_success(self, sample_guidelines_json):
        """Test successful contract types extraction"""
        importer = GuidelinesJSONImporter(region='us-east-1')
        data = importer.load_json_file(sample_guidelines_json)
        contract_types = importer.extract_contract_types_from_json(data)

        assert len(contract_types) == 2
        assert 'service-agreement' in contract_types
        assert 'employment-contract' in contract_types
        assert contract_types['service-agreement']['name'] == 'Service Agreement'

    def test_extract_guidelines_from_contract_type(self, sample_guidelines_json):
        """Test guidelines extraction from contract type"""
        importer = GuidelinesJSONImporter(region='us-east-1')
        data = importer.load_json_file(sample_guidelines_json)
        contract_types = importer.extract_contract_types_from_json(data)

        guidelines = importer.extract_guidelines_from_contract_type(
            contract_types['service-agreement'],
            'service-agreement'
        )

        assert len(guidelines) == 3
        assert guidelines[0]['clause_type_id'] == 'CLAUSE_001'
        assert guidelines[0]['name'] == 'Payment Terms'

    def test_validate_guidelines_success(self, sample_guidelines_json):
        """Test successful guidelines validation"""
        importer = GuidelinesJSONImporter(region='us-east-1')
        data = importer.load_json_file(sample_guidelines_json)
        contract_types = importer.extract_contract_types_from_json(data)
        guidelines = importer.extract_guidelines_from_contract_type(
            contract_types['service-agreement'],
            'service-agreement'
        )

        valid_guidelines, errors = importer.validate_guidelines(guidelines)

        assert len(valid_guidelines) == 3
        assert len(errors) == 0

    def test_import_from_json_success(self, dynamodb_tables, cloudformation_stack, sample_guidelines_json):
        """Test successful full import from JSON"""
        guidelines_table, contract_types_table = dynamodb_tables
        importer = GuidelinesJSONImporter(region='us-east-1')

        results = importer.import_from_json(
            sample_guidelines_json,
            cloudformation_stack,
            clear_existing=True
        )

        # Check results
        assert results['contract_types_processed'] == 2
        assert results['total_imported'] == 4  # 3 + 1 guidelines
        assert results['total_errors'] == 0

        # Verify contract types were created
        ct_response = contract_types_table.scan()
        ct_items = ct_response['Items']
        assert len(ct_items) == 2

        ct_ids = [item['contract_type_id'] for item in ct_items]
        assert 'service-agreement' in ct_ids
        assert 'employment-contract' in ct_ids

        # Verify guidelines were loaded
        gl_response = guidelines_table.scan()
        gl_items = gl_response['Items']
        assert len(gl_items) == 4  # 3 + 1 guidelines

        # Check that all items have the correct structure
        for item in gl_items:
            assert 'contract_type_id' in item
            assert 'clause_type_id' in item
            assert 'name' in item
            assert 'standard_wording' in item
            assert 'level' in item
            assert item['level'] in VALID_LEVELS
            assert 'evaluation_questions' in item
            assert isinstance(item['evaluation_questions'], list)

    def test_import_preserves_contract_types_on_reload(self, dynamodb_tables, cloudformation_stack, sample_guidelines_json):
        """Test that reloading preserves contract types but replaces guidelines"""
        guidelines_table, contract_types_table = dynamodb_tables
        importer = GuidelinesJSONImporter(region='us-east-1')

        # First import
        importer.import_from_json(sample_guidelines_json, cloudformation_stack)

        # Verify initial state
        ct_response = contract_types_table.scan()
        gl_response = guidelines_table.scan()
        assert len(ct_response['Items']) == 2
        assert len(gl_response['Items']) == 4

        # Second import (should replace guidelines but preserve contract types)
        results = importer.import_from_json(sample_guidelines_json, cloudformation_stack)

        # Verify final state
        ct_response = contract_types_table.scan()
        gl_response = guidelines_table.scan()
        assert len(ct_response['Items']) == 2  # Contract types preserved
        assert len(gl_response['Items']) == 4  # Guidelines replaced (same count)
        assert results['total_cleared'] == 4  # All guidelines were cleared and replaced


class TestGuidelineValidator:
    """Test suite for guideline validation"""

    def test_validate_guideline_success(self):
        """Test successful guideline validation"""
        valid_guideline = {
            "clause_type_id": "test-clause",
            "name": "Test Clause",
            "standard_wording": "This is a test clause",
            "level": "medium",
            "evaluation_questions": ["Is this a test?", "Does it work?"],
            "examples": ["Example 1", "Example 2"]
        }

        errors = GuidelineValidator.validate_guideline(valid_guideline, 0)
        assert len(errors) == 0

    def test_validate_guideline_missing_required_fields(self):
        """Test validation failure for missing required fields"""
        invalid_guideline = {
            "clause_type_id": "test-clause",
            "name": "Test Clause"
            # Missing standard_wording, level, evaluation_questions
        }

        errors = GuidelineValidator.validate_guideline(invalid_guideline, 0)
        assert len(errors) >= 3  # At least 3 missing fields
        assert any("Missing required field 'standard_wording'" in error for error in errors)
        assert any("Missing required field 'level'" in error for error in errors)
        assert any("Missing required field 'evaluation_questions'" in error for error in errors)

    def test_validate_guideline_invalid_level(self):
        """Test validation failure for invalid level"""
        invalid_guideline = {
            "clause_type_id": "test-clause",
            "name": "Test Clause",
            "standard_wording": "This is a test clause",
            "level": "invalid_level",  # Invalid level
            "evaluation_questions": ["Is this a test?"]
        }

        errors = GuidelineValidator.validate_guideline(invalid_guideline, 0)
        assert len(errors) >= 1
        assert any("level must be one of: low, medium, high" in error for error in errors)

    def test_validate_guideline_invalid_clause_type_id(self):
        """Test validation failure for invalid clause_type_id format"""
        invalid_guideline = {
            "clause_type_id": "invalid@clause#id",  # Invalid characters
            "name": "Test Clause",
            "standard_wording": "This is a test clause",
            "level": "medium",
            "evaluation_questions": ["Is this a test?"]
        }

        errors = GuidelineValidator.validate_guideline(invalid_guideline, 0)
        assert len(errors) >= 1
        assert any("clause_type_id must contain only alphanumeric characters" in error for error in errors)

    def test_validate_guideline_empty_evaluation_questions(self):
        """Test validation failure for empty evaluation questions"""
        invalid_guideline = {
            "clause_type_id": "test-clause",
            "name": "Test Clause",
            "standard_wording": "This is a test clause",
            "level": "medium",
            "evaluation_questions": []  # Empty list
        }

        errors = GuidelineValidator.validate_guideline(invalid_guideline, 0)
        assert len(errors) >= 1
        assert any("evaluation_questions must contain at least one question" in error for error in errors)

    def test_validate_guideline_too_many_examples(self):
        """Test validation failure for too many examples"""
        invalid_guideline = {
            "clause_type_id": "test-clause",
            "name": "Test Clause",
            "standard_wording": "This is a test clause",
            "level": "medium",
            "evaluation_questions": ["Is this a test?"],
            "examples": [f"Example {i}" for i in range(25)]  # Too many examples
        }

        errors = GuidelineValidator.validate_guideline(invalid_guideline, 0)
        assert len(errors) >= 1
        assert any("examples must contain no more than 20 items" in error for error in errors)


class TestJSONFormatValidation:
    """Test suite for JSON format validation"""

    def test_invalid_json_format(self):
        """Test error for invalid JSON format"""
        invalid_data = {"invalid": "format"}  # Missing contract_types

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(invalid_data, tmp_file)
            tmp_file.flush()

            try:
                importer = GuidelinesJSONImporter(region='us-east-1')
                data = importer.load_json_file(tmp_file.name)

                with pytest.raises(GuidelinesImportError, match="Invalid JSON format"):
                    importer.extract_contract_types_from_json(data)
            finally:
                os.unlink(tmp_file.name)

    def test_malformed_json_file(self):
        """Test error for malformed JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_file.write('{"invalid": json}')  # Malformed JSON
            tmp_file.flush()

            try:
                importer = GuidelinesJSONImporter(region='us-east-1')
                with pytest.raises(GuidelinesImportError, match="Invalid JSON format"):
                    importer.load_json_file(tmp_file.name)
            finally:
                os.unlink(tmp_file.name)