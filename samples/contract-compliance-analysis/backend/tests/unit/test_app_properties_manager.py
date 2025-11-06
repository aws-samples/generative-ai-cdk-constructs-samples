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
from unittest.mock import patch
from aws_lambda_powertools.utilities.parameters.exceptions import GetParameterError

# Import the class under test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'stack', 'lambda', 'common_layer'))
from app_properties_manager import AppPropertiesManager


class TestAppPropertiesManager:
    """Test cases for AppPropertiesManager class - Parameter Store functionality only"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.manager = AppPropertiesManager(cache_ttl=30)

    @patch('app_properties_manager.get_parameter')
    def test_get_parameter_task_specific_found(self, mock_get_parameter):
        """Test get_parameter when task-specific parameter is found"""
        mock_get_parameter.return_value = "task-specific-value"

        result = self.manager.get_parameter('TestParam', task_name='TestTask')

        mock_get_parameter.assert_called_once_with('/ContractAnalysis/TestTask/TestParam', max_age=30)
        assert result == "task-specific-value"

    @patch('app_properties_manager.get_parameter')
    def test_get_parameter_global_fallback(self, mock_get_parameter):
        """Test get_parameter falls back to global parameter when task-specific not found"""
        # First call (task-specific) raises exception, second call (global) succeeds
        mock_get_parameter.side_effect = [
            GetParameterError("ParameterNotFound"),
            "global-value"
        ]

        result = self.manager.get_parameter('TestParam', task_name='TestTask')

        assert result == "global-value"
        assert mock_get_parameter.call_count == 2

    @patch('app_properties_manager.get_parameter')
    def test_get_parameter_default_fallback(self, mock_get_parameter):
        """Test get_parameter uses default when no parameters found"""
        mock_get_parameter.side_effect = GetParameterError("ParameterNotFound")

        result = self.manager.get_parameter('TestParam', task_name='TestTask', default='default-value')

        assert result == "default-value"

    @patch('app_properties_manager.get_parameter')
    def test_get_parameter_no_task_name(self, mock_get_parameter):
        """Test get_parameter without task_name only tries global parameter"""
        mock_get_parameter.return_value = "global-value"

        result = self.manager.get_parameter('TestParam')

        mock_get_parameter.assert_called_once_with('/ContractAnalysis/TestParam', max_age=30)
        assert result == "global-value"

    @patch('app_properties_manager.get_parameter')
    def test_get_parameter_not_found_no_default(self, mock_get_parameter):
        """Test get_parameter raises ValueError when parameter not found and no default"""
        mock_get_parameter.side_effect = GetParameterError("ParameterNotFound")

        with pytest.raises(ValueError, match="Parameter 'TestParam' not found in Parameter Store"):
            self.manager.get_parameter('TestParam')
