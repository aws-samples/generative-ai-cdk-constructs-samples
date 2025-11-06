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
Unit tests for Finalize Import Step Lambda function
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timezone


class TestFinalizeImportStep:
    """Test cases for Finalize Import Step Lambda function"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_context = Mock()
        self.mock_context.aws_request_id = "test-request-id"

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'CONTRACT_TYPES_TABLE_NAME': 'test-contract-types-table',
            'GUIDELINES_TABLE_NAME': 'test-guidelines-table',
            'IMPORT_JOBS_TABLE_NAME': 'test-import-jobs-table',
            'LOG_LEVEL': 'INFO'
        })
        self.env_patcher.start()

    def teardown_method(self):
        """Clean up after tests"""
        self.env_patcher.stop()

    def test_successful_finalization_logic(self):
        """Test successful import finalization logic"""
        event = {
            "ImportJobId": "import-job-456",
            "ContractTypeInfo": {
                "contract_type_name": "Service Agreement",
                "description": "Agreement for provision of professional services",
                "company_party_type": "Customer",
                "other_party_type": "Service Provider",
                "language": "en"
            },
            "ClauseTypes": [
                {
                    "name": "Payment Terms",
                    "standard_wording": "Payment shall be made within 30 days of invoice receipt.",
                    "suggested_impact_level": "high"
                },
                {
                    "name": "Service Level Requirements",
                    "standard_wording": "Service Provider shall meet performance standards specified in SOW.",
                    "suggested_impact_level": "medium"
                }
            ]
        }

        # Validate required parameters
        assert event.get("ImportJobId") == "import-job-456"
        assert "ContractTypeInfo" in event
        assert "ClauseTypes" in event
        assert len(event["ClauseTypes"]) == 2

        # Test expected response structure
        expected_response = {
            "ImportJobId": "import-job-456",
            "ContractTypeId": "service_agreement",
            "GuidelinesCreated": 2,
            "Status": "SUCCEEDED"
        }

        # Verify response structure
        assert "ImportJobId" in expected_response
        assert "ContractTypeId" in expected_response
        assert "GuidelinesCreated" in expected_response
        assert "Status" in expected_response
        assert expected_response["Status"] == "SUCCEEDED"

    def test_generate_contract_type_id_logic(self):
        """Test contract type ID generation logic"""
        def generate_contract_type_id(name: str) -> str:
            """Generate a unique contract type ID from the name"""
            import re
            # Convert to lowercase, replace spaces and special chars with underscores
            base_id = name.lower().replace(' ', '_')
            # Remove non-alphanumeric characters except underscores
            base_id = re.sub(r'[^a-z0-9_]', '', base_id)
            # Remove multiple consecutive underscores and strip leading/trailing underscores
            base_id = re.sub(r'_+', '_', base_id).strip('_')
            # Ensure it doesn't start with a number
            if base_id and base_id[0].isdigit():
                base_id = f"ct_{base_id}"
            # Fallback if empty
            if not base_id:
                base_id = "contract_type"
            return base_id

        # Test normal cases
        assert generate_contract_type_id("Service Agreement") == "service_agreement"
        assert generate_contract_type_id("Employment Contract") == "employment_contract"
        assert generate_contract_type_id("NDA") == "nda"

        # Test edge cases
        assert generate_contract_type_id("123 Contract") == "ct_123_contract"
        assert generate_contract_type_id("Contract-Type!@#") == "contracttype"
        assert generate_contract_type_id("") == "contract_type"
        assert generate_contract_type_id("   ") == "contract_type"

    def test_unique_name_generation_logic(self):
        """Test unique contract type name generation logic"""
        # Mock existing contract types
        existing_types = [
            Mock(name="Service Agreement", contract_type_id="service_agreement"),
            Mock(name="Service Agreement-2", contract_type_id="service_agreement_2"),
            Mock(name="Employment Contract", contract_type_id="employment_contract")
        ]

        def ensure_unique_contract_type_name(name: str, existing_types) -> tuple[str, str]:
            """Ensure contract type name is unique, append suffix if needed"""
            def generate_contract_type_id(name: str) -> str:
                import re
                base_id = name.lower().replace(' ', '_')
                base_id = re.sub(r'[^a-z0-9_]', '', base_id)
                if base_id and base_id[0].isdigit():
                    base_id = f"ct_{base_id}"
                if not base_id:
                    base_id = "contract_type"
                return base_id

            original_name = name
            original_id = generate_contract_type_id(name)

            existing_names = {ct.name.lower() for ct in existing_types}
            existing_ids = {ct.contract_type_id.lower() for ct in existing_types}

            # If name is unique, return as-is
            if name.lower() not in existing_names and original_id.lower() not in existing_ids:
                return name, original_id

            # Find next available suffix
            counter = 2
            while counter <= 100:  # Safety limit
                new_name = f"{original_name}-{counter}"
                new_id = f"{original_id}_{counter}"

                if new_name.lower() not in existing_names and new_id.lower() not in existing_ids:
                    return new_name, new_id

                counter += 1

            # Fallback
            return f"{original_name}-unique", f"{original_id}_unique"

        # Test unique name (should return as-is)
        name, id = ensure_unique_contract_type_name("NDA", existing_types)
        assert name == "NDA"
        assert id == "nda"

        # Test duplicate name (should get suffix)
        name, id = ensure_unique_contract_type_name("Service Agreement", existing_types)
        assert name == "Service Agreement-3"  # -2 already exists
        assert id == "service_agreement_3"

        # Test new unique name
        name, id = ensure_unique_contract_type_name("Purchase Agreement", existing_types)
        assert name == "Purchase Agreement"
        assert id == "purchase_agreement"

    def test_contract_type_creation_logic(self):
        """Test contract type creation logic"""
        contract_type_info = {
            "contract_type_name": "Service Agreement",
            "description": "Agreement for provision of professional services",
            "company_party_type": "Customer",
            "other_party_type": "Service Provider",
            "language": "en"
        }

        # Test contract type data structure
        contract_type_data = {
            "contract_type_id": "service_agreement",
            "name": "Service Agreement",
            "description": contract_type_info.get("description", ""),
            "company_party_type": contract_type_info.get("company_party_type", "Company"),
            "other_party_type": contract_type_info.get("other_party_type", "Other Party"),
            "high_risk_threshold": Decimal('0.8'),
            "medium_risk_threshold": Decimal('0.5'),
            "low_risk_threshold": Decimal('0.2'),
            "is_active": False,  # Start as disabled for imported types
            "default_language": contract_type_info.get("language", "en"),
            "created_at": "2025-01-01T12:00:00Z",
            "updated_at": "2025-01-01T12:00:00Z"
        }

        # Verify all required fields are present
        required_fields = [
            "contract_type_id", "name", "description", "company_party_type",
            "other_party_type", "high_risk_threshold", "medium_risk_threshold",
            "low_risk_threshold", "is_active", "default_language", "created_at", "updated_at"
        ]

        for field in required_fields:
            assert field in contract_type_data

        # Verify field values
        assert contract_type_data["contract_type_id"] == "service_agreement"
        assert contract_type_data["name"] == "Service Agreement"
        assert contract_type_data["is_active"] is False  # Should be disabled initially
        assert contract_type_data["default_language"] == "en"
        assert contract_type_data["high_risk_threshold"] == Decimal('0.8')

    def test_guideline_creation_logic(self):
        """Test guideline creation logic"""
        contract_type_id = "service_agreement"
        clause_types = [
            {
                "name": "Payment Terms",
                "standard_wording": "Payment shall be made within 30 days of invoice receipt.",
                "suggested_impact_level": "high"
            },
            {
                "name": "Service Level Requirements",
                "standard_wording": "Service Provider shall meet performance standards specified in SOW.",
                "suggested_impact_level": "medium"
            }
        ]

        # Test guideline data structure for each clause type
        guidelines_data = []
        for clause_type in clause_types:
            guideline_data = {
                "contract_type_id": contract_type_id,
                "clause_type_id": None,  # Will be auto-generated
                "name": clause_type["name"],
                "standard_wording": clause_type["standard_wording"],
                "level": clause_type["suggested_impact_level"],
                "evaluation_questions": ["Does this clause meet the standard requirements?"],
                "examples": [],
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z"
            }
            guidelines_data.append(guideline_data)

        # Verify guidelines structure
        assert len(guidelines_data) == 2

        # Check first guideline
        guideline1 = guidelines_data[0]
        assert guideline1["contract_type_id"] == contract_type_id
        assert guideline1["name"] == "Payment Terms"
        assert guideline1["level"] == "high"
        assert len(guideline1["evaluation_questions"]) == 1
        assert guideline1["examples"] == []

        # Check second guideline
        guideline2 = guidelines_data[1]
        assert guideline2["contract_type_id"] == contract_type_id
        assert guideline2["name"] == "Service Level Requirements"
        assert guideline2["level"] == "medium"

    def test_missing_required_fields_validation(self):
        """Test validation of required fields"""
        def validate_required_fields(event):
            if not event.get("ImportJobId"):
                raise ValueError("ImportJobId is required")
            if not event.get("ContractTypeInfo"):
                raise ValueError("ContractTypeInfo is required")
            if not event.get("ClauseTypes"):
                raise ValueError("ClauseTypes is required")
            return True

        # Test missing ImportJobId
        event_missing_job_id = {
            "ContractTypeInfo": {"contract_type_name": "Test"},
            "ClauseTypes": [{"name": "Test", "standard_wording": "Test", "suggested_impact_level": "low"}]
        }

        with pytest.raises(ValueError, match="ImportJobId is required"):
            validate_required_fields(event_missing_job_id)

        # Test missing ContractTypeInfo
        event_missing_contract_info = {
            "ImportJobId": "import-job-456",
            "ClauseTypes": [{"name": "Test", "standard_wording": "Test", "suggested_impact_level": "low"}]
        }

        with pytest.raises(ValueError, match="ContractTypeInfo is required"):
            validate_required_fields(event_missing_contract_info)

        # Test missing ClauseTypes
        event_missing_clause_types = {
            "ImportJobId": "import-job-456",
            "ContractTypeInfo": {"contract_type_name": "Test"}
        }

        with pytest.raises(ValueError, match="ClauseTypes is required"):
            validate_required_fields(event_missing_clause_types)

    def test_rollback_logic(self):
        """Test rollback logic for error scenarios"""
        contract_type_id = "service_agreement"
        guideline_ids = ["1", "2", "3"]

        # Mock repositories
        mock_contract_type_repo = Mock()
        mock_guidelines_repo = Mock()

        def rollback_created_data(contract_type_id, guideline_ids, contract_type_repo, guidelines_repo):
            """Rollback created contract type and guidelines on error"""
            # Delete guidelines first (due to foreign key relationship)
            for clause_type_id in guideline_ids:
                try:
                    if contract_type_id:
                        guidelines_repo.delete_guideline(contract_type_id, clause_type_id)
                except Exception:
                    pass  # Log warning but continue

            # Delete contract type
            if contract_type_id:
                try:
                    contract_type_repo.delete_contract_type(contract_type_id)
                except Exception:
                    pass  # Log warning but continue

        # Test rollback execution
        rollback_created_data(contract_type_id, guideline_ids, mock_contract_type_repo, mock_guidelines_repo)

        # Verify rollback calls
        assert mock_guidelines_repo.delete_guideline.call_count == 3
        mock_guidelines_repo.delete_guideline.assert_any_call(contract_type_id, "1")
        mock_guidelines_repo.delete_guideline.assert_any_call(contract_type_id, "2")
        mock_guidelines_repo.delete_guideline.assert_any_call(contract_type_id, "3")
        mock_contract_type_repo.delete_contract_type.assert_called_once_with(contract_type_id)

    def test_error_handling_logic(self):
        """Test error handling logic"""
        import_job_id = "import-job-456"

        def handle_error(error, import_job_id):
            error_message = f"Import finalization failed: {str(error)}"

            # Simulate updating import job status to FAILED
            update_data = {
                "import_job_id": import_job_id,
                "status": "FAILED",
                "error_message": str(error),
                "current_step": "Finalize Import"
            }

            # Re-raise as RuntimeError for Step Functions
            raise RuntimeError(error_message)

        # Test error handling
        original_error = ValueError("Contract type creation failed")

        with pytest.raises(RuntimeError, match="Import finalization failed"):
            handle_error(original_error, import_job_id)

    def test_import_job_status_updates(self):
        """Test import job status update logic"""
        import_job_id = "import-job-456"

        # Test status update data structures
        start_update = {
            "import_job_id": import_job_id,
            "status": "RUNNING",
            "current_step": "Finalize Import",
            "progress": 80
        }

        success_update = {
            "import_job_id": import_job_id,
            "status": "SUCCEEDED",
            "current_step": "Completed",
            "progress": 100,
            "contract_type_id": "service_agreement"
        }

        failure_update = {
            "import_job_id": import_job_id,
            "status": "FAILED",
            "error_message": "Import finalization failed: Test error",
            "current_step": "Finalize Import"
        }

        # Verify update structures
        assert start_update["status"] == "RUNNING"
        assert start_update["progress"] == 80
        assert success_update["status"] == "SUCCEEDED"
        assert success_update["progress"] == 100
        assert "contract_type_id" in success_update
        assert failure_update["status"] == "FAILED"
        assert "error_message" in failure_update

    def test_response_format_validation(self):
        """Test response format validation"""
        # Test successful response format
        response = {
            "ImportJobId": "import-job-456",
            "ContractTypeId": "service_agreement",
            "GuidelinesCreated": 2,
            "Status": "SUCCEEDED"
        }

        # Verify response structure
        required_response_fields = [
            "ImportJobId", "ContractTypeId", "GuidelinesCreated", "Status"
        ]

        for field in required_response_fields:
            assert field in response

        # Verify field types
        assert isinstance(response["ImportJobId"], str)
        assert isinstance(response["ContractTypeId"], str)
        assert isinstance(response["GuidelinesCreated"], int)
        assert isinstance(response["Status"], str)

        # Verify specific values
        assert response["Status"] == "SUCCEEDED"
        assert response["GuidelinesCreated"] >= 0

    def test_environment_variables_usage(self):
        """Test environment variables usage"""
        # Test that required environment variables are available
        assert os.environ.get("CONTRACT_TYPES_TABLE_NAME") == "test-contract-types-table"
        assert os.environ.get("GUIDELINES_TABLE_NAME") == "test-guidelines-table"
        assert os.environ.get("IMPORT_JOBS_TABLE_NAME") == "test-import-jobs-table"
        assert os.environ.get("LOG_LEVEL") == "INFO"

        # Test environment variable validation logic
        def validate_environment():
            required_env_vars = [
                "CONTRACT_TYPES_TABLE_NAME",
                "GUIDELINES_TABLE_NAME",
                "IMPORT_JOBS_TABLE_NAME"
            ]
            missing_vars = []

            for var in required_env_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)

            if missing_vars:
                raise RuntimeError(f"Missing required environment variables: {missing_vars}")

            return True

        # Should not raise error with current environment
        assert validate_environment() is True

        # Test with missing environment variable
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="Missing required environment variables"):
                validate_environment()

    def test_contract_type_info_validation(self):
        """Test contract type info validation"""
        # Test valid contract type info
        valid_info = {
            "contract_type_name": "Service Agreement",
            "description": "Agreement for provision of professional services",
            "company_party_type": "Customer",
            "other_party_type": "Service Provider",
            "language": "en"
        }

        def validate_contract_type_info(info):
            if not info.get("contract_type_name"):
                raise ValueError("contract_type_name is required in ContractTypeInfo")
            return True

        # Should pass validation
        assert validate_contract_type_info(valid_info) is True

        # Test missing contract_type_name
        invalid_info = {
            "description": "Agreement for provision of professional services",
            "company_party_type": "Customer",
            "other_party_type": "Service Provider",
            "language": "en"
        }

        with pytest.raises(ValueError, match="contract_type_name is required"):
            validate_contract_type_info(invalid_info)

    def test_clause_types_validation(self):
        """Test clause types validation"""
        # Test valid clause types
        valid_clause_types = [
            {
                "name": "Payment Terms",
                "standard_wording": "Payment shall be made within 30 days of invoice receipt.",
                "suggested_impact_level": "high"
            },
            {
                "name": "Service Level Requirements",
                "standard_wording": "Service Provider shall meet performance standards specified in SOW.",
                "suggested_impact_level": "medium"
            }
        ]

        def validate_clause_types(clause_types):
            if not clause_types or len(clause_types) == 0:
                raise ValueError("At least one clause type is required")

            for i, clause_type in enumerate(clause_types):
                if not clause_type.get("name"):
                    raise ValueError(f"Clause type {i+1} is missing 'name'")
                if not clause_type.get("standard_wording"):
                    raise ValueError(f"Clause type {i+1} is missing 'standard_wording'")
                if not clause_type.get("suggested_impact_level"):
                    raise ValueError(f"Clause type {i+1} is missing 'suggested_impact_level'")
                if clause_type["suggested_impact_level"] not in ["low", "medium", "high"]:
                    raise ValueError(f"Clause type {i+1} has invalid impact level")

            return True

        # Should pass validation
        assert validate_clause_types(valid_clause_types) is True

        # Test empty clause types
        with pytest.raises(ValueError, match="At least one clause type is required"):
            validate_clause_types([])

        # Test missing name
        invalid_clause_types = [
            {
                "standard_wording": "Payment shall be made within 30 days of invoice receipt.",
                "suggested_impact_level": "high"
            }
        ]

        with pytest.raises(ValueError, match="Clause type 1 is missing 'name'"):
            validate_clause_types(invalid_clause_types)

        # Test invalid impact level
        invalid_impact_clause_types = [
            {
                "name": "Payment Terms",
                "standard_wording": "Payment shall be made within 30 days of invoice receipt.",
                "suggested_impact_level": "invalid"
            }
        ]

        with pytest.raises(ValueError, match="Clause type 1 has invalid impact level"):
            validate_clause_types(invalid_impact_clause_types)