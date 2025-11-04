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
import sys
import os
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

# Add path for imports
lambda_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'check_legislation', 'sfn', 'check_legislation', 'calculate_legislation_compliance_fn')
if lambda_path not in sys.path:
    sys.path.insert(0, lambda_path)


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB resource"""
    with patch('index.dynamodb') as mock_db:
        yield mock_db


@pytest.fixture
def mock_context():
    """Mock Lambda context"""
    return SimpleNamespace(
        aws_request_id="test-request-id",
        function_name="test-function",
        memory_limit_in_mb=128,
        invoked_function_arn="arn:aws:lambda:us-east-1:123456789012:function:test-function"
    )


def test_all_clauses_compliant(mock_dynamodb, mock_context):
    """Test when all clauses are compliant with legislation"""
    with patch.dict('os.environ', {'JOBS_TABLE': 'JobsTable', 'CLAUSES_TABLE': 'ClausesTable'}):
        from index import lambda_handler
        
        # Mock tables
        mock_clauses_table = MagicMock()
        mock_jobs_table = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: mock_clauses_table if 'Clauses' in name else mock_jobs_table
        
        # Mock clauses query response - all compliant
        mock_clauses_table.query.return_value = {
            'Items': [
                {
                    'job_id': 'test-job',
                    'clause_number': 1,
                    'additional_checks': {
                        'legislation_check': {'compliant': True}
                    }
                },
                {
                    'job_id': 'test-job',
                    'clause_number': 2,
                    'additional_checks': {
                        'legislation_check': {'compliant': True}
                    }
                }
            ]
        }
        
        event = {
            'JobId': 'test-job',
            'ClausesTableName': 'ClausesTable'
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['JobId'] == 'test-job'
        assert result['LegislationCompliant'] == True
        mock_jobs_table.update_item.assert_called_once()


def test_one_clause_non_compliant(mock_dynamodb, mock_context):
    """Test when one clause is non-compliant with legislation"""
    with patch.dict('os.environ', {'JOBS_TABLE': 'JobsTable', 'CLAUSES_TABLE': 'ClausesTable'}):
        from index import lambda_handler
        
        mock_clauses_table = MagicMock()
        mock_jobs_table = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: mock_clauses_table if 'Clauses' in name else mock_jobs_table
        
        # Mock clauses query response - one non-compliant
        mock_clauses_table.query.return_value = {
            'Items': [
                {
                    'job_id': 'test-job',
                    'clause_number': 1,
                    'additional_checks': {
                        'legislation_check': {'compliant': True}
                    }
                },
                {
                    'job_id': 'test-job',
                    'clause_number': 2,
                    'additional_checks': {
                        'legislation_check': {'compliant': False}
                    }
                }
            ]
        }
        
        event = {
            'JobId': 'test-job',
            'ClausesTableName': 'ClausesTable'
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['JobId'] == 'test-job'
        assert result['LegislationCompliant'] == False


def test_no_legislation_checks(mock_dynamodb, mock_context):
    """Test when no clauses have legislation checks"""
    with patch.dict('os.environ', {'JOBS_TABLE': 'JobsTable', 'CLAUSES_TABLE': 'ClausesTable'}):
        from index import lambda_handler
        
        mock_clauses_table = MagicMock()
        mock_jobs_table = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: mock_clauses_table if 'Clauses' in name else mock_jobs_table
        
        # Mock clauses query response - no legislation checks
        mock_clauses_table.query.return_value = {
            'Items': [
                {
                    'job_id': 'test-job',
                    'clause_number': 1,
                    'additional_checks': {}
                },
                {
                    'job_id': 'test-job',
                    'clause_number': 2,
                    'additional_checks': {}
                }
            ]
        }
        
        event = {
            'JobId': 'test-job',
            'ClausesTableName': 'ClausesTable'
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['JobId'] == 'test-job'
        assert result['LegislationCompliant'] == True


def test_empty_clauses(mock_dynamodb, mock_context):
    """Test when there are no clauses"""
    with patch.dict('os.environ', {'JOBS_TABLE': 'JobsTable', 'CLAUSES_TABLE': 'ClausesTable'}):
        from index import lambda_handler
        
        mock_clauses_table = MagicMock()
        mock_jobs_table = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: mock_clauses_table if 'Clauses' in name else mock_jobs_table
        
        # Mock clauses query response - empty
        mock_clauses_table.query.return_value = {'Items': []}
        
        event = {
            'JobId': 'test-job',
            'ClausesTableName': 'ClausesTable'
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['JobId'] == 'test-job'
        assert result['LegislationCompliant'] == True


def test_dynamodb_update_called_correctly(mock_dynamodb, mock_context):
    """Test that DynamoDB update is called with correct parameters"""
    with patch.dict('os.environ', {'JOBS_TABLE': 'JobsTable', 'CLAUSES_TABLE': 'ClausesTable'}):
        from index import lambda_handler
        
        mock_clauses_table = MagicMock()
        mock_jobs_table = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: mock_clauses_table if 'Clauses' in name else mock_jobs_table
        
        mock_clauses_table.query.return_value = {
            'Items': [
                {
                    'job_id': 'test-job',
                    'clause_number': 1,
                    'additional_checks': {
                        'legislation_check': {'compliant': True}
                    }
                }
            ]
        }
        
        event = {
            'JobId': 'test-job',
            'ClausesTableName': 'ClausesTable'
        }
        
        lambda_handler(event, mock_context)
        
        # Verify update_item was called with only legislation_compliant
        mock_jobs_table.update_item.assert_called_once_with(
            Key={'id': 'test-job'},
            UpdateExpression='SET legislation_compliant = :compliant',
            ExpressionAttributeValues={':compliant': True}
        )
