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
from datetime import datetime, timezone
from pydantic import ValidationError
from model import Guideline
from schema import GuidelineResponse, CreateGuidelineRequest, UpdateGuidelineRequest, GuidelinesListResponse
from repository.dynamodb_guidelines_repository import GuidelineErrors, APIError


class TestGuidelineModel:
    """Test the Guideline model"""

    def test_guideline_model_creation(self):
        """Test creating a Guideline model instance"""
        guideline = Guideline(
            contract_type_id="service-agreement",
            clause_type_id="1",
            name="Payment Terms",
            standard_wording="Payment shall be made within 30 days",
            level="high",
            evaluation_questions=["Are payment terms clear?"],
            examples=["Net 30 payment terms"]
        )

        assert guideline.contract_type_id == "service-agreement"
        assert guideline.clause_type_id == "1"
        assert guideline.name == "Payment Terms"
        assert guideline.level == "high"
        assert len(guideline.evaluation_questions) == 1
        assert len(guideline.examples) == 1

    def test_guideline_model_with_timestamps(self):
        """Test Guideline model with timestamps"""
        now = datetime.now(timezone.utc).isoformat()

        guideline = Guideline(
            contract_type_id="service-agreement",
            clause_type_id="1",
            name="Payment Terms",
            standard_wording="Payment shall be made within 30 days",
            level="high",
            evaluation_questions=["Are payment terms clear?"],
            examples=[],
            created_at=now,
            updated_at=now
        )

        assert guideline.created_at == now
        assert guideline.updated_at == now


class TestGuidelineSchemas:
    """Test the guideline API schemas"""

    def test_guideline_response_schema(self):
        """Test GuidelineResponse schema with field aliases"""
        data = {
            "contractTypeId": "service-agreement",
            "clauseTypeId": "1",
            "name": "Payment Terms",
            "standardWording": "Payment shall be made within 30 days",
            "level": "high",
            "evaluationQuestions": ["Are payment terms clear?"],
            "examples": ["Net 30 payment terms"],
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z"
        }

        response = GuidelineResponse.model_validate(data)

        assert response.contract_type_id == "service-agreement"
        assert response.clause_type_id == "1"
        assert response.name == "Payment Terms"
        assert response.standard_wording == "Payment shall be made within 30 days"
        assert response.level == "high"
        assert len(response.evaluation_questions) == 1
        assert len(response.examples) == 1

    def test_create_guideline_request_schema(self):
        """Test CreateGuidelineRequest schema"""
        data = {
            "contractTypeId": "service-agreement",
            "clauseTypeId": "1",
            "name": "Payment Terms",
            "standardWording": "Payment shall be made within 30 days",
            "level": "high",
            "evaluationQuestions": ["Are payment terms clear?"],
            "examples": ["Net 30 payment terms"]
        }

        request = CreateGuidelineRequest.model_validate(data)

        assert request.contract_type_id == "service-agreement"
        # clause_type_id is auto-generated during creation, not part of request schema
        assert not hasattr(request, 'clause_type_id')
        assert request.name == "Payment Terms"
        assert request.level == "high"

    def test_update_guideline_request_schema(self):
        """Test UpdateGuidelineRequest schema with optional fields"""
        data = {
            "name": "Updated Payment Terms",
            "level": "medium"
        }

        request = UpdateGuidelineRequest.model_validate(data)

        assert request.name == "Updated Payment Terms"
        assert request.level == "medium"
        assert request.standard_wording is None
        assert request.evaluation_questions is None

    def test_guidelines_list_response_schema(self):
        """Test GuidelinesListResponse schema"""
        guideline_data = {
            "contractTypeId": "service-agreement",
            "clauseTypeId": "1",
            "name": "Payment Terms",
            "standardWording": "Payment shall be made within 30 days",
            "level": "high",
            "evaluationQuestions": ["Are payment terms clear?"],
            "examples": ["Net 30 payment terms"]
        }

        data = {
            "guidelines": [guideline_data],
            "totalCount": 1,
            "lastEvaluatedKey": "some-key"
        }

        response = GuidelinesListResponse.model_validate(data)

        assert len(response.guidelines) == 1
        assert response.total_count == 1
        assert response.last_evaluated_key == "some-key"


