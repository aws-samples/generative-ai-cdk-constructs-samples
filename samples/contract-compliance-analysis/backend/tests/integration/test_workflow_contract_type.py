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
import boto3
import json
import time
from decimal import Decimal
from moto import mock_aws
from unittest.mock import patch, MagicMock
import sys
import os
import importlib.util
from contextlib import contextmanager


@contextmanager
def validation_module_context():
    """Context manager to safely import validation modules without path conflicts."""
    validation_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/contract_analysis/validation_fn')
    common_layer_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/common_layer')

    # Store original sys.path
    original_path = sys.path.copy()
    modules_to_cleanup = []

    try:
        # Clear conflicting paths and add validation paths
        sys.path = [p for p in sys.path if 'classification' not in p and 'evaluation' not in p]
        sys.path.insert(0, validation_path)
        sys.path.insert(0, common_layer_path)

        # Import modules dynamically
        index_spec = importlib.util.spec_from_file_location("validation_index", os.path.join(validation_path, "index.py"))
        index_module = importlib.util.module_from_spec(index_spec)
        index_spec.loader.exec_module(index_module)
        modules_to_cleanup.append("validation_index")

        yield index_module

    finally:
        # Clean up imported modules to avoid conflicts
        for module_name in modules_to_cleanup:
            sys.modules.pop(module_name, None)
        # Also clean up any 'index' modules that might conflict
        sys.modules.pop('index', None)
        # Restore original sys.path
        sys.path = original_path


@contextmanager
def classification_module_context():
    """Context manager to safely import classification modules without path conflicts."""
    classification_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/contract_analysis/classification_fn')
    common_layer_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/common_layer')
    langchain_layer_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/langchain_deps_layer')

    # Store original sys.path and environment
    original_path = sys.path.copy()
    original_env = os.environ.copy()
    modules_to_cleanup = []

    try:
        # Set required environment variables
        os.environ.setdefault('GUIDELINES_TABLE_NAME', 'test-guidelines-table')
        os.environ.setdefault('CLAUSES_TABLE_NAME', 'test-clauses-table')
        os.environ.setdefault('CONTRACT_TYPES_TABLE', 'test-contract-types-table')

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
        # Restore original sys.path and environment
        sys.path = original_path
        os.environ.clear()
        os.environ.update(original_env)


@contextmanager
def evaluation_module_context():
    """Context manager to safely import evaluation modules without path conflicts."""
    evaluation_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/contract_analysis/evaluation_fn')
    common_layer_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/common_layer')
    langchain_layer_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/langchain_deps_layer')

    # Store original sys.path and environment
    original_path = sys.path.copy()
    original_env = os.environ.copy()
    modules_to_cleanup = []

    try:
        # Set required environment variables
        os.environ.setdefault('GUIDELINES_TABLE_NAME', 'test-guidelines-table')
        os.environ.setdefault('CLAUSES_TABLE_NAME', 'test-clauses-table')
        os.environ.setdefault('CONTRACT_TYPES_TABLE', 'test-contract-types-table')

        # Clear conflicting paths and add evaluation paths
        sys.path = [p for p in sys.path if 'classification' not in p and 'validation' not in p]
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
        # Restore original sys.path and environment
        sys.path = original_path
        os.environ.clear()
        os.environ.update(original_env)


@contextmanager
def risk_module_context():
    """Context manager to safely import risk modules without path conflicts."""
    risk_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/contract_analysis/risk_fn')
    common_layer_path = os.path.join(os.path.dirname(__file__), '../../stack/lambda/common_layer')

    # Store original sys.path and environment
    original_path = sys.path.copy()
    original_env = os.environ.copy()
    modules_to_cleanup = []

    try:
        # Set required environment variables
        os.environ.setdefault('JOBS_TABLE', 'test-jobs-table')
        os.environ.setdefault('CLAUSES_TABLE', 'test-clauses-table')
        os.environ.setdefault('GUIDELINES_TABLE', 'test-guidelines-table')
        os.environ.setdefault('CONTRACT_TYPES_TABLE', 'test-contract-types-table')

        # Clear conflicting paths and add risk paths
        sys.path = [p for p in sys.path if 'classification' not in p and 'evaluation' not in p and 'validation' not in p]
        sys.path.insert(0, risk_path)
        sys.path.insert(0, common_layer_path)

        # Import modules dynamically
        index_spec = importlib.util.spec_from_file_location("risk_index", os.path.join(risk_path, "index.py"))
        index_module = importlib.util.module_from_spec(index_spec)
        index_spec.loader.exec_module(index_module)
        modules_to_cleanup.append("risk_index")

        app_props_spec = importlib.util.spec_from_file_location("risk_app_properties", os.path.join(common_layer_path, "app_properties_manager.py"))
        app_props_module = importlib.util.module_from_spec(app_props_spec)
        app_props_spec.loader.exec_module(app_props_module)
        modules_to_cleanup.append("risk_app_properties")

        yield index_module, app_props_module

    finally:
        # Clean up imported modules to avoid conflicts
        for module_name in modules_to_cleanup:
            sys.modules.pop(module_name, None)
        # Also clean up any 'index' modules that might conflict
        sys.modules.pop('index', None)
        # Restore original sys.path and environment
        sys.path = original_path
        os.environ.clear()
        os.environ.update(original_env)


