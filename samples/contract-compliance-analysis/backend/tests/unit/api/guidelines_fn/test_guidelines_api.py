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

import json
import pytest
from unittest.mock import patch, MagicMock
import base64

# Paths are set up in conftest.py
from model import ContractType, Guideline


class MockLambdaContext:
    """Mock Lambda context for testing"""
    def __init__(self):
        self.function_name = "test-function"
        self.memory_limit_in_mb = 128
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        self.aws_request_id = "test-request-id"


@pytest.fixture
def mock_contract_type():
    """Mock active contract type for testing"""
    return ContractType(
        contract_type_id="service-agreement",
        name="Service Agreement",
        description="Service agreement contracts",
        company_party_type="Customer",
        other_party_type="Service Provider",
        is_active=True,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_guideline():
    """Sample guideline for testing"""
    return Guideline(
        contract_type_id="service-agreement",
        clause_type_id="1",
        name="Payment Terms",
        standard_wording="Payment shall be made within 30 days of invoice date",
        level="high",
        evaluation_questions=[
            "Are payment terms clearly specified?",
            "Is the payment period reasonable?"
        ],
        examples=[
            "Payment due within 30 days",
            "Net 30 payment terms"
        ],
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z"
    )


class TestGetGuidelines:
    """Test GET /guidelines endpoint"""

    def test_get_guidelines_success(self, guidelines_module, mock_contract_type, sample_guideline):
        """Test successful guidelines retrieval"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_ct_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_ct_repo.get_contract_type.return_value = mock_contract_type
            mock_g_repo.list_guidelines.return_value = {
                'guidelines': [sample_guideline],
                'count': 1,
                'last_evaluated_key': None
            }

            # Create API Gateway event
            event = {
                "httpMethod": "GET",
                "path": "/guidelines",
                "queryStringParameters": {
                    "contract_type_id": "service-agreement"
                },
                "headers": {},
                "body": None
            }

            # Test
            response = guidelines_module.app.resolve(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 200
            result = json.loads(response['body'])
            assert 'guidelines' in result
            assert len(result['guidelines']) == 1
            assert result['guidelines'][0]['contractTypeId'] == "service-agreement"
            assert result['guidelines'][0]['clauseTypeId'] == "1"
            assert result['totalCount'] == 1

    def test_get_guidelines_with_filters(self, guidelines_module, mock_contract_type, sample_guideline):
        """Test guidelines retrieval with search and level filters"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_ct_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_ct_repo.get_contract_type.return_value = mock_contract_type
            mock_g_repo.list_guidelines.return_value = {
                'guidelines': [sample_guideline],
                'count': 1,
                'last_evaluated_key': None
            }

            # Create API Gateway event with filters
            event = {
                "httpMethod": "GET",
                "path": "/guidelines",
                "queryStringParameters": {
                    "contract_type_id": "service-agreement",
                    "search": "payment",
                    "level": "high",
                    "limit": "25"
                },
                "headers": {},
                "body": None
            }

            # Test
            response = guidelines_module.app.resolve(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 200
            result = json.loads(response['body'])
            assert len(result['guidelines']) == 1

            # Verify repository calls with filters
            mock_g_repo.list_guidelines.assert_called_once_with(
                contract_type_id="service-agreement",
                search="payment",
                level="high",
                limit=25,
                last_evaluated_key=None
            )

    def test_get_guidelines_invalid_contract_type(self, guidelines_module):
        """Test guidelines retrieval with invalid contract type"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_ct_repo:
            mock_ct_repo.get_contract_type.return_value = None
            mock_ct_repo.get_contract_types.return_value = [
                ContractType(
                    contract_type_id="valid-type",
                    name="Valid Type",
                    description="Valid contract type",
                    company_party_type="Customer",
                    other_party_type="Provider",
                    is_active=True,
                    created_at="2024-01-01T00:00:00Z",
                    updated_at="2024-01-01T00:00:00Z"
                )
            ]

            # Create API Gateway event
            event = {
                "httpMethod": "GET",
                "path": "/guidelines",
                "queryStringParameters": {
                    "contract_type_id": "invalid-type"
                },
                "headers": {},
                "body": None
            }

            # Test
            response = guidelines_module.app.resolve(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 400
            result = json.loads(response['body'])
            assert "Invalid contract type 'invalid-type'" in result['message']
            assert "valid-type" in result['message']

    def test_get_guidelines_invalid_limit(self, guidelines_module, mock_contract_type):
        """Test guidelines retrieval with invalid limit parameter"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_ct_repo:
            mock_ct_repo.get_contract_type.return_value = mock_contract_type

            # Test with limit too high
            event = {
                "httpMethod": "GET",
                "path": "/guidelines",
                "queryStringParameters": {
                    "contract_type_id": "service-agreement",
                    "limit": "101"
                },
                "headers": {},
                "body": None
            }

            response = guidelines_module.app.resolve(event, MockLambdaContext())
            assert response['statusCode'] == 400
            result = json.loads(response['body'])
            assert "Limit must be between 1 and 100" in result['message']

    def test_get_guidelines_with_pagination(self, guidelines_module, mock_contract_type, sample_guideline):
        """Test guidelines retrieval with pagination"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_ct_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_ct_repo.get_contract_type.return_value = mock_contract_type

            # Mock pagination key
            last_key = {"contract_type_id": "service-agreement", "clause_type_id": "1"}
            encoded_key = base64.b64encode(json.dumps(last_key).encode('utf-8')).decode('utf-8')

            mock_g_repo.list_guidelines.return_value = {
                'guidelines': [sample_guideline],
                'last_evaluated_key': encoded_key,
                'count': 1
            }

            # Create API Gateway event with pagination
            event = {
                "httpMethod": "GET",
                "path": "/guidelines",
                "queryStringParameters": {
                    "contract_type_id": "service-agreement",
                    "last_evaluated_key": encoded_key
                },
                "headers": {},
                "body": None
            }

            # Test
            response = guidelines_module.app.resolve(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 200
            result = json.loads(response['body'])
            assert 'lastEvaluatedKey' in result
            assert result['lastEvaluatedKey'] is not None


class TestGetGuideline:
    """Test GET /guidelines/{contract_type_id}/{clause_type_id} endpoint"""

    def test_get_guideline_success(self, guidelines_module, mock_contract_type, sample_guideline):
        """Test successful guideline retrieval"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_g_repo.get_guideline.return_value = sample_guideline

            # Create API Gateway event
            event = {
                "httpMethod": "GET",
                "path": "/guidelines/service-agreement/1",
                "pathParameters": {
                    "contract_type_id": "service-agreement",
                    "clause_type_id": "1"
                },
                "headers": {},
                "body": None,
                "requestContext": {
                    "httpMethod": "GET",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 200
            result = json.loads(response['body'])
            assert result['contractTypeId'] == "service-agreement"
            assert result['clauseTypeId'] == "1"
            assert result['name'] == "Payment Terms"

    def test_get_guideline_not_found(self, guidelines_module):
        """Test guideline retrieval when guideline doesn't exist"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_g_repo.get_guideline.return_value = None

            # Create API Gateway event
            event = {
                "httpMethod": "GET",
                "path": "/guidelines/service-agreement/999",
                "pathParameters": {
                    "contract_type_id": "service-agreement",
                    "clause_type_id": "999"
                },
                "headers": {},
                "body": None,
                "requestContext": {
                    "httpMethod": "GET",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 404
            result = json.loads(response['body'])
            assert "Guideline not found" in result['message']

    def test_get_guideline_invalid_contract_type(self, guidelines_module):
        """Test guideline retrieval with invalid contract type"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            mock_g_repo.get_guideline.return_value = None

            # Create API Gateway event
            event = {
                "httpMethod": "GET",
                "path": "/guidelines/invalid-type/1",
                "pathParameters": {
                    "contract_type_id": "invalid-type",
                    "clause_type_id": "1"
                },
                "headers": {},
                "body": None,
                "requestContext": {
                    "httpMethod": "GET",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 404
            result = json.loads(response['body'])
            assert "Guideline not found" in result['message']


class TestCreateGuideline:
    """Test POST /guidelines endpoint"""

    def test_create_guideline_success(self, guidelines_module, mock_contract_type, sample_guideline):
        """Test successful guideline creation"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_ct_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_ct_repo.get_contract_type.return_value = mock_contract_type
            mock_g_repo.create_guideline.return_value = sample_guideline

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "contractTypeId": "service-agreement",
                    "name": "Payment Terms",
                    "standardWording": "Payment shall be made within 30 days",
                    "level": "high",
                    "evaluationQuestions": ["Are payment terms clear?"],
                    "examples": ["Net 30 terms"]
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 200
            result = json.loads(response['body'])
            assert result['contractTypeId'] == "service-agreement"
            assert result['clauseTypeId'] == "1"
            assert result['name'] == "Payment Terms"

    def test_create_guideline_invalid_contract_type(self, guidelines_module):
        """Test guideline creation with invalid contract type"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_ct_repo:
            mock_ct_repo.get_contract_type.return_value = None
            mock_ct_repo.get_contract_types.return_value = []

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "contractTypeId": "invalid-type",
                    "name": "Payment Terms",
                    "standardWording": "Payment shall be made within 30 days",
                    "level": "high",
                    "evaluationQuestions": ["Are payment terms clear?"]
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 400
            result = json.loads(response['body'])
            assert "Contract type 'invalid-type' not found" in result['message']

    def test_create_guideline_duplicate(self, guidelines_module, mock_contract_type):
        """Test guideline creation with duplicate clause_type_id"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_ct_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_ct_repo.get_contract_type.return_value = mock_contract_type
            mock_g_repo.create_guideline.side_effect = Exception("already exists")

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "contractTypeId": "service-agreement",
                    "name": "Payment Terms",
                    "standardWording": "Payment shall be made within 30 days",
                    "level": "high",
                    "evaluationQuestions": ["Are payment terms clear?"]
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 400

    def test_create_guideline_validation_error(self, guidelines_module, mock_contract_type):
        """Test guideline creation with validation errors"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_ct_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_ct_repo.get_contract_type.return_value = mock_contract_type
            mock_g_repo.create_guideline.side_effect = ValueError("Invalid clause type ID")

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "contractTypeId": "service-agreement",
                    "name": "Payment Terms",
                    "standardWording": "Payment shall be made within 30 days",
                    "level": "high",
                    "evaluationQuestions": ["Are payment terms clear?"]
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 400
            result = json.loads(response['body'])
            assert "Invalid clause type ID" in result['message']


class TestUpdateGuideline:
    """Test PUT /guidelines/{contract_type_id}/{clause_type_id} endpoint"""

    def test_update_guideline_success(self, guidelines_module, sample_guideline):
        """Test successful guideline update"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_g_repo.get_guideline.return_value = sample_guideline

            updated_guideline = sample_guideline.model_copy()
            updated_guideline.name = "Updated Payment Terms"
            mock_g_repo.update_guideline.return_value = updated_guideline

            # Create API Gateway event
            event = {
                "httpMethod": "PUT",
                "path": "/guidelines/service-agreement/1",
                "pathParameters": {
                    "contract_type_id": "service-agreement",
                    "clause_type_id": "1"
                },
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "name": "Updated Payment Terms",
                    "level": "medium"
                }),
                "requestContext": {
                    "httpMethod": "PUT",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 200
            result = json.loads(response['body'])
            assert result['name'] == "Updated Payment Terms"

    def test_update_guideline_not_found(self, guidelines_module):
        """Test guideline update when guideline doesn't exist"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_g_repo.get_guideline.return_value = None

            # Create API Gateway event
            event = {
                "httpMethod": "PUT",
                "path": "/guidelines/service-agreement/999",
                "pathParameters": {
                    "contract_type_id": "service-agreement",
                    "clause_type_id": "999"
                },
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"name": "Updated Name"}),
                "requestContext": {
                    "httpMethod": "PUT",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 404
            result = json.loads(response['body'])
            assert "Guideline not found" in result['message']

    def test_update_guideline_no_changes(self, guidelines_module, sample_guideline):
        """Test guideline update with no changes"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_g_repo.get_guideline.return_value = sample_guideline
            mock_g_repo.update_guideline.return_value = sample_guideline

            # Create API Gateway event
            event = {
                "httpMethod": "PUT",
                "path": "/guidelines/service-agreement/1",
                "pathParameters": {
                    "contract_type_id": "service-agreement",
                    "clause_type_id": "1"
                },
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({}),
                "requestContext": {
                    "httpMethod": "PUT",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 200
            result = json.loads(response['body'])
            assert result['name'] == sample_guideline.name

    def test_update_guideline_validation_error(self, guidelines_module, sample_guideline):
        """Test guideline update with validation errors"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_g_repo.get_guideline.return_value = sample_guideline
            mock_g_repo.update_guideline.side_effect = ValueError("Invalid data")

            # Create API Gateway event
            event = {
                "httpMethod": "PUT",
                "path": "/guidelines/service-agreement/1",
                "pathParameters": {
                    "contract_type_id": "service-agreement",
                    "clause_type_id": "1"
                },
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"name": "Valid Name"}),
                "requestContext": {
                    "httpMethod": "PUT",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 400
            result = json.loads(response['body'])
            assert "Invalid data" in result['message']


class TestDeleteGuideline:
    """Test DELETE /guidelines/{contract_type_id}/{clause_type_id} endpoint"""

    def test_delete_guideline_success(self, guidelines_module):
        """Test successful guideline deletion"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_g_repo.delete_guideline.return_value = True

            # Create API Gateway event
            event = {
                "httpMethod": "DELETE",
                "path": "/guidelines/service-agreement/1",
                "pathParameters": {
                    "contract_type_id": "service-agreement",
                    "clause_type_id": "1"
                },
                "headers": {},
                "body": None,
                "requestContext": {
                    "httpMethod": "DELETE",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 200
            result = json.loads(response['body'])
            assert "deleted successfully" in result['message']

    def test_delete_guideline_not_found(self, guidelines_module):
        """Test guideline deletion when guideline doesn't exist"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_g_repo.delete_guideline.return_value = False

            # Create API Gateway event
            event = {
                "httpMethod": "DELETE",
                "path": "/guidelines/service-agreement/999",
                "pathParameters": {
                    "contract_type_id": "service-agreement",
                    "clause_type_id": "999"
                },
                "headers": {},
                "body": None,
                "requestContext": {
                    "httpMethod": "DELETE",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 404
            result = json.loads(response['body'])
            assert "Guideline not found" in result['message']

    def test_delete_guideline_invalid_contract_type(self, guidelines_module):
        """Test guideline deletion with invalid contract type"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            mock_g_repo.delete_guideline.side_effect = Exception("Database error")

            # Create API Gateway event
            event = {
                "httpMethod": "DELETE",
                "path": "/guidelines/invalid-type/1",
                "pathParameters": {
                    "contract_type_id": "invalid-type",
                    "clause_type_id": "1"
                },
                "headers": {},
                "body": None,
                "requestContext": {
                    "httpMethod": "DELETE",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 400

    def test_delete_guideline_repository_error(self, guidelines_module):
        """Test guideline deletion with repository error"""
        with patch.object(guidelines_module, 'guidelines_repository') as mock_g_repo:

            # Setup mocks
            mock_g_repo.delete_guideline.side_effect = Exception("Database error")

            # Create API Gateway event
            event = {
                "httpMethod": "DELETE",
                "path": "/guidelines/service-agreement/1",
                "pathParameters": {
                    "contract_type_id": "service-agreement",
                    "clause_type_id": "1"
                },
                "headers": {},
                "body": None,
                "requestContext": {
                    "httpMethod": "DELETE",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}"
                }
            }

            # Test
            response = guidelines_module.handler(event, MockLambdaContext())

            # Assertions
            assert response['statusCode'] == 400
            result = json.loads(response['body'])
            assert "Failed to delete guideline" in result['message']