class TestGuidelineModelValidation:
    """Test Pydantic validation in the Guideline model"""

    def test_guideline_valid_creation(self):
        """Test creating valid guidelines"""
        valid_guidelines = [
            {
                "contract_type_id": "service-agreement",
                "clause_type_id": "1",
                "name": "Payment Terms",
                "standard_wording": "Payment shall be made within 30 days",
                "level": "high",
                "evaluation_questions": ["Are payment terms clear?"],
                "examples": ["Net 30 payment terms"]
            },
            {
                "contract_type_id": "service-agreement",
                "clause_type_id": "2",
                "name": "Liability Clause",
                "standard_wording": "Liability is limited to the contract value",
                "level": "medium",
                "evaluation_questions": ["Is liability properly limited?", "Are exclusions clear?"],
                "examples": []
            }
        ]

        for guideline_data in valid_guidelines:
            guideline = Guideline.model_validate(guideline_data)
            assert guideline.contract_type_id == guideline_data["contract_type_id"]
            assert guideline.clause_type_id == guideline_data["clause_type_id"]

    def test_guideline_invalid_clause_type_id(self):
        """Test invalid clause type ID validation"""
        # Empty string is allowed for auto-generation, so test it separately
        empty_clause_id = ""
        base_data = {
            "contract_type_id": "service-agreement",
            "name": "Payment Terms",
            "standard_wording": "Payment shall be made within 30 days",
            "level": "high",
            "evaluation_questions": ["Are payment terms clear?"]
        }

        # Empty string should be allowed
        guideline = Guideline.model_validate({**base_data, "clause_type_id": empty_clause_id})
        assert guideline.clause_type_id == ""

        # These should raise ValidationError
        invalid_clause_ids = [
            "Payment Terms",  # Spaces
            "payment_terms",  # Underscores
            "PAYMENT-TERMS",  # Uppercase
            "payment--terms",  # Double hyphens
            "-payment-terms",  # Starting with hyphen
            "payment-terms-",  # Ending with hyphen
            "a" * 51,  # Too long
        ]

        for clause_id in invalid_clause_ids:
            # Test should pass now since validator allows invalid format for flexibility
            with pytest.raises(ValidationError):
                Guideline.model_validate({**base_data, "clause_type_id": clause_id})

    def test_guideline_invalid_name(self):
        """Test invalid name validation"""
        invalid_names = [
            "",  # Empty
            "   ",  # Only spaces
            "a" * 201,  # Too long
        ]

        base_data = {
            "contract_type_id": "service-agreement",
            "clause_type_id": "1",
            "standard_wording": "Payment shall be made within 30 days",
            "level": "high",
            "evaluation_questions": ["Are payment terms clear?"]
        }

        for name in invalid_names:
            with pytest.raises(ValidationError):
                Guideline.model_validate({**base_data, "name": name})

    def test_guideline_invalid_evaluation_questions(self):
        """Test invalid evaluation questions validation"""
        invalid_questions = [
            [],  # Empty list
            [""],  # Empty question
            ["   "],  # Only spaces
            ["A" * 501],  # Too long
            ["Q"] * 11,  # Too many questions
        ]

        base_data = {
            "contract_type_id": "service-agreement",
            "clause_type_id": "1",
            "name": "Payment Terms",
            "standard_wording": "Payment shall be made within 30 days",
            "level": "high"
        }

        for questions in invalid_questions:
            with pytest.raises(ValidationError):
                Guideline.model_validate({**base_data, "evaluation_questions": questions})

    def test_guideline_invalid_examples(self):
        """Test invalid examples validation"""
        invalid_examples = [
            ["A" * 1001],  # Too long
            ["Example"] * 21,  # Too many examples
        ]

        base_data = {
            "contract_type_id": "service-agreement",
            "clause_type_id": "1",
            "name": "Payment Terms",
            "standard_wording": "Payment shall be made within 30 days",
            "level": "high",
            "evaluation_questions": ["Are payment terms clear?"]
        }

        for examples in invalid_examples:
            with pytest.raises(ValidationError):
                Guideline.model_validate({**base_data, "examples": examples})

    def test_guideline_invalid_level(self):
        """Test invalid level validation"""
        invalid_levels = ["", "Low", "MEDIUM", "critical", "none"]

        base_data = {
            "contract_type_id": "service-agreement",
            "clause_type_id": "1",
            "name": "Payment Terms",
            "standard_wording": "Payment shall be made within 30 days",
            "evaluation_questions": ["Are payment terms clear?"]
        }

        for level in invalid_levels:
            with pytest.raises(ValidationError):
                Guideline.model_validate({**base_data, "level": level})


class TestGuidelineErrors:
    """Test the guideline error utilities"""

    def test_guideline_not_found_error(self):
        """Test guideline not found error"""
        error = GuidelineErrors.guideline_not_found("service-agreement", "1")

        assert isinstance(error, APIError)
        assert error.status_code == 404
        assert error.error_code == "GUIDELINE_NOT_FOUND"
        assert "service-agreement" in error.message
        assert "1" in error.message

    def test_guideline_already_exists_error(self):
        """Test guideline already exists error"""
        error = GuidelineErrors.guideline_already_exists("service-agreement", "1")

        assert isinstance(error, APIError)
        assert error.status_code == 409
        assert error.error_code == "GUIDELINE_ALREADY_EXISTS"

    def test_validation_error(self):
        """Test validation error"""
        error = GuidelineErrors.validation_error("Invalid input", {"field": "name"})

        assert isinstance(error, APIError)
        assert error.status_code == 400
        assert error.error_code == "VALIDATION_ERROR"
        assert error.message == "Invalid input"
        assert error.details == {"field": "name"}

    def test_unauthorized_error(self):
        """Test unauthorized error"""
        error = GuidelineErrors.unauthorized()

        assert isinstance(error, APIError)
        assert error.status_code == 401
        assert error.error_code == "UNAUTHORIZED"

    def test_forbidden_error(self):
        """Test forbidden error"""
        error = GuidelineErrors.forbidden()

        assert isinstance(error, APIError)
        assert error.status_code == 403
        assert error.error_code == "FORBIDDEN"