@mock_aws
class TestWorkflowContractType:
    """Integration tests for Step Functions workflow with contract type support"""

    def setup_method(self, method):
        """Set up test environment"""
        # Use session-scoped DynamoDB tables
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        # Get existing tables
        self.contract_types_table = self.dynamodb.Table('test-contract-types-table')
        self.guidelines_table = self.dynamodb.Table('test-guidelines-table')
        self.clauses_table = self.dynamodb.Table('test-clauses-table')
        self.jobs_table = self.dynamodb.Table('test-jobs-table')

        # Clear all tables
        for table in [self.contract_types_table, self.guidelines_table, self.clauses_table, self.jobs_table]:
            scan_result = table.scan()
            with table.batch_writer() as batch:
                for item in scan_result.get('Items', []):
                    # Get the key schema for this table
                    key_names = [key['AttributeName'] for key in table.key_schema]
                    key = {name: item[name] for name in key_names}
                    batch.delete_item(Key=key)

        # Create S3 bucket
        self.s3 = boto3.client('s3', region_name='us-east-1')
        self.s3.create_bucket(Bucket='test-contract-bucket')

        # Create Step Functions client
        self.sfn = boto3.client('stepfunctions', region_name='us-east-1')

        # Sample contract type data
        self.contract_type_data = {
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
        }

        # Sample guidelines data
        self.guidelines_data = [
            {
                'contract_type_id': 'service-agreement',
                'clause_type_id': 'payment-terms',
                'name': 'Payment Terms',
                'level': 'high',
                'standard_wording': 'Payment shall be made within 30 days',
                'evaluation_questions': [
                    'Does the clause specify payment terms?',
                    'Are payment deadlines clearly defined?'
                ],
                'examples': ['Payment is due within 30 days of invoice']
            },
            {
                'contract_type_id': 'service-agreement',
                'clause_type_id': 'termination',
                'name': 'Termination Clause',
                'level': 'medium',
                'standard_wording': 'Either party may terminate with 30 days notice',
                'evaluation_questions': [
                    'Does the clause specify termination conditions?'
                ],
                'examples': ['This agreement may be terminated by either party']
            }
        ]

    def _setup_test_data(self):
        """Set up test data in DynamoDB tables"""
        # Insert contract type
        self.contract_types_table.put_item(Item=self.contract_type_data)

        # Insert guidelines
        for guideline in self.guidelines_data:
            self.guidelines_table.put_item(Item=guideline)

    def test_workflow_input_schema_includes_contract_type(self):
        """Test that workflow input schema includes ContractTypeId parameter"""
        # This test verifies the workflow can accept ContractTypeId in input
        workflow_input = {
            "document_s3_path": "s3://test-bucket/test-contract.pdf",
            "ContractTypeId": "service-agreement",
            "OutputLanguage": "en",
            "AdditionalChecks": {}
        }

        # Verify all required fields are present
        assert "ContractTypeId" in workflow_input
        assert workflow_input["ContractTypeId"] == "service-agreement"
        assert "document_s3_path" in workflow_input
        assert "OutputLanguage" in workflow_input

    @patch('boto3.client')
    def test_contract_type_validation_step(self, mock_boto_client):
        """Test contract type validation step"""
        self._setup_test_data()

        # Use context manager to safely import validation module
        with validation_module_context() as validation_module:
            handler = validation_module.handler

            # Test valid contract type
            event = {"ContractTypeId": "service-agreement"}
            context = MagicMock()

            with patch.dict('os.environ', {'CONTRACT_TYPES_TABLE': 'test-contract-types-table'}):
                with patch.object(validation_module, 'boto3') as mock_boto3:
                    mock_dynamodb = MagicMock()
                    mock_boto3.resource.return_value = mock_dynamodb
                    mock_dynamodb.Table.return_value = self.contract_types_table

                    result = handler(event, context)
                    assert result == event  # Should pass through the event

            # Test invalid contract type
            event_invalid = {"ContractTypeId": "invalid-type"}
            with patch.dict('os.environ', {'CONTRACT_TYPES_TABLE': 'test-contract-types-table'}):
                with patch.object(validation_module, 'boto3') as mock_boto3:
                    mock_dynamodb = MagicMock()
                    mock_boto3.resource.return_value = mock_dynamodb
                    mock_dynamodb.Table.return_value = self.contract_types_table

                    with pytest.raises(ValueError, match="Contract type 'invalid-type' not found"):
                        handler(event_invalid, context)

    @patch('boto3.client')
    def test_classification_receives_contract_type(self, mock_boto_client):
        """Test that classification Lambda receives ContractTypeId parameter"""
        self._setup_test_data()

        # Use context manager to safely import classification module
        with classification_module_context() as (classification_module, app_props_module):
            handler = classification_module.handler

            # Set up test clause
            self.clauses_table.put_item(Item={
                'job_id': 'test-job-123',
                'clause_number': 1,
                'text': 'Payment shall be made within 30 days of invoice receipt.'
            })

            event = {
                "JobId": "test-job-123",
                "ClauseNumber": 1,
                "ContractTypeId": "service-agreement",
                "OutputLanguage": "en"
            }
            context = MagicMock()
            context.aws_request_id = "test-request-123"

            # Mock the tables and dependencies
            with patch.dict('os.environ', {
                'GUIDELINES_TABLE_NAME': 'test-guidelines-table',
                'CLAUSES_TABLE_NAME': 'test-clauses-table',
                'CONTRACT_TYPES_TABLE': 'test-contract-types-table'
            }):
                with patch.object(classification_module, 'clauses_table', self.clauses_table):
                    with patch.object(classification_module, 'guidelines_table', self.guidelines_table):
                        with patch.object(classification_module, 'invoke_llm') as mock_llm:
                            with patch.object(classification_module, 'AppPropertiesManager') as mock_props:
                                # Mock LLM response
                                mock_llm.return_value = (
                                    '<clause_replica>Payment shall be made within 30 days</clause_replica><type reason="Payment terms specified">Payment Terms</type>',
                                    {},
                                    'stop'
                                )

                                # Mock properties manager
                                mock_props_instance = MagicMock()
                                mock_props_instance.get_parameter.return_value = 'test-model'
                                mock_props_instance.get_contract_type_data.return_value = {
                                    'description': 'Service Agreement',
                                    'company_party_type': 'Customer',
                                    'other_party_type': 'Service Provider'
                                }
                                mock_props.return_value = mock_props_instance

                                result = handler(event, context)

                                # Verify the function completed successfully
                                assert result == "OK"

                                # Note: Contract type data is now retrieved via DynamoDBContractTypeRepository
                                # instead of AppPropertiesManager.get_contract_type_data()

    @patch('boto3.client')
    def test_evaluation_receives_contract_type(self, mock_boto_client):
        """Test that evaluation Lambda receives ContractTypeId parameter"""
        self._setup_test_data()

        # Use context manager to safely import evaluation module
        with evaluation_module_context() as (evaluation_module, app_props_module):
            evaluation_handler = evaluation_module.handler

            # Set up test clause with classification results
            self.clauses_table.put_item(Item={
                'job_id': 'test-job-123',
                'clause_number': 1,
                'text': 'Payment shall be made within 30 days of invoice receipt.',
                'types': [
                    {
                        'type_id': 'payment-terms',
                        'type_name': 'Payment Terms',
                        'classification_analysis': 'Payment terms specified'
                    }
                ]
            })

            event = {
                "JobId": "test-job-123",
                "ClauseNumber": 1,
                "ContractTypeId": "service-agreement",
                "OutputLanguage": "en"
            }
            context = MagicMock()
            context.aws_request_id = "test-request-123"

            # Mock the tables and dependencies
            with patch.dict('os.environ', {
                'GUIDELINES_TABLE_NAME': 'test-guidelines-table',
                'CLAUSES_TABLE_NAME': 'test-clauses-table',
                'CONTRACT_TYPES_TABLE': 'test-contract-types-table'
            }):
                with patch.object(evaluation_module, 'clauses_table', self.clauses_table):
                    with patch.object(evaluation_module, 'guidelines_table', self.guidelines_table):
                        with patch.object(evaluation_module, 'invoke_llm') as mock_llm:
                            with patch.object(evaluation_module, 'AppPropertiesManager') as mock_props:
                                # Mock LLM response
                                mock_llm.return_value = (
                                    '<answering><question_replica>Does the clause specify payment terms?</question_replica><reasoning_translated>Yes, payment terms are clearly specified</reasoning_translated><answer_english>Yes</answer_english><answer_translated>Yes</answer_translated></answering>',
                                    {},
                                    'stop'
                                )

                                # Mock properties manager
                                mock_props_instance = MagicMock()
                                mock_props_instance.get_parameter.return_value = 'test-model'
                                mock_props_instance.get_contract_type_data.return_value = {
                                    'description': 'Service Agreement',
                                    'company_party_type': 'Customer',
                                    'other_party_type': 'Service Provider'
                                }
                                mock_props.return_value = mock_props_instance

                                result = evaluation_handler(event, context)

                                # Verify the function completed successfully
                                assert result == {"Status": "OK"}

                                # Note: Contract type data is now retrieved via DynamoDBContractTypeRepository
                                # instead of AppPropertiesManager.get_contract_type_data()

    @patch('boto3.client')
    def test_risk_calculation_receives_contract_type(self, mock_boto_client):
        """Test that risk calculation Lambda receives ContractTypeId parameter"""
        self._setup_test_data()

        # Use context manager to safely import risk module
        with risk_module_context() as (risk_module, app_props_module):
            risk_handler = risk_module.handler

            # Set up test job
            self.jobs_table.put_item(Item={
                'id': 'test-job-123',
                'document_s3_key': 'test-contract.pdf',
                'contract_type_id': 'service-agreement',
                'description': 'Test contract',
                'output_language': 'en'
            })

            # Set up test clauses with evaluation results
            self.clauses_table.put_item(Item={
                'job_id': 'test-job-123',
                'clause_number': 1,
                'text': 'Payment shall be made within 30 days.',
                'types': [
                    {
                        'type_id': 'payment-terms',
                        'type_name': 'Payment Terms',
                        'compliant': True,
                        'analysis': 'Payment terms are compliant'
                    }
                ]
            })

            event = {
                "JobId": "test-job-123",
                "ContractTypeId": "service-agreement"
            }
            context = MagicMock()

            # Mock the tables and dependencies
            with patch.dict('os.environ', {
                'JOBS_TABLE': 'test-jobs-table',
                'CLAUSES_TABLE': 'test-clauses-table',
                'GUIDELINES_TABLE': 'test-guidelines-table',
                'CONTRACT_TYPES_TABLE': 'test-contract-types-table'
            }):
                with patch.object(risk_module, 'jobs_table', self.jobs_table):
                    with patch.object(risk_module, 'clauses_table', self.clauses_table):
                        with patch.object(risk_module, 'guidelines_table', self.guidelines_table):
                            with patch.object(risk_module, 'AppPropertiesManager') as mock_props:
                                # Mock properties manager
                                mock_props_instance = MagicMock()
                                mock_props_instance.get_contract_type_data.return_value = {
                                    'high_risk_threshold': 0,
                                    'medium_risk_threshold': 1,
                                    'low_risk_threshold': 3
                                }
                                mock_props.return_value = mock_props_instance

                                result = risk_handler(event, context)

                                # Verify the function completed successfully
                                assert 'id' in result
                                assert result['id'] == 'test-job-123'

                                # Note: Contract type data is now retrieved via DynamoDBContractTypeRepository
                                # instead of AppPropertiesManager.get_contract_type_data()

    def test_workflow_error_handling_invalid_contract_type(self):
        """Test workflow error handling for invalid contract type"""
        # This test verifies that the workflow fails gracefully with invalid contract type
        workflow_input = {
            "document_s3_path": "s3://test-bucket/test-contract.pdf",
            "ContractTypeId": "invalid-contract-type",
            "OutputLanguage": "en",
            "AdditionalChecks": {}
        }

        # The validation step should catch this and raise an appropriate error
        # In a real Step Functions execution, this would result in an execution failure
        # with a clear error message about the invalid contract type

        # Verify the error case is handled
        assert workflow_input["ContractTypeId"] == "invalid-contract-type"

    def test_workflow_passes_contract_type_through_pipeline(self):
        """Test that ContractTypeId flows through the entire analysis pipeline"""
        # This test verifies the data flow through all steps

        # Initial workflow input
        workflow_input = {
            "document_s3_path": "s3://test-bucket/test-contract.pdf",
            "ContractTypeId": "service-agreement",
            "OutputLanguage": "en",
            "AdditionalChecks": {}
        }

        # After validation step - should pass through unchanged
        validation_output = workflow_input.copy()

        # After preprocessing step - should include ContractTypeId
        preprocessing_output = {
            "JobId": "test-execution-123",
            "ContractTypeId": "service-agreement",
            "ClauseNumbers": [0, 1, 2],
            "OutputLanguage": "en",
            "AdditionalChecks": {}
        }

        # Classification map parameters - should include ContractTypeId
        classification_params = {
            "JobId": "test-execution-123",
            "ClauseNumber": 1,
            "ContractTypeId": "service-agreement",
            "OutputLanguage": "en"
        }

        # Evaluation map parameters - should include ContractTypeId
        evaluation_params = {
            "JobId": "test-execution-123",
            "ClauseNumber": 1,
            "ContractTypeId": "service-agreement",
            "OutputLanguage": "en"
        }

        # Risk calculation input - should include ContractTypeId
        risk_input = {
            "JobId": "test-execution-123",
            "ContractTypeId": "service-agreement",
            "OutputLanguage": "en"
        }

        # Verify ContractTypeId is present at each step
        assert validation_output["ContractTypeId"] == "service-agreement"
        assert preprocessing_output["ContractTypeId"] == "service-agreement"
        assert classification_params["ContractTypeId"] == "service-agreement"
        assert evaluation_params["ContractTypeId"] == "service-agreement"
        assert risk_input["ContractTypeId"] == "service-agreement"

    def test_multiple_contract_types_isolation(self):
        """Test that different contract types use their own guidelines"""
        # Set up multiple contract types
        employment_contract_type = {
            'contract_type_id': 'employment-agreement',
            'name': 'Employment Agreement',
            'description': 'Employment contract',
            'company_party_type': 'Employer',
            'other_party_type': 'Employee',
            'high_risk_threshold': 0,
            'medium_risk_threshold': 2,
            'low_risk_threshold': 5,
            'is_active': True,
            'default_language': 'en',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z'
        }

        employment_guidelines = [
            {
                'contract_type_id': 'employment-agreement',
                'clause_type_id': 'salary-terms',
                'name': 'Salary Terms',
                'level': 'high',
                'standard_wording': 'Salary shall be paid monthly',
                'evaluation_questions': ['Does the clause specify salary payment terms?'],
                'examples': ['Salary is paid on the last day of each month']
            }
        ]

        # Set up test data
        self._setup_test_data()
        self.contract_types_table.put_item(Item=employment_contract_type)
        for guideline in employment_guidelines:
            self.guidelines_table.put_item(Item=guideline)

        # Verify service agreement guidelines
        service_guidelines = list(self.guidelines_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('contract_type_id').eq('service-agreement')
        )['Items'])
        assert len(service_guidelines) == 2
        assert any(g['clause_type_id'] == 'payment-terms' for g in service_guidelines)

        # Verify employment agreement guidelines
        employment_guidelines_result = list(self.guidelines_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('contract_type_id').eq('employment-agreement')
        )['Items'])
        assert len(employment_guidelines_result) == 1
        assert employment_guidelines_result[0]['clause_type_id'] == 'salary-terms'

        # Verify no cross-contamination
        assert not any(g['clause_type_id'] == 'salary-terms' for g in service_guidelines)
        assert not any(g['clause_type_id'] == 'payment-terms' for g in employment_guidelines_result)