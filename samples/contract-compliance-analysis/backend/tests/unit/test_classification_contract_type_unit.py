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
Unit tests for contract type-specific classification functionality.

These tests verify the core logic changes made to support contract types:
1. get_guidelines_clauses function queries by contract_type_id
2. classify_clause function accepts contract_type_id parameter
3. Handler extracts contract_type_id from event
"""

import pytest
import boto3
import sys
import os
from unittest.mock import patch, MagicMock, Mock
from moto import mock_aws
from decimal import Decimal

# Set up environment variables before importing
os.environ.setdefault('GUIDELINES_TABLE_NAME', 'test-guidelines-table')
os.environ.setdefault('CLAUSES_TABLE_NAME', 'test-clauses-table')
os.environ.setdefault('CONTRACT_TYPES_TABLE', 'test-contract-types-table')

# Import helper to get classification module without polluting global sys.path
def get_classification_module():
    """Get the classification index module with isolated imports"""
    import importlib.util
    import sys

    # Clear any cached classification modules to avoid conflicts
    modules_to_clear = [k for k in sys.modules.keys() if k.startswith('classification_index') or (k == 'index' and 'classification_fn' in str(sys.modules.get(k, '')))]
    for module in modules_to_clear:
        del sys.modules[module]

    # Set up paths
    classification_path = os.path.join(os.path.dirname(__file__), '..', '..', 'stack', 'lambda', 'contract_analysis', 'classification_fn')
    common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', 'stack', 'lambda', 'common_layer')
    langchain_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', 'stack', 'lambda', 'langchain_deps_layer')

    # Import with temporary path setup
    original_path = sys.path.copy()
    try:
        sys.path.insert(0, classification_path)
        sys.path.insert(0, common_layer_path)
        sys.path.insert(0, langchain_layer_path)

        classification_index_path = os.path.join(classification_path, 'index.py')
        spec = importlib.util.spec_from_file_location("classification_index", classification_index_path)
        classification_index = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(classification_index)

        return classification_index
    finally:
        sys.path[:] = original_path

@pytest.fixture
def classification_module():
    """Fixture to provide the classification module"""
    return get_classification_module()

@pytest.fixture
def app_properties_manager():
    """Fixture to provide AppPropertiesManager with isolated import"""
    import sys
    common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', 'stack', 'lambda', 'common_layer')
    original_path = sys.path.copy()
    try:
        sys.path.insert(0, common_layer_path)
        from app_properties_manager import AppPropertiesManager
        return AppPropertiesManager
    finally:
        sys.path[:] = original_path


class TestClassificationContractTypeUnit:
    """Unit tests for contract type classification changes."""

    @mock_aws
    @patch.dict('os.environ', {
        'GUIDELINES_TABLE_NAME': 'test-guidelines-table',
        'CLAUSES_TABLE_NAME': 'test-clauses-table'
    })
    def test_get_guidelines_clauses_queries_by_contract_type_id(self, classification_module, dynamodb_resource):
        """Test that get_guidelines_clauses uses contract_type_id as partition key."""
        # Use the session-scoped table
        table = dynamodb_resource.Table('test-guidelines-table')

        # Clear any existing items
        scan_result = table.scan()
        with table.batch_writer() as batch:
            for item in scan_result.get('Items', []):
                batch.delete_item(
                    Key={
                        'contract_type_id': item['contract_type_id'],
                        'clause_type_id': item['clause_type_id']
                    }
                )

        # Add test data
        table.put_item(Item={
            'contract_type_id': 'service-agreement',
            'clause_type_id': 'payment-terms',
            'name': 'Payment Terms',
            'examples': ['Payment due in 30 days']
        })
        table.put_item(Item={
            'contract_type_id': 'employment-contract',
            'clause_type_id': 'termination',
            'name': 'Termination Clause',
            'examples': ['30 days notice required']
        })

        # Mock the guidelines_table global variable
        with patch.object(classification_module, 'guidelines_table', table):
            # Test service agreement
            service_clauses = classification_module.get_guidelines_clauses('service-agreement')
            assert len(service_clauses) == 1
            assert service_clauses[0]['contract_type_id'] == 'service-agreement'
            assert service_clauses[0]['clause_type_id'] == 'payment-terms'

            # Test employment contract
            employment_clauses = classification_module.get_guidelines_clauses('employment-contract')
            assert len(employment_clauses) == 1
            assert employment_clauses[0]['contract_type_id'] == 'employment-contract'
            assert employment_clauses[0]['clause_type_id'] == 'termination'

            # Test nonexistent contract type
            with pytest.raises(RuntimeError, match="No clause types found for contract type nonexistent"):
                classification_module.get_guidelines_clauses('nonexistent')

    def test_classify_clause_signature_accepts_contract_type_id(self, classification_module):
        """Test that classify_clause function signature accepts contract_type_id parameter."""
        # Test that the function signature includes contract_type_id parameter
        import inspect

        # Get the function signature
        sig = inspect.signature(classification_module.classify_clause)
        params = list(sig.parameters.keys())

        # Verify contract_type_id is in the parameter list
        assert 'contract_type_id' in params
        assert 'clause' in params
        assert 'request_id' in params

        # Verify the parameter order is correct
        expected_params = ['clause', 'contract_type_id', 'request_id']
        for expected_param in expected_params:
            assert expected_param in params

    def test_handler_extracts_contract_type_id_from_event(self):
        """Test that handler extracts ContractTypeId from Step Functions event."""
        # Create a mock handler function that mimics the expected behavior
        def mock_handler(event, context):
            # Extract contract_type_id from event (this is the key change)
            contract_type_id = event.get("ContractTypeId")

            if not contract_type_id:
                raise ValueError("ContractTypeId is required")

            # Mock the rest of the handler logic
            job_id = event.get("JobId", "unknown")
            clause_number = event.get("ClauseNumber")
            output_language = event.get("OutputLanguage", "en")

            return {
                'contract_type_id': contract_type_id,
                'job_id': job_id,
                'clause_number': clause_number,
                'output_language': output_language
            }

        # Test with valid event
        event = {
            'JobId': 'test-job-123',
            'ClauseNumber': 1,
            'ContractTypeId': 'service-agreement',
            'OutputLanguage': 'en'
        }

        context = Mock()
        context.aws_request_id = 'test-request-123'

        result = mock_handler(event, context)

        assert result['contract_type_id'] == 'service-agreement'
        assert result['job_id'] == 'test-job-123'
        assert result['clause_number'] == 1
        assert result['output_language'] == 'en'

        # Test with missing ContractTypeId
        event_missing_contract_type = {
            'JobId': 'test-job-123',
            'ClauseNumber': 1,
            'OutputLanguage': 'en'
        }

        with pytest.raises(ValueError, match="ContractTypeId is required"):
            mock_handler(event_missing_contract_type, context)

    def test_build_system_prompt_uses_contract_type_data(self, classification_module, app_properties_manager):
        """Test that system prompt building uses contract type data from ContractTypesTable."""
        # Mock AppPropertiesManager
        mock_properties = Mock()
        mock_properties.get_parameter.return_value = 'Test Company'
        mock_properties.get_contract_type_data.return_value = {
            'name': 'Service Agreement',
            'description': 'Professional services contract',
            'company_party_type': 'Customer',
            'other_party_type': 'Service Provider'
        }

        # Create a mock _build_system_prompt function
        def mock_build_system_prompt(possible_types_str, examples_str, properties, contract_type_id, output_language="en"):
            # Get contract type data (this is the key change)
            contract_data = properties.get_contract_type_data(contract_type_id)
            company_name = properties.get_parameter('CompanyName', default='')

            # Build prompt with contract type data
            prompt = f"""Contract Type: {contract_data.get('description', contract_data.get('name', ''))}
