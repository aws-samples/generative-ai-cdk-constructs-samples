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
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

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
def sample_contract_type():
    """Sample contract type for testing"""
    return ContractType(
        contract_type_id="test-contract",
        name="Test Service Agreement",
        description="Test contract type",
        company_party_type="Customer",
        other_party_type="Service Provider",
        high_risk_threshold=0,
        medium_risk_threshold=1,
        low_risk_threshold=3,
        is_active=True,
        default_language="en",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_guideline():
    """Sample guideline for testing"""
    return Guideline(
        contract_type_id="test-contract",
        clause_type_id="1",
        name="Payment Terms",
        standard_wording="Payment shall be made within 30 days of invoice receipt.",
        level="high",
        evaluation_questions=["Does the clause specify payment terms?"],
        examples=["Payment due within 30 days."],
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z"
    )


class TestGenerateQuestionsEndpoint:
    """Test cases for the generate questions endpoint"""

    def test_generate_questions_success(self, guidelines_module, sample_contract_type, sample_guideline):
        """Test successful question generation"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_contract_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_guidelines_repo, \
             patch.object(guidelines_module, 'invoke_llm') as mock_invoke_llm:

            # Setup mocks
            mock_contract_repo.get_contract_type.return_value = sample_contract_type
            mock_guidelines_repo.get_guideline.return_value = sample_guideline

            # Mock LLM response with questions in XML tags
            mock_llm_response = """
            <statements>
            Key statements: Payment timing, Invoice receipt requirement
            </statements>

            <thinking>
            I need to create questions that validate payment timing requirements.
            </thinking>

            <critic_analysis>
            The question should be answerable with Yes when applied to the standard wording.
            </critic_analysis>

            <question_translated>Does the clause specify a payment deadline?</question_translated>
            <question_translated>Does the clause require payment within a specific timeframe?</question_translated>
            <question_translated>Does the clause reference invoice receipt as a trigger?</question_translated>
            """

            mock_invoke_llm.return_value = (mock_llm_response, {}, "stop")

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines/test-contract/1/generate-questions",
                "pathParameters": {
                    "contract_type_id": "test-contract",
                    "clause_type_id": "1"
                },
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "standardWording": "Payment shall be made within 30 days of invoice receipt."
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}/generate-questions"
                }
            }

            # Execute request
            response = guidelines_module.handler(event, MockLambdaContext())

            # Verify response
            assert response['statusCode'] == 200

            body = json.loads(response['body'])
            assert 'questions' in body
            assert len(body['questions']) == 3
            assert "Does the clause specify a payment deadline?" in body['questions']
            assert "Does the clause require payment within a specific timeframe?" in body['questions']
            assert "Does the clause reference invoice receipt as a trigger?" in body['questions']

    def test_generate_questions_contract_type_not_found(self, guidelines_module):
        """Test question generation with non-existent contract type"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_contract_repo:
            # Setup mock
            mock_contract_repo.get_contract_type.return_value = None
            mock_contract_repo.get_contract_types.return_value = []

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines/test-contract/1/generate-questions",
                "pathParameters": {
                    "contract_type_id": "test-contract",
                    "clause_type_id": "1"
                },
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "standardWording": "Payment shall be made within 30 days of invoice receipt."
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}/generate-questions"
                }
            }

            # Execute request
            response = guidelines_module.handler(event, MockLambdaContext())

            # Verify error response
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert "Invalid contract type" in body['message']

    def test_generate_questions_guideline_not_found(self, guidelines_module, sample_contract_type):
        """Test question generation with non-existent guideline"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_contract_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_guidelines_repo:

            # Setup mocks
            mock_contract_repo.get_contract_type.return_value = sample_contract_type
            mock_guidelines_repo.get_guideline.return_value = None

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines/test-contract/1/generate-questions",
                "pathParameters": {
                    "contract_type_id": "test-contract",
                    "clause_type_id": "1"
                },
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "standardWording": "Payment shall be made within 30 days of invoice receipt."
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}/generate-questions"
                }
            }

            # Execute request
            response = guidelines_module.handler(event, MockLambdaContext())

            # Verify error response
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert "Guideline not found" in body['message']

    def test_generate_questions_llm_failure(self, guidelines_module, sample_contract_type, sample_guideline):
        """Test question generation with LLM failure"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_contract_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_guidelines_repo, \
             patch.object(guidelines_module, 'invoke_llm') as mock_invoke_llm:

            # Setup mocks
            mock_contract_repo.get_contract_type.return_value = sample_contract_type
            mock_guidelines_repo.get_guideline.return_value = sample_guideline
            mock_invoke_llm.side_effect = Exception("LLM service unavailable")

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines/test-contract/1/generate-questions",
                "pathParameters": {
                    "contract_type_id": "test-contract",
                    "clause_type_id": "1"
                },
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "standardWording": "Payment shall be made within 30 days of invoice receipt."
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}/generate-questions"
                }
            }

            # Execute request
            response = guidelines_module.handler(event, MockLambdaContext())

            # Verify error response
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert "Question generation failed" in body['message']

    def test_generate_questions_no_questions_generated(self, guidelines_module, sample_contract_type, sample_guideline):
        """Test question generation when no valid questions are generated"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_contract_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_guidelines_repo, \
             patch.object(guidelines_module, 'invoke_llm') as mock_invoke_llm:

            # Setup mocks
            mock_contract_repo.get_contract_type.return_value = sample_contract_type
            mock_guidelines_repo.get_guideline.return_value = sample_guideline

            # Mock LLM response without valid question tags
            mock_llm_response = "No valid questions generated in this response."
            mock_invoke_llm.return_value = (mock_llm_response, {}, "stop")

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines/test-contract/1/generate-questions",
                "pathParameters": {
                    "contract_type_id": "test-contract",
                    "clause_type_id": "1"
                },
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "standardWording": "Payment shall be made within 30 days of invoice receipt."
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}/generate-questions"
                }
            }

            # Execute request
            response = guidelines_module.handler(event, MockLambdaContext())

            # Verify error response
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert "Generation failed" in body['message']

    def test_generate_questions_invalid_request_body(self, guidelines_module):
        """Test question generation with invalid request body"""
        # Create API Gateway event with invalid body
        event = {
            "httpMethod": "POST",
            "path": "/guidelines/test-contract/1/generate-questions",
            "pathParameters": {
                "contract_type_id": "test-contract",
                "clause_type_id": "1"
            },
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "invalidField": "test"
            }),
            "requestContext": {
                "httpMethod": "POST",
                "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}/generate-questions"
            }
        }

        # Execute request
        response = guidelines_module.handler(event, MockLambdaContext())

        # Verify validation error
        assert response['statusCode'] == 422  # Validation error


class TestGenerateExamplesEndpoint:
    """Test cases for the generate examples endpoint"""

    def test_generate_examples_success(self, guidelines_module, sample_contract_type, sample_guideline):
        """Test successful example generation"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_contract_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_guidelines_repo, \
             patch.object(guidelines_module, 'invoke_llm') as mock_invoke_llm:

            # Setup mocks
            mock_contract_repo.get_contract_type.return_value = sample_contract_type
            mock_guidelines_repo.get_guideline.return_value = sample_guideline

            # Mock LLM response with examples in XML tags
            mock_llm_response = """
            <example>Payment is due within thirty (30) days from the date of invoice.</example>
            <example>All invoices must be paid within 30 calendar days of receipt.</example>
            <example>Payment terms: Net 30 days from invoice date.</example>
            """

            mock_invoke_llm.return_value = (mock_llm_response, {}, "stop")

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines/test-contract/1/generate-examples",
                "pathParameters": {
                    "contract_type_id": "test-contract",
                    "clause_type_id": "1"
                },
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "standardWording": "Payment shall be made within 30 days of invoice receipt."
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}/generate-examples"
                }
            }

            # Execute request
            response = guidelines_module.handler(event, MockLambdaContext())

            # Verify response
            assert response['statusCode'] == 200

            body = json.loads(response['body'])
            assert 'examples' in body
            assert len(body['examples']) == 3
            assert "Payment is due within thirty (30) days" in body['examples'][0]
            assert "All invoices must be paid within 30 calendar days" in body['examples'][1]
            assert "Payment terms: Net 30 days" in body['examples'][2]

    def test_generate_examples_insufficient_examples(self, guidelines_module, sample_contract_type, sample_guideline):
        """Test example generation when insufficient examples are generated"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_contract_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_guidelines_repo, \
             patch.object(guidelines_module, 'invoke_llm') as mock_invoke_llm:

            # Setup mocks
            mock_contract_repo.get_contract_type.return_value = sample_contract_type
            mock_guidelines_repo.get_guideline.return_value = sample_guideline

            # Mock LLM response with only one example
            mock_llm_response = """
            <example>Payment is due within thirty (30) days from the date of invoice.</example>
            """

            mock_invoke_llm.return_value = (mock_llm_response, {}, "stop")

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines/test-contract/1/generate-examples",
                "pathParameters": {
                    "contract_type_id": "test-contract",
                    "clause_type_id": "1"
                },
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "standardWording": "Payment shall be made within 30 days of invoice receipt."
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}/generate-examples"
                }
            }

            # Execute request
            response = guidelines_module.handler(event, MockLambdaContext())

            # Verify error response
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert "Generation failed" in body['message']


class TestGenerationEndpointsIntegration:
    """Integration tests for generation endpoints"""

    def test_generation_with_different_languages(self, guidelines_module, sample_guideline):
        """Test generation with different contract languages"""
        # Create contract type with Portuguese language
        pt_contract_type = ContractType(
            contract_type_id="test-contract-pt",
            name="Contrato de Serviço",
            description="Contrato de teste",
            company_party_type="Cliente",
            other_party_type="Prestador de Serviços",
            high_risk_threshold=0,
            medium_risk_threshold=1,
            low_risk_threshold=3,
            is_active=True,
            default_language="pt_BR",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        with patch.object(guidelines_module, 'contract_type_repository') as mock_contract_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_guidelines_repo, \
             patch.object(guidelines_module, 'invoke_llm') as mock_invoke_llm:

            # Setup mocks
            mock_contract_repo.get_contract_type.return_value = pt_contract_type
            mock_guidelines_repo.get_guideline.return_value = sample_guideline

            # Mock LLM response in Portuguese
            mock_llm_response = """
            <question_translated>A cláusula especifica um prazo para pagamento?</question_translated>
            <question_translated>A cláusula exige pagamento dentro de um prazo específico?</question_translated>
            """

            mock_invoke_llm.return_value = (mock_llm_response, {}, "stop")

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines/test-contract-pt/1/generate-questions",
                "pathParameters": {
                    "contract_type_id": "test-contract-pt",
                    "clause_type_id": "1"
                },
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "standardWording": "O pagamento deve ser feito em 30 dias após o recebimento da fatura."
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}/generate-questions"
                }
            }

            # Execute request
            response = guidelines_module.handler(event, MockLambdaContext())

            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body['questions']) == 2

    def test_generation_with_retry_logic(self, guidelines_module, sample_contract_type, sample_guideline):
        """Test that generation handles LLM retry logic properly"""
        with patch.object(guidelines_module, 'contract_type_repository') as mock_contract_repo, \
             patch.object(guidelines_module, 'guidelines_repository') as mock_guidelines_repo, \
             patch.object(guidelines_module, 'invoke_llm') as mock_invoke_llm:

            # Setup mocks
            mock_contract_repo.get_contract_type.return_value = sample_contract_type
            mock_guidelines_repo.get_guideline.return_value = sample_guideline

            # Mock LLM to succeed after retry (invoke_llm handles retries internally)
            mock_llm_response = """
            <question_translated>Does the clause specify payment terms?</question_translated>
            <question_translated>Does the clause include a payment deadline?</question_translated>
            """

            mock_invoke_llm.return_value = (mock_llm_response, {}, "stop")

            # Create API Gateway event
            event = {
                "httpMethod": "POST",
                "path": "/guidelines/test-contract/1/generate-questions",
                "pathParameters": {
                    "contract_type_id": "test-contract",
                    "clause_type_id": "1"
                },
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "standardWording": "Payment shall be made within 30 days of invoice receipt."
                }),
                "requestContext": {
                    "httpMethod": "POST",
                    "resourcePath": "/guidelines/{contract_type_id}/{clause_type_id}/generate-questions"
                }
            }

            # Execute request
            response = guidelines_module.handler(event, MockLambdaContext())

            # Verify successful response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body['questions']) == 2
