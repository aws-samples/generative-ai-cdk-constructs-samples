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
Integration tests for contract type-specific evaluation functionality.

These tests verify that the evaluation Lambda function correctly:
1. Uses composite key (contract_type_id, clause_type_id) to query guidelines
2. Uses contract type data from ContractTypesTable for evaluation prompts
3. Handles different contract types with isolated guidelines
4. Extracts contract_type_id from Step Functions input
"""

import pytest
import boto3
import json
import os
from unittest.mock import patch, MagicMock, Mock
from moto import mock_aws
from decimal import Decimal

# Set environment variables before importing
os.environ.setdefault('CLAUSES_TABLE_NAME', 'test-clauses-table')
os.environ.setdefault('GUIDELINES_TABLE_NAME', 'test-guidelines-table')
os.environ.setdefault('CONTRACT_TYPES_TABLE', 'test-contract-types-table')

# Import the evaluation function using a context manager approach
import sys
import os
import importlib.util
from contextlib import contextmanager

@contextmanager
def evaluation_module_context():
    """Context manager to safely import evaluation modules without path conflicts."""
    evaluation_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/contract_analysis/evaluation_fn')
    common_layer_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/common_layer')
    langchain_layer_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/langchain_deps_layer')

    # Store original sys.path and modules
    original_path = sys.path.copy()
    modules_to_cleanup = []

    try:
        # Clear conflicting paths and add evaluation paths
        sys.path = [p for p in sys.path if 'classification' not in p and 'fn-classify-clauses' not in p]
        sys.path.insert(0, evaluation_path)
        sys.path.insert(0, common_layer_path)
        sys.path.insert(0, langchain_layer_path)

        # Import modules dynamically
        index_spec = importlib.util.spec_from_file_location("evaluation_index", os.path.join(evaluation_path, "index.py"))
        index_module = importlib.util.module_from_spec(index_spec)
        index_spec.loader.exec_module(index_module)
        modules_to_cleanup.append("evaluation_index")

        app_props_spec = importlib.util.spec_from_file_location("evaluation_app_properties", os.path.join(common_layer_path, "app_properties_manager.py"))
        app_props_module = importlib.util.module_from_spec(app_props_spec)
        app_props_spec.loader.exec_module(app_props_module)
        modules_to_cleanup.append("evaluation_app_properties")

        yield index_module, app_props_module

    finally:
        # Clean up imported modules to avoid conflicts
        for module_name in modules_to_cleanup:
            sys.modules.pop(module_name, None)
        # Also clean up any 'index' modules that might conflict
        sys.modules.pop('index', None)
        # Restore original sys.path
        sys.path = original_path

# Global variables to hold the imported modules
evaluation_index = None
evaluation_app_properties = None


@pytest.fixture
def evaluation_modules():
    """Fixture to import evaluation modules safely."""
    with evaluation_module_context() as (index_module, app_props_module):
        yield {
            'get_guidelines_rule': index_module.get_guidelines_rule,
            'run_evaluation': index_module.run_evaluation,
            'handler': index_module.handler,
            'AppPropertiesManager': app_props_module.AppPropertiesManager,
            'index_module': index_module,  # Store reference to the module itself
            'app_props_module': app_props_module
        }

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
                'evaluation_questions': [
                    'Are payment terms clearly defined?',
                    'Is the payment schedule reasonable?'
                ],
                'examples': ['Payment is due within 30 days of invoice date']
            },
            {
                'contract_type_id': 'service-agreement',
                'clause_type_id': 'liability',
                'name': 'Liability Limitation',
                'standard_wording': 'Liability is limited to contract value',
                'level': 'critical',
                'evaluation_questions': [
                    'Is liability properly limited?',
                    'Are exclusions clearly stated?'
                ],
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
                'evaluation_questions': [
                    'Are termination conditions clear?',
                    'Is notice period specified?'
                ],
                'examples': ['Either party may terminate with 30 days notice']
            },
            {
                'contract_type_id': 'employment-contract',
                'clause_type_id': 'confidentiality',
                'name': 'Confidentiality Agreement',
                'standard_wording': 'Employee must maintain confidentiality',
                'level': 'critical',
                'evaluation_questions': [
                    'Are confidentiality obligations defined?',
                    'Is the scope of confidentiality clear?'
                ],
                'examples': ['Employee agrees to maintain strict confidentiality']
            }
        ]
    }


@pytest.fixture
def sample_clauses():
    """Sample clause data for testing."""
    return [
        {
            'job_id': 'test-job-123',
            'clause_number': 1,
            'text': 'Payment is due within 30 days of invoice date',
            'types': [
                {
                    'type_id': 'payment-terms',
                    'type_name': 'Payment Terms',
                    'classification_analysis': 'Clear payment terms specified'
                }
            ]
        },
        {
            'job_id': 'test-job-456',
            'clause_number': 1,
            'text': 'Either party may terminate this agreement with 30 days written notice',
            'types': [
                {
                    'type_id': 'termination',
                    'type_name': 'Termination Clause',
                    'classification_analysis': 'Standard termination clause'
                }
            ]
        }
    ]


def populate_test_data(tables, contract_types, guidelines, clauses=None):
    """Populate test tables with sample data."""
    # Populate contract types
    for contract_type in contract_types.values():
        tables['contract_types'].put_item(Item=contract_type)

    # Populate guidelines
    for contract_guidelines in guidelines.values():
        for guideline in contract_guidelines:
            tables['guidelines'].put_item(Item=guideline)

    # Populate clauses if provided
    if clauses:
        for clause in clauses:
            tables['clauses'].put_item(Item=clause)


class TestContractTypeEvaluation:
    """Test contract type-specific evaluation functionality."""

    def test_get_guidelines_rule_with_composite_key(self, evaluation_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines):
        """Test that get_guidelines_rule uses composite key (contract_type_id, clause_type_id)."""
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines)

        get_guidelines_rule = evaluation_modules['get_guidelines_rule']

        # Mock the guidelines_table to use our test table
        with patch.object(evaluation_modules['index_module'], 'guidelines_table', mock_dynamodb_tables['guidelines']):
            # Test service agreement payment terms rule
            rule = get_guidelines_rule('service-agreement', 'payment-terms')
            assert rule['contract_type_id'] == 'service-agreement'
            assert rule['clause_type_id'] == 'payment-terms'
            assert rule['name'] == 'Payment Terms'
            assert len(rule['evaluation_questions']) == 2
            assert 'Are payment terms clearly defined?' in rule['evaluation_questions']

            # Test employment contract termination rule
            rule = get_guidelines_rule('employment-contract', 'termination')
            assert rule['contract_type_id'] == 'employment-contract'
            assert rule['clause_type_id'] == 'termination'
            assert rule['name'] == 'Termination Clause'
            assert len(rule['evaluation_questions']) == 2
            assert 'Are termination conditions clear?' in rule['evaluation_questions']

    def test_get_guidelines_rule_not_found(self, evaluation_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines):
        """Test that get_guidelines_rule raises error for nonexistent rule."""
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines)

        get_guidelines_rule = evaluation_modules['get_guidelines_rule']

        # Mock the guidelines_table to use our test table
        with patch.object(evaluation_modules['index_module'], 'guidelines_table', mock_dynamodb_tables['guidelines']):
            # Test nonexistent clause type
            with pytest.raises(ValueError, match="Clause type nonexistent not found for contract type service-agreement"):
                get_guidelines_rule('service-agreement', 'nonexistent')

            # Test nonexistent contract type
            with pytest.raises(ValueError, match="Clause type payment-terms not found for contract type nonexistent"):
                get_guidelines_rule('nonexistent', 'payment-terms')

    def test_run_evaluation_with_contract_type_data(self, evaluation_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines):
        """Test that run_evaluation uses contract type data from ContractTypesTable."""
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines)

        run_evaluation = evaluation_modules['run_evaluation']
        AppPropertiesManager = evaluation_modules['AppPropertiesManager']

        # Mock Parameter Store and LLM responses
        with patch.object(evaluation_modules['app_props_module'], 'get_parameter') as mock_get_parameter:
            mock_get_parameter.return_value = 'Test Company'

            with patch.object(evaluation_modules['index_module'], 'invoke_llm') as mock_invoke_llm:
                mock_invoke_llm.return_value = (
                    '<answering><question_replica>Are payment terms clearly defined?</question_replica><reasoning_translated>Yes, payment terms are clear</reasoning_translated><answer_english>Yes</answer_english><answer_translated>Sí</answer_translated></answering>',
                    {'input_tokens': 200, 'output_tokens': 100},
                    'stop'
                )

                # Mock the DynamoDBContractTypeRepository to use our test table
                with patch.object(evaluation_modules['index_module'], 'DynamoDBContractTypeRepository') as mock_repo_class:
                    mock_repo = Mock()
                    mock_repo.get_contract_type.return_value = Mock(
                        description='Professional services contract',
                        name='Service Agreement',
                        company_party_type='Customer',
                        other_party_type='Service Provider',
                        is_active=True
                    )
                    mock_repo_class.return_value = mock_repo
                    
                    properties = AppPropertiesManager()

                    # Test clause and rule data
                    clause = {
                        'text': 'Payment is due within 30 days of invoice date'
                    }
                    rule = {
                        'evaluation_questions': ['Are payment terms clearly defined?']
                    }
                    clause_context = 'This is a service agreement between parties.'

                    # Test evaluation with service agreement
                    result = run_evaluation(
                        clause=clause,
                        clause_context=clause_context,
                        rule=rule,
                        properties=properties,
                        contract_type_id='service-agreement',
                        output_language='es'
                    )

                    assert result['compliant'] is True
                    assert 'Yes, payment terms are clear' in result['analysis']

                    # Verify the LLM was called with correct prompt containing contract type data
                    mock_invoke_llm.assert_called_once()
                    prompt_args = mock_invoke_llm.call_args[1]
                    prompt = prompt_args['prompt']

                    # Verify contract type-specific data is in the prompt
                assert 'Professional services contract' in prompt
                assert 'Customer' in prompt
                assert 'Service Provider' in prompt
                assert 'Test Company' in prompt
                assert 'Payment is due within 30 days of invoice date' in prompt
                assert 'Are payment terms clearly defined?' in prompt

    def test_run_evaluation_employment_contract(self, evaluation_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines):
        """Test evaluation with employment contract type data."""
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines)

        run_evaluation = evaluation_modules['run_evaluation']
        AppPropertiesManager = evaluation_modules['AppPropertiesManager']

        # Mock Parameter Store and LLM responses
        with patch.object(evaluation_modules['app_props_module'], 'get_parameter') as mock_get_parameter:
            mock_get_parameter.return_value = 'Test Company'

            with patch.object(evaluation_modules['index_module'], 'invoke_llm') as mock_invoke_llm:
                mock_invoke_llm.return_value = (
                    '<answering><question_replica>Are termination conditions clear?</question_replica><reasoning_translated>Yes, conditions are clear</reasoning_translated><answer_english>Yes</answer_english><answer_translated>Yes</answer_translated></answering>',
                    {'input_tokens': 200, 'output_tokens': 100},
                    'stop'
                )

                # Mock the DynamoDBContractTypeRepository to use our test table
                with patch.object(evaluation_modules['index_module'], 'DynamoDBContractTypeRepository') as mock_repo_class:
                    mock_repo = Mock()
                    mock_repo.get_contract_type.return_value = Mock(
                        description='Employee agreement',
                        name='Employment Contract',
                        company_party_type='Employer',
                        other_party_type='Employee',
                        is_active=True
                    )
                    mock_repo_class.return_value = mock_repo
                    
                    properties = AppPropertiesManager()

                    # Test clause and rule data
                    clause = {
                        'text': 'Either party may terminate with 30 days notice'
                    }
                    rule = {
                        'evaluation_questions': ['Are termination conditions clear?']
                    }
                    clause_context = 'This is an employment agreement.'

                # Test evaluation with employment contract
                result = run_evaluation(
                    clause=clause,
                    clause_context=clause_context,
                    rule=rule,
                    properties=properties,
                    contract_type_id='employment-contract',
                    output_language='en'
                )

                assert result['compliant'] is True

                # Verify the LLM was called with employment contract data
                mock_invoke_llm.assert_called_once()
                prompt_args = mock_invoke_llm.call_args[1]
                prompt = prompt_args['prompt']

                # Verify employment contract-specific data is in the prompt
                assert 'Employee agreement' in prompt
                assert 'Employer' in prompt
                assert 'Employee' in prompt
                assert 'Test Company' in prompt

    def test_handler_extracts_contract_type_from_event(self, evaluation_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines, sample_clauses):
        """Test that handler extracts contract_type_id from Step Functions input."""
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines, sample_clauses)

        handler = evaluation_modules['handler']

        # Mock the tables and evaluation function
        with patch.object(evaluation_modules['index_module'], 'clauses_table', mock_dynamodb_tables['clauses']):
            with patch.object(evaluation_modules['index_module'], 'guidelines_table', mock_dynamodb_tables['guidelines']):
                with patch.object(evaluation_modules['index_module'], 'run_evaluation') as mock_run_evaluation:
                    # Mock evaluation result
                    mock_run_evaluation.return_value = {
                        'compliant': True,
                        'analysis': 'Test analysis'
                    }

                    # Test event with ContractTypeId
                    event = {
                        'JobId': 'test-job-123',
                        'ClauseNumber': 1,
                        'ContractTypeId': 'service-agreement',
                        'OutputLanguage': 'en'
                    }

                    context = MagicMock()
                    context.aws_request_id = 'test-request-123'

                    result = handler(event, context)

                    # Verify run_evaluation was called with correct contract_type_id
                    mock_run_evaluation.assert_called_once()
                    call_args = mock_run_evaluation.call_args[0]  # positional arguments
                    # Arguments: clause, clause_context, rule, properties, contract_type_id, output_language
                    assert call_args[4] == 'service-agreement'  # contract_type_id is 5th argument (index 4)
                    assert call_args[5] == 'en'  # output_language is 6th argument (index 5)

                    assert result == {'Status': 'OK'}

    def test_handler_missing_contract_type_id(self, evaluation_modules, mock_dynamodb_tables):
        """Test that handler raises error when ContractTypeId is missing."""
        # Add a test clause
        test_clause = {
            'job_id': 'test-job-123',
            'clause_number': 1,
            'text': 'Test clause text',
            'types': [{'type_id': 'test-type', 'type_name': 'Test Type'}]
        }
        mock_dynamodb_tables['clauses'].put_item(Item=test_clause)

        handler = evaluation_modules['handler']

        # Mock the clauses_table
        with patch.object(evaluation_modules['index_module'], 'clauses_table', mock_dynamodb_tables['clauses']):
            # Test event without ContractTypeId
            event = {
                'JobId': 'test-job-123',
                'ClauseNumber': 1,
                'OutputLanguage': 'en'
            }

            context = MagicMock()
            context.aws_request_id = 'test-request-123'

            with pytest.raises(ValueError, match="ContractTypeId is required"):
                handler(event, context)

    def test_handler_processes_multiple_clause_types(self, evaluation_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines):
        """Test that handler processes multiple clause types for a single clause."""
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines)

        handler = evaluation_modules['handler']

        # Add clause with multiple types
        clause_with_multiple_types = {
            'job_id': 'test-job-multi',
            'clause_number': 1,
            'text': 'Payment terms and liability limitations are defined',
            'types': [
                {
                    'type_id': 'payment-terms',
                    'type_name': 'Payment Terms',
                    'classification_analysis': 'Payment terms identified'
                },
                {
                    'type_id': 'liability',
                    'type_name': 'Liability Limitation',
                    'classification_analysis': 'Liability terms identified'
                }
            ]
        }
        mock_dynamodb_tables['clauses'].put_item(Item=clause_with_multiple_types)

        # Mock the tables and evaluation function
        with patch.object(evaluation_modules['index_module'], 'clauses_table', mock_dynamodb_tables['clauses']):
            with patch.object(evaluation_modules['index_module'], 'guidelines_table', mock_dynamodb_tables['guidelines']):
                with patch.object(evaluation_modules['index_module'], 'run_evaluation') as mock_run_evaluation:
                    # Mock evaluation results
                    mock_run_evaluation.side_effect = [
                        {'compliant': True, 'analysis': 'Payment terms analysis'},
                        {'compliant': False, 'analysis': 'Liability analysis'}
                    ]

                    # Test event
                    event = {
                        'JobId': 'test-job-multi',
                        'ClauseNumber': 1,
                        'ContractTypeId': 'service-agreement',
                        'OutputLanguage': 'en'
                    }

                    context = MagicMock()
                    context.aws_request_id = 'test-request-123'

                    result = handler(event, context)

                    # Verify run_evaluation was called twice (once for each clause type)
                    assert mock_run_evaluation.call_count == 2

                    # Verify both calls used the correct contract_type_id (positional argument index 4)
                    for call in mock_run_evaluation.call_args_list:
                        assert call[0][4] == 'service-agreement'  # contract_type_id is 5th argument (index 4)

                    assert result == {'Status': 'OK'}

    def test_guidelines_isolation_between_contract_types(self, evaluation_modules, mock_dynamodb_tables, sample_contract_types, sample_guidelines):
        """Test that guidelines are properly isolated between contract types."""
        populate_test_data(mock_dynamodb_tables, sample_contract_types, sample_guidelines)

        get_guidelines_rule = evaluation_modules['get_guidelines_rule']

        # Mock the guidelines_table to use our test table
        with patch.object(evaluation_modules['index_module'], 'guidelines_table', mock_dynamodb_tables['guidelines']):
            # Test that service agreement guidelines are isolated
            service_payment_rule = get_guidelines_rule('service-agreement', 'payment-terms')
            assert service_payment_rule['contract_type_id'] == 'service-agreement'

            service_liability_rule = get_guidelines_rule('service-agreement', 'liability')
            assert service_liability_rule['contract_type_id'] == 'service-agreement'

            # Test that employment contract guidelines are isolated
            employment_termination_rule = get_guidelines_rule('employment-contract', 'termination')
            assert employment_termination_rule['contract_type_id'] == 'employment-contract'

            employment_confidentiality_rule = get_guidelines_rule('employment-contract', 'confidentiality')
            assert employment_confidentiality_rule['contract_type_id'] == 'employment-contract'

            # Verify cross-contamination doesn't occur
            with pytest.raises(ValueError):
                get_guidelines_rule('service-agreement', 'termination')

            with pytest.raises(ValueError):
                get_guidelines_rule('employment-contract', 'payment-terms')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])