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
Unit tests for the multi-contract type migration script
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime
from botocore.exceptions import ClientError

# Add the scripts directory to the path so we can import the migration script
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../scripts'))

from migrate_to_multi_contract_type import MultiContractTypeMigrator


class TestMultiContractTypeMigrator:
    """Test cases for MultiContractTypeMigrator class"""

    @pytest.fixture
    def mock_aws_clients(self):
        """Mock AWS clients"""
        with patch('migrate_to_multi_contract_type.boto3') as mock_boto3:
            mock_cf_client = Mock()
            mock_ssm_client = Mock()
            mock_dynamodb = Mock()

            mock_boto3.client.side_effect = lambda service, **kwargs: {
                'cloudformation': mock_cf_client,
                'ssm': mock_ssm_client
            }[service]
            mock_boto3.resource.return_value = mock_dynamodb

            # Mock CloudFormation stack responses
            mock_cf_client.describe_stacks.side_effect = [
                {  # Old stack
                    "Stacks": [{
                        "Outputs": [
                            {"OutputKey": "GuidelinesTableName", "OutputValue": "old-guidelines-table"},
                            {"OutputKey": "JobsTableName", "OutputValue": "old-jobs-table"}
                        ]
                    }]
                },
                {  # New stack
                    "Stacks": [{
                        "Outputs": [
                            {"OutputKey": "GuidelinesTableName", "OutputValue": "new-guidelines-table"},
                            {"OutputKey": "JobsTableName", "OutputValue": "new-jobs-table"},
                            {"OutputKey": "ContractTypesTableName", "OutputValue": "contract-types-table"}
                        ]
                    }]
                }
            ]

            yield {
                'cf_client': mock_cf_client,
                'ssm_client': mock_ssm_client,
                'dynamodb': mock_dynamodb
            }

    @pytest.fixture
    def migrator(self, mock_aws_clients):
        """Create a migrator instance with mocked AWS clients"""
        return MultiContractTypeMigrator("old-stack", "new-stack", "us-east-1")

    def test_init(self, mock_aws_clients):
        """Test migrator initialization"""
        migrator = MultiContractTypeMigrator("old-stack", "new-stack", "us-east-1")

        assert migrator.old_stack_name == "old-stack"
        assert migrator.new_stack_name == "new-stack"
        assert migrator.region == "us-east-1"
        assert migrator._contract_type_data is None

    def test_slugify_contract_type(self, migrator):
        """Test contract type slugification"""
        test_cases = [
            ("Service Agreement", "service-agreement"),
            ("Employment Contract", "employment-contract"),
            ("Non-Disclosure Agreement (NDA)", "non-disclosure-agreement-nda"),
            ("Purchase Order", "purchase-order"),
            ("Software License", "software-license"),
            ("Service  Agreement  ", "service-agreement"),  # Multiple spaces
            ("Service-Agreement", "service-agreement"),  # Already hyphenated
        ]

        for input_name, expected_slug in test_cases:
            result = migrator._slugify_contract_type(input_name)
            assert result == expected_slug, f"Expected '{expected_slug}' but got '{result}' for input '{input_name}'"

    def test_get_parameter_value_success(self, migrator, mock_aws_clients):
        """Test successful parameter retrieval"""
        mock_aws_clients['ssm_client'].get_parameter.return_value = {
            'Parameter': {'Value': 'Service Agreement'}
        }

        result = migrator._get_parameter_value('/ContractAnalysis/ContractType', {})

        assert result == 'Service Agreement'
        mock_aws_clients['ssm_client'].get_parameter.assert_called_once_with(
            Name='/ContractAnalysis/ContractType'
        )

    def test_get_parameter_value_not_found(self, migrator, mock_aws_clients):
        """Test parameter not found"""
        mock_aws_clients['ssm_client'].get_parameter.side_effect = ClientError(
            {'Error': {'Code': 'ParameterNotFound'}}, 'GetParameter'
        )

        result = migrator._get_parameter_value('/ContractAnalysis/ContractType', {})

        assert result is None

    def test_get_parameter_value_other_error(self, migrator, mock_aws_clients):
        """Test other parameter retrieval errors"""
        mock_aws_clients['ssm_client'].get_parameter.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'GetParameter'
        )

        with pytest.raises(RuntimeError, match="Failed to get parameter"):
            migrator._get_parameter_value('/ContractAnalysis/ContractType', {})

    def test_create_contract_type_from_existing_config_success(self, migrator, mock_aws_clients):
        """Test successful contract type creation"""
        # Mock parameter retrieval
        mock_aws_clients['ssm_client'].get_parameter.side_effect = [
            {'Parameter': {'Value': 'Service Agreement'}},  # ContractType
            {'Parameter': {'Value': 'Customer'}},  # CompanyPartyType
            {'Parameter': {'Value': 'Service Provider'}},  # OtherPartyType
            {'Parameter': {'Value': '0'}},  # HighRiskThreshold
            {'Parameter': {'Value': '1'}},  # MediumRiskThreshold
            {'Parameter': {'Value': '3'}},  # LowRiskThreshold
            {'Parameter': {'Value': 'en'}},  # Language
        ]

        # Mock DynamoDB table
        mock_table = Mock()
        mock_table.get_item.return_value = {}  # Contract type doesn't exist
        mock_table.put_item.return_value = {}
        mock_aws_clients['dynamodb'].Table.return_value = mock_table

        result = migrator._create_contract_type_from_existing_config()

        assert result['contract_type_id'] == 'service-agreement'
        assert result['name'] == 'Service Agreement'
        assert result['company_party_type'] == 'Customer'
        assert result['other_party_type'] == 'Service Provider'
        assert result['high_risk_threshold'] == 0
        assert result['is_active'] is True

        # Verify table operations
        mock_table.get_item.assert_called_once()
        mock_table.put_item.assert_called_once()

    def test_create_contract_type_already_exists(self, migrator, mock_aws_clients):
        """Test contract type creation when it already exists"""
        # Mock parameter retrieval - need to handle multiple calls
        mock_aws_clients['ssm_client'].get_parameter.side_effect = [
            {'Parameter': {'Value': 'Service Agreement'}},  # ContractType
            ClientError({'Error': {'Code': 'ParameterNotFound'}}, 'GetParameter'),  # CompanyPartyType - not found
            ClientError({'Error': {'Code': 'ParameterNotFound'}}, 'GetParameter'),  # OtherPartyType - not found
            ClientError({'Error': {'Code': 'ParameterNotFound'}}, 'GetParameter'),  # HighRiskThreshold - not found
            ClientError({'Error': {'Code': 'ParameterNotFound'}}, 'GetParameter'),  # MediumRiskThreshold - not found
            ClientError({'Error': {'Code': 'ParameterNotFound'}}, 'GetParameter'),  # LowRiskThreshold - not found
            ClientError({'Error': {'Code': 'ParameterNotFound'}}, 'GetParameter'),  # Language - not found
        ]

        # Mock existing contract type
        existing_contract_type = {
            'contract_type_id': 'service-agreement',
            'name': 'Service Agreement',
            'description': 'Service Agreement'
        }

        mock_table = Mock()
        mock_table.get_item.return_value = {'Item': existing_contract_type}
        mock_aws_clients['dynamodb'].Table.return_value = mock_table

        result = migrator._create_contract_type_from_existing_config()

        assert result == existing_contract_type
        mock_table.put_item.assert_not_called()  # Should not create new one

    def test_create_contract_type_missing_parameter(self, migrator, mock_aws_clients):
        """Test contract type creation with missing ContractType parameter"""
        mock_aws_clients['ssm_client'].get_parameter.side_effect = ClientError(
            {'Error': {'Code': 'ParameterNotFound'}}, 'GetParameter'
        )

        with pytest.raises(ValueError, match="ContractType parameter not found"):
            migrator._create_contract_type_from_existing_config()

    def test_migrate_guidelines_success(self, migrator, mock_aws_clients):
        """Test successful guidelines migration"""
        # Set up contract type data
        migrator._contract_type_data = {
            'contract_type_id': 'service-agreement',
            'name': 'Service Agreement'
        }

        # Mock old guidelines data
        old_guidelines = [
            {
                'type_id': 'clause-1',
                'name': 'Payment Terms',
                'standard_wording': 'Payment due within 30 days',
                'level': 'high',
                'evaluation_questions': ['Is payment term reasonable?'],
                'examples': ['Net 30', 'Net 60']
            },
            {
                'type_id': 'clause-2',
                'name': 'Termination',
                'standard_wording': 'Either party may terminate',
                'level': 'medium',
                'evaluation_questions': ['Is termination clause fair?'],
                'examples': ['30 days notice']
            }
        ]

        # Mock old table
        mock_old_table = Mock()
        mock_old_table.scan.return_value = {'Items': old_guidelines}

        # Mock new table
        mock_new_table = Mock()
        mock_new_table.query.return_value = {'Items': []}  # No existing guidelines
        mock_batch_writer = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_new_table.batch_writer.return_value = mock_context_manager

        mock_aws_clients['dynamodb'].Table.side_effect = [mock_old_table, mock_new_table]

        result = migrator._migrate_guidelines()

        assert result == 2  # Two guidelines migrated
        assert mock_batch_writer.put_item.call_count == 2

        # Verify transformed data structure
        call_args = mock_batch_writer.put_item.call_args_list
        first_guideline = call_args[0][1]['Item']
        assert first_guideline['contract_type_id'] == 'service-agreement'
        assert first_guideline['clause_type_id'] == 'clause-1'
        assert 'type_id' not in first_guideline  # Old field should be removed

    def test_migrate_guidelines_no_contract_type(self, migrator):
        """Test guidelines migration without contract type"""
        with pytest.raises(RuntimeError, match="Contract type must be created"):
            migrator._migrate_guidelines()

    def test_migrate_jobs_success(self, migrator, mock_aws_clients):
        """Test successful jobs migration"""
        # Set up contract type data
        migrator._contract_type_data = {
            'contract_type_id': 'service-agreement',
            'name': 'Service Agreement'
        }

        # Mock old jobs data
        old_jobs = [
            {
                'id': 'job-1',
                'document_s3_key': 'contracts/contract1.pdf',
                'description': 'Test contract 1',
                'status': 'completed'
            },
            {
                'id': 'job-2',
                'document_s3_key': 'contracts/contract2.pdf',
                'description': 'Test contract 2',
                'status': 'running'
            }
        ]

        # Mock old table
        mock_old_table = Mock()
        mock_old_table.scan.return_value = {'Items': old_jobs}

        # Mock new table
        mock_new_table = Mock()
        mock_batch_writer = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_new_table.batch_writer.return_value = mock_context_manager

        mock_aws_clients['dynamodb'].Table.side_effect = [mock_old_table, mock_new_table]

        result = migrator._migrate_jobs()

        assert result == 2  # Two jobs migrated
        assert mock_batch_writer.put_item.call_count == 2

        # Verify contract_type_id was added
        call_args = mock_batch_writer.put_item.call_args_list
        first_job = call_args[0][1]['Item']
        assert first_job['contract_type_id'] == 'service-agreement'
        assert first_job['id'] == 'job-1'  # Original data preserved

    def test_migrate_jobs_no_contract_type(self, migrator):
        """Test jobs migration without contract type"""
        with pytest.raises(RuntimeError, match="Contract type must be created"):
            migrator._migrate_jobs()

    def test_validate_migration_success(self, migrator, mock_aws_clients):
        """Test successful migration validation"""
        # Set up contract type data
        migrator._contract_type_data = {
            'contract_type_id': 'service-agreement',
            'name': 'Service Agreement'
        }

        # Mock contract types table
        mock_contract_types_table = Mock()
        mock_contract_types_table.get_item.return_value = {
            'Item': {'contract_type_id': 'service-agreement'}
        }

        # Mock old tables for count validation
        mock_old_guidelines_table = Mock()
        mock_old_guidelines_table.scan.return_value = {'Count': 5}

        mock_old_jobs_table = Mock()
        mock_old_jobs_table.scan.return_value = {'Count': 3}

        # Mock new tables for count validation
        mock_new_guidelines_table = Mock()
        mock_new_guidelines_table.query.return_value = {'Count': 5}

        mock_new_jobs_table = Mock()
        mock_new_jobs_table.query.return_value = {'Count': 3}
        mock_new_jobs_table.scan.return_value = {
            'Items': [{'id': 'job-1', 'contract_type_id': 'service-agreement'}]
        }

        # Set up table mocking
        def table_side_effect(table_name):
            table_map = {
                'contract-types-table': mock_contract_types_table,
                'old-guidelines-table': mock_old_guidelines_table,
                'new-guidelines-table': mock_new_guidelines_table,
                'old-jobs-table': mock_old_jobs_table,
                'new-jobs-table': mock_new_jobs_table
            }
            return table_map[table_name]

        mock_aws_clients['dynamodb'].Table.side_effect = table_side_effect

        result = migrator._validate_migration()

        assert result is True

    def test_validate_migration_count_mismatch(self, migrator, mock_aws_clients):
        """Test validation failure due to count mismatch"""
        # Set up contract type data
        migrator._contract_type_data = {
            'contract_type_id': 'service-agreement',
            'name': 'Service Agreement'
        }

        # Mock contract types table
        mock_contract_types_table = Mock()
        mock_contract_types_table.get_item.return_value = {
            'Item': {'contract_type_id': 'service-agreement'}
        }

        # Mock count mismatch
        mock_old_guidelines_table = Mock()
        mock_old_guidelines_table.scan.return_value = {'Count': 5}

        mock_new_guidelines_table = Mock()
        mock_new_guidelines_table.query.return_value = {'Count': 3}  # Mismatch!

        def table_side_effect(table_name):
            table_map = {
                'contract-types-table': mock_contract_types_table,
                'old-guidelines-table': mock_old_guidelines_table,
                'new-guidelines-table': mock_new_guidelines_table
            }
            return table_map[table_name]

        mock_aws_clients['dynamodb'].Table.side_effect = table_side_effect

        with pytest.raises(RuntimeError, match="Guidelines count mismatch"):
            migrator._validate_migration()

    def test_migrate_full_process(self, migrator, mock_aws_clients):
        """Test the complete migration process"""
        # Mock parameter retrieval for contract type creation
        mock_aws_clients['ssm_client'].get_parameter.side_effect = [
            {'Parameter': {'Value': 'Service Agreement'}},  # ContractType
            {'Parameter': {'Value': 'Customer'}},  # CompanyPartyType
            {'Parameter': {'Value': 'Service Provider'}},  # OtherPartyType
            {'Parameter': {'Value': '0'}},  # HighRiskThreshold
            {'Parameter': {'Value': '1'}},  # MediumRiskThreshold
            {'Parameter': {'Value': '3'}},  # LowRiskThreshold
            {'Parameter': {'Value': 'en'}},  # Language
        ]

        # Mock all table operations for successful migration
        mock_tables = {}

        # Contract types table
        mock_contract_types_table = Mock()
        mock_contract_types_table.get_item.side_effect = [
            {},  # Doesn't exist during creation
            {'Item': {'contract_type_id': 'service-agreement'}}  # Exists during validation
        ]
        mock_contract_types_table.put_item.return_value = {}
        mock_tables['contract-types-table'] = mock_contract_types_table

        # Guidelines tables
        mock_old_guidelines_table = Mock()
        mock_old_guidelines_table.scan.side_effect = [
            {'Items': [{'type_id': 'clause-1', 'name': 'Test Clause'}]},  # Migration
            {'Count': 1}  # Count validation
        ]
        mock_tables['old-guidelines-table'] = mock_old_guidelines_table

        mock_new_guidelines_table = Mock()
        mock_new_guidelines_table.query.side_effect = [
            {'Items': []},  # No existing guidelines to clear
            {'Count': 1}    # Count validation
        ]
        mock_batch_writer = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_new_guidelines_table.batch_writer.return_value = mock_context_manager
        mock_tables['new-guidelines-table'] = mock_new_guidelines_table

        # Jobs tables
        mock_old_jobs_table = Mock()
        mock_old_jobs_table.scan.side_effect = [
            {'Items': [{'id': 'job-1', 'status': 'completed'}]},  # Migration
            {'Count': 1}  # Count validation
        ]
        mock_tables['old-jobs-table'] = mock_old_jobs_table

        mock_new_jobs_table = Mock()
        mock_jobs_batch_writer = Mock()
        mock_jobs_context_manager = Mock()
        mock_jobs_context_manager.__enter__ = Mock(return_value=mock_jobs_batch_writer)
        mock_jobs_context_manager.__exit__ = Mock(return_value=None)
        mock_new_jobs_table.batch_writer.return_value = mock_jobs_context_manager
        mock_new_jobs_table.query.return_value = {'Count': 1}  # Count validation
        mock_new_jobs_table.scan.return_value = {
            'Items': [{'id': 'job-1', 'contract_type_id': 'service-agreement'}]
        }
        mock_tables['new-jobs-table'] = mock_new_jobs_table

        mock_aws_clients['dynamodb'].Table.side_effect = lambda name: mock_tables[name]

        # Run migration
        results = migrator.migrate()

        # Verify results
        assert results['contract_type_created'] is True
        assert results['contract_type_id'] == 'service-agreement'
        assert results['contract_type_name'] == 'Service Agreement'
        assert results['guidelines_migrated'] == 1
        assert results['jobs_migrated'] == 1
        assert results['validation_passed'] is True


