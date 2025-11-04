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
import os
import sys
import importlib.util
from unittest.mock import patch, MagicMock
from moto import mock_aws


class TestValidationContractType:
    """Unit tests for contract type validation Lambda function"""

    @classmethod
    def setup_class(cls):
        """Set up the test class by importing the handler once"""
        validation_path = os.path.join(os.path.dirname(__file__), '..', '..', 'stack', 'lambda', 'contract_analysis', 'validation_fn')
        if validation_path not in sys.path:
            sys.path.insert(0, validation_path)

        # Import with a specific name to avoid conflicts
        import importlib.util
        spec = importlib.util.spec_from_file_location("validation_index", os.path.join(validation_path, "index.py"))
        validation_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validation_module)
        cls.handler_module = validation_module

    def test_validation_success(self):
        """Test successful contract type validation"""
        with patch.dict('os.environ', {'CONTRACT_TYPES_TABLE': 'test-contract-types-table'}):
            with patch.object(self.handler_module, 'boto3') as mock_boto3:
                # Mock DynamoDB table
                mock_table = MagicMock()
                mock_table.get_item.return_value = {
                    'Item': {
                        'contract_type_id': 'service-agreement',
                        'name': 'Service Agreement',
                        'is_active': True
                    }
                }
                mock_dynamodb = MagicMock()
                mock_dynamodb.Table.return_value = mock_table
                mock_boto3.resource.return_value = mock_dynamodb

                event = {"ContractTypeId": "service-agreement"}
                context = MagicMock()

                result = self.handler_module.handler(event, context)

                # Verify the function returns the original event
                assert result == event

                # Verify DynamoDB was called correctly
                mock_table.get_item.assert_called_once_with(
                    Key={'contract_type_id': 'service-agreement'}
                )

    def test_validation_missing_contract_type_id(self):
        """Test validation with missing ContractTypeId"""
        with patch.dict('os.environ', {'CONTRACT_TYPES_TABLE': 'test-contract-types-table'}):
            event = {}  # Missing ContractTypeId
            context = MagicMock()

            with pytest.raises(ValueError, match="ContractTypeId is required"):
                self.handler_module.handler(event, context)

    def test_validation_contract_type_not_found(self):
        """Test validation with non-existent contract type"""
        with patch.dict('os.environ', {'CONTRACT_TYPES_TABLE': 'test-contract-types-table'}):
            with patch.object(self.handler_module, 'boto3') as mock_boto3:
                # Mock DynamoDB table - return empty response
                mock_table = MagicMock()
                mock_table.get_item.return_value = {}  # No Item found
                mock_dynamodb = MagicMock()
                mock_dynamodb.Table.return_value = mock_table
                mock_boto3.resource.return_value = mock_dynamodb

                event = {"ContractTypeId": "non-existent-type"}
                context = MagicMock()

                with pytest.raises(ValueError, match="Contract type 'non-existent-type' not found"):
                    self.handler_module.handler(event, context)

    def test_validation_inactive_contract_type(self):
        """Test validation with inactive contract type"""
        with patch.dict('os.environ', {'CONTRACT_TYPES_TABLE': 'test-contract-types-table'}):
            with patch.object(self.handler_module, 'boto3') as mock_boto3:
                # Mock DynamoDB table - return inactive contract type
                mock_table = MagicMock()
                mock_table.get_item.return_value = {
                    'Item': {
                        'contract_type_id': 'inactive-type',
                        'name': 'Inactive Contract',
                        'is_active': False
                    }
                }
                mock_dynamodb = MagicMock()
                mock_dynamodb.Table.return_value = mock_table
                mock_boto3.resource.return_value = mock_dynamodb

                event = {"ContractTypeId": "inactive-type"}
                context = MagicMock()

                with pytest.raises(ValueError, match="Contract type 'inactive-type' is not active"):
                    self.handler_module.handler(event, context)