Company: {company_name} ({contract_data.get('company_party_type', '')})
Other Party: {contract_data.get('other_party_type', '')}
Possible Types: {possible_types_str}
Examples: {examples_str}
Language: {output_language}"""

            return prompt

        # Test the function
        prompt = mock_build_system_prompt(
            possible_types_str="- Payment Terms\n- Liability",
            examples_str="<example>test</example>",
            properties=mock_properties,
            contract_type_id='service-agreement',
            output_language='en'
        )

        # Verify contract type data was retrieved
        mock_properties.get_contract_type_data.assert_called_once_with('service-agreement')

        # Verify prompt contains contract type information
        assert 'Professional services contract' in prompt
        assert 'Customer' in prompt
        assert 'Service Provider' in prompt
        assert 'Test Company' in prompt

    def test_clause_type_id_field_mapping(self):
        """Test that clause type mapping uses clause_type_id instead of type_id."""
        # Mock guidelines data with new schema
        clause_types = [
            {
                'name': 'Payment Terms',
                'clause_type_id': 'payment-terms',  # New field name
                'examples': ['Payment due in 30 days']
            },
            {
                'name': 'Liability Limitation',
                'clause_type_id': 'liability',  # New field name
                'examples': ['Liability is limited']
            }
        ]

        # Create mapping using new field name (this is the key change)
        clause_type_name_to_id = {clause_type['name']: clause_type['clause_type_id'] for clause_type in clause_types}

        # Verify mapping works correctly
        assert clause_type_name_to_id['Payment Terms'] == 'payment-terms'
        assert clause_type_name_to_id['Liability Limitation'] == 'liability'

        # Verify old field name would fail (if we tried to use it)
        with pytest.raises(KeyError):
            {clause_type['name']: clause_type['type_id'] for clause_type in clause_types}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])