class TestMigrationScriptHelpers:
    """Test helper functions and edge cases"""

    @patch('migrate_to_multi_contract_type.boto3')
    def test_slugify_edge_cases(self, mock_boto3):
        """Test edge cases for slugification"""
        # Mock AWS clients to avoid credential issues
        mock_cf_client = Mock()
        mock_ssm_client = Mock()
        mock_dynamodb = Mock()

        mock_boto3.client.side_effect = lambda service, **kwargs: {
            'cloudformation': mock_cf_client,
            'ssm': mock_ssm_client
        }[service]
        mock_boto3.resource.return_value = mock_dynamodb

        # Mock stack responses
        mock_cf_client.describe_stacks.side_effect = [
            {"Stacks": [{"Outputs": []}]},  # Old stack
            {"Stacks": [{"Outputs": []}]}   # New stack
        ]

        migrator = MultiContractTypeMigrator("old", "new")

        # Empty string
        assert migrator._slugify_contract_type("") == ""

        # Only special characters
        assert migrator._slugify_contract_type("!@#$%") == ""

        # Mixed case with numbers
        assert migrator._slugify_contract_type("Contract Type 2024") == "contract-type-2024"

        # Leading/trailing hyphens
        assert migrator._slugify_contract_type("-Contract Type-") == "contract-type"