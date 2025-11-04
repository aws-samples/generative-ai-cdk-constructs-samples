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
Integration tests for contract type-specific classification functionality.

These tests verify that the classification Lambda function correctly:
1. Queries guidelines by contract_type_id partition key
2. Uses contract type data from ContractTypesTable for system prompts
3. Handles different contract types with isolated guidelines
"""

import pytest
import boto3
import json
import os
from unittest.mock import patch, MagicMock
from moto import mock_aws
from decimal import Decimal

# Set up environment variables before importing
os.environ.setdefault('GUIDELINES_TABLE_NAME', 'test-guidelines-table')
os.environ.setdefault('CLAUSES_TABLE_NAME', 'test-clauses-table')
os.environ.setdefault('CONTRACT_TYPES_TABLE', 'test-contract-types-table')

# Import the classification function using context manager approach
import sys
import importlib.util
from contextlib import contextmanager

@contextmanager
def classification_module_context():
    """Context manager to safely import classification modules without path conflicts."""
    classification_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/contract_analysis/classification_fn')
    common_layer_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/common_layer')
    langchain_layer_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/langchain_deps_layer')

    # Store original sys.path
    original_path = sys.path.copy()
    modules_to_cleanup = []

    try:
        # Clear conflicting paths and add classification paths
        sys.path = [p for p in sys.path if 'evaluation' not in p and 'validation' not in p]
        sys.path.insert(0, classification_path)
        sys.path.insert(0, common_layer_path)
        sys.path.insert(0, langchain_layer_path)

        # Import modules dynamically
        index_spec = importlib.util.spec_from_file_location("classification_index", os.path.join(classification_path, "index.py"))
        index_module = importlib.util.module_from_spec(index_spec)
        index_spec.loader.exec_module(index_module)
        modules_to_cleanup.append("classification_index")

        app_props_spec = importlib.util.spec_from_file_location("classification_app_properties", os.path.join(common_layer_path, "app_properties_manager.py"))
        app_props_module = importlib.util.module_from_spec(app_props_spec)
        app_props_spec.loader.exec_module(app_props_module)
        modules_to_cleanup.append("classification_app_properties")

        yield index_module, app_props_module

    finally:
        # Clean up imported modules to avoid conflicts
        for module_name in modules_to_cleanup:
            sys.modules.pop(module_name, None)
        # Also clean up any 'index' modules that might conflict
        sys.modules.pop('index', None)
        # Restore original sys.path
        sys.path = original_path

@pytest.fixture
def classification_modules():
    """Fixture to provide classification modules"""
    with classification_module_context() as (index_module, app_props_module):
        yield index_module, app_props_module





@pytest.fixture
def mock_dynamodb_tables(dynamodb_resource):
    """Use session-scoped DynamoDB tables and clear them for testing."""
    # Get the existing tables
    guidelines_table = dynamodb_resource.Table('test-guidelines-table')
    clauses_table = dynamodb_resource.Table('test-clauses-table')
    contract_types_table = dynamodb_resource.Table('test-contract-types-table')

    # Clear all tables
    for table in [guidelines_table, clauses_table, contract_types_table]:
        scan_result = table.scan()
        with table.batch_writer() as batch:
            for item in scan_result.get('Items', []):
                # Get the key schema for this table
                key_names = [key['AttributeName'] for key in table.key_schema]
                key = {name: item[name] for name in key_names}
                batch.delete_item(Key=key)

    yield {
        'guidelines': guidelines_table,
        'clauses': clauses_table,
        'contract_types': contract_types_table
    }


@pytest.fixture
def sample_contract_types():
    """Sample contract type data for testing."""
    return {
        'service-agreement': {
            'contract_type_id': 'service-agreement',
            'name': 'Service Agreement',
            'description': 'Professional services contract',
            'company_party_type': 'Customer',
            'other_party_type': 'Service Provider',
            'high_risk_threshold': 0,
            'medium_risk_threshold': 1,
            'low_risk_threshold': 3,
            'is_active': True,
            'default_language': 'en',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z'
        },
        'employment-contract': {
            'contract_type_id': 'employment-contract',
            'name': 'Employment Contract',
            'description': 'Employee agreement',
            'company_party_type': 'Employer',
            'other_party_type': 'Employee',
            'high_risk_threshold': 0,
            'medium_risk_threshold': 2,
            'low_risk_threshold': 4,
            'is_active': True,
            'default_language': 'en',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z'
        }
    }


@pytest.fixture
def sample_guidelines():
    """Sample guidelines data for different contract types."""
    return {
        'service-agreement': [
            {
                'contract_type_id': 'service-agreement',
                'clause_type_id': 'payment-terms',
                'name': 'Payment Terms',
                'standard_wording': 'Payment shall be made within 30 days',
                'level': 'high',
                'evaluation_questions': ['Are payment terms clearly defined?'],
                'examples': ['Payment is due within 30 days of invoice date']
            },
            {
                'contract_type_id': 'service-agreement',
                'clause_type_id': 'liability',
                'name': 'Liability Limitation',
                'standard_wording': 'Liability is limited to contract value',
                'level': 'critical',
                'evaluation_questions': ['Is liability properly limited?'],
                'examples': ['Total liability shall not exceed the contract value']
            }
        ],
        'employment-contract': [
            {
                'contract_type_id': 'employment-contract',
                'clause_type_id': 'termination',
                'name': 'Termination Clause',
                'standard_wording': 'Employment may be terminated with notice',
                'level': 'high',
                'evaluation_questions': ['Are termination conditions clear?'],
                'examples': ['Either party may terminate with 30 days notice']
            },
            {
                'contract_type_id': 'employment-contract',
                'clause_type_id': 'confidentiality',
                'name': 'Confidentiality Agreement',
                'standard_wording': 'Employee must maintain confidentiality',
                'level': 'critical',
                'evaluation_questions': ['Are confidentiality obligations defined?'],
                'examples': ['Employee agrees to maintain strict confidentiality']
            }
        ]
    }


def populate_test_data(tables, contract_types, guidelines):
    """Populate test tables with sample data."""
    # Populate contract types
    for contract_type in contract_types.values():
        tables['contract_types'].put_item(Item=contract_type)

    # Populate guidelines
    for contract_guidelines in guidelines.values():
        for guideline in contract_guidelines:
            tables['guidelines'].put_item(Item=guideline)


class TestContractTypeClassification:
    """Test contract type-specific classification functionality."""

    @patch.dict(os.environ, {
        'GUIDELINES_TABLE_NAME': 'test-guidelines-table',
        'CLAUSES_TABLE_NAME': 'test-clauses-table',
        'CONTRACT_TYPES_TABLE': 'test-contract-types-table'
    })
    def test_get_guidelines_clauses_by_contract_type(self, classification_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines):
        """Test that get_guidelines_clauses queries by contract_type_id partition key."""
        index_module, app_props_module = classification_modules
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines)

        # Mock the guidelines_table to use our test table
        with patch.object(index_module, 'guidelines_table', mock_dynamodb_tables['guidelines']):
            # Test service agreement guidelines
            service_clauses = index_module.get_guidelines_clauses('service-agreement')
            assert len(service_clauses) == 2
            assert all(clause['contract_type_id'] == 'service-agreement' for clause in service_clauses)

            clause_names = [clause['name'] for clause in service_clauses]
            assert 'Payment Terms' in clause_names
            assert 'Liability Limitation' in clause_names

            # Test employment contract guidelines
            employment_clauses = index_module.get_guidelines_clauses('employment-contract')
            assert len(employment_clauses) == 2
            assert all(clause['contract_type_id'] == 'employment-contract' for clause in employment_clauses)

            clause_names = [clause['name'] for clause in employment_clauses]
            assert 'Termination Clause' in clause_names
            assert 'Confidentiality Agreement' in clause_names

    @patch.dict(os.environ, {
        'GUIDELINES_TABLE_NAME': 'test-guidelines-table',
        'CLAUSES_TABLE_NAME': 'test-clauses-table',
        'CONTRACT_TYPES_TABLE': 'test-contract-types-table'
    })
    def test_get_guidelines_clauses_nonexistent_contract_type(self, classification_modules, mock_dynamodb_tables):
        """Test that get_guidelines_clauses raises error for nonexistent contract type."""
        index_module, app_props_module = classification_modules
        with patch.object(index_module, 'guidelines_table', mock_dynamodb_tables['guidelines']):
            with pytest.raises(RuntimeError, match="No clause types found for contract type nonexistent-type"):
                index_module.get_guidelines_clauses('nonexistent-type')

    @patch.dict(os.environ, {
        'CONTRACT_TYPES_TABLE': 'test-contract-types-table'
    })
    def test_build_system_prompt_with_contract_type_data(self, classification_modules, mock_dynamodb_tables, sample_contract_types):
        """Test that system prompt uses contract type data from ContractTypesTable."""
        index_module, app_props_module = classification_modules
        populate_test_data(mock_dynamodb_tables, sample_contract_types, {})

        # Mock Parameter Store responses
        with patch.object(app_props_module, 'get_parameter', return_value='Test Company'):
            properties = app_props_module.AppPropertiesManager()

            # Test service agreement prompt
            system_prompt = index_module._build_system_prompt(
                possible_types_str="- Payment Terms\n- Liability Limitation",
                examples_str="<example>test</example>",
                properties=properties,
                contract_type_id='service-agreement',
                output_language='en'
            )

            assert 'Professional services contract' in system_prompt
            assert 'Customer' in system_prompt
            assert 'Service Provider' in system_prompt
            assert 'Test Company' in system_prompt

            # Test employment contract prompt
            system_prompt = index_module._build_system_prompt(
                possible_types_str="- Termination Clause\n- Confidentiality Agreement",
                examples_str="<example>test</example>",
                properties=properties,
                contract_type_id='employment-contract',
                output_language='en'
            )

            assert 'Employee agreement' in system_prompt
            assert 'Employer' in system_prompt
            assert 'Employee' in system_prompt

    @patch.dict(os.environ, {
        'GUIDELINES_TABLE_NAME': 'test-guidelines-table',
        'CLAUSES_TABLE_NAME': 'test-clauses-table',
        'CONTRACT_TYPES_TABLE': 'test-contract-types-table'
    })
    def test_classify_clause_with_contract_type(self, classification_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines):
        """Test that classify_clause uses contract type-specific guidelines."""
        index_module, app_props_module = classification_modules
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines)

        # Mock Parameter Store and LLM responses
        with patch.object(app_props_module, 'get_parameter', return_value='us.amazon.nova-pro-v1:0'), \
             patch.object(index_module, 'invoke_llm', return_value=(
                '<clause_replica>Payment is due within 30 days</clause_replica><type reason="Clear payment terms">Payment Terms</type>',
                {'input_tokens': 100, 'output_tokens': 50},
                'stop'
             )):

            # Mock the guidelines_table to use our test table
            with patch.object(index_module, 'guidelines_table', mock_dynamodb_tables['guidelines']):
                # Test classification with service agreement
                ddb_values, yes_answers = index_module.classify_clause(
                    clause="Payment is due within 30 days of invoice date",
                    contract_type_id='service-agreement',
                    request_id='test-request-123',
                    output_language='en'
                )

            assert len(ddb_values) == 1
            assert ddb_values[0]['type_id'] == 'payment-terms'
            assert ddb_values[0]['type_name'] == 'Payment Terms'
            assert 'Clear payment terms' in ddb_values[0]['classification_analysis']

            assert len(yes_answers) == 1
            assert yes_answers[0]['type_id'] == 'payment-terms'
            assert yes_answers[0]['type_name'] == 'Payment Terms'

    @patch.dict(os.environ, {
        'GUIDELINES_TABLE_NAME': 'test-guidelines-table',
        'CLAUSES_TABLE_NAME': 'test-clauses-table',
        'CONTRACT_TYPES_TABLE': 'test-contract-types-table'
    })
    def test_handler_extracts_contract_type_from_event(self, classification_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines):
        """Test that handler extracts contract_type_id from Step Functions input."""
        index_module, app_props_module = classification_modules
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines)

        # Add test clause to clauses table
        mock_dynamodb_tables['clauses'].put_item(Item={
            'job_id': 'test-job-123',
            'clause_number': 1,
            'text': 'Payment is due within 30 days of invoice date'
        })

        # Test event with ContractTypeId
        event = {
            'JobId': 'test-job-123',
            'ClauseNumber': 1,
            'ContractTypeId': 'service-agreement',
            'OutputLanguage': 'en'
        }

        context = MagicMock()
        context.aws_request_id = 'test-request-123'

        # Mock both tables
        with patch.object(index_module, 'clauses_table', mock_dynamodb_tables['clauses']):
            with patch.object(index_module, 'classify_clause') as mock_classify:
                mock_classify.return_value = ([], [])

                result = index_module.handler(event, context)

                # Verify classify_clause was called with correct contract_type_id
                mock_classify.assert_called_once_with(
                    'Payment is due within 30 days of invoice date',
                    'service-agreement',
                    'test-request-123',
                    'en'
                )

                assert result == 'OK'

    @patch.dict(os.environ, {
        'GUIDELINES_TABLE_NAME': 'test-guidelines-table',
        'CLAUSES_TABLE_NAME': 'test-clauses-table',
        'CONTRACT_TYPES_TABLE': 'test-contract-types-table'
    })
    def test_handler_missing_contract_type_id(self, classification_modules, mock_dynamodb_tables):
        """Test that handler raises error when ContractTypeId is missing."""
        index_module, app_props_module = classification_modules
        # Test event without ContractTypeId
        event = {
            'JobId': 'test-job-123',
            'ClauseNumber': 1,
            'OutputLanguage': 'en'
        }

        context = MagicMock()
        context.aws_request_id = 'test-request-123'

        with pytest.raises(ValueError, match="ContractTypeId is required"):
            index_module.handler(event, context)

    @patch.dict(os.environ, {
        'GUIDELINES_TABLE_NAME': 'test-guidelines-table',
        'CLAUSES_TABLE_NAME': 'test-clauses-table',
        'CONTRACT_TYPES_TABLE': 'test-contract-types-table'
    })
    def test_guidelines_isolation_between_contract_types(self, classification_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines):
        """Test that guidelines are properly isolated between contract types."""
        index_module, app_props_module = classification_modules
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines)

        # Mock the guidelines_table to use our test table
        with patch.object(index_module, 'guidelines_table', mock_dynamodb_tables['guidelines']):
            # Get guidelines for service agreement
            service_clauses = index_module.get_guidelines_clauses('service-agreement')
            service_clause_ids = [clause['clause_type_id'] for clause in service_clauses]

            # Get guidelines for employment contract
            employment_clauses = index_module.get_guidelines_clauses('employment-contract')
            employment_clause_ids = [clause['clause_type_id'] for clause in employment_clauses]

            # Verify no overlap between contract types
            assert set(service_clause_ids).isdisjoint(set(employment_clause_ids))

            # Verify each contract type has its expected guidelines
            assert 'payment-terms' in service_clause_ids
            assert 'liability' in service_clause_ids
            assert 'termination' in employment_clause_ids
            assert 'confidentiality' in employment_clause_ids

            # Verify cross-contamination doesn't occur
            assert 'termination' not in service_clause_ids
            assert 'confidentiality' not in service_clause_ids
            assert 'payment-terms' not in employment_clause_ids
            assert 'liability' not in employment_clause_ids


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
