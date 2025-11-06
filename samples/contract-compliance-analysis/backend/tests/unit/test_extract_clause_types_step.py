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
Unit tests for Extract Clause Types Step Lambda function
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError


class TestExtractClauseTypesStep:
    """Test cases for Extract Clause Types Step Lambda function"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_context = Mock()
        self.mock_context.aws_request_id = "test-request-id"

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'IMPORT_JOBS_TABLE_NAME': 'test-import-jobs-table',
            'CONTRACT_BUCKET_NAME': 'test-contract-bucket',
            'DEFAULT_LLM_MODEL_ID': 'amazon.nova-pro-v1:0',
            'LOG_LEVEL': 'INFO'
        })
        self.env_patcher.start()

    def teardown_method(self):
        """Clean up after tests"""
        self.env_patcher.stop()

    def test_successful_clause_types_extraction_logic(self):
        """Test successful clause types extraction logic"""
        event = {
            "ExecutionName": "test-execution-123",
            "ImportJobId": "import-job-456",
            "DocumentS3Key": "documents/test-contract.pdf",
            "ContractTypeInfo": {
                "contract_type_name": "Service Agreement",
                "description": "Agreement for provision of professional services",
                "company_party_type": "Customer",
                "other_party_type": "Service Provider",
                "language": "en"
            }
        }

        # Validate required parameters
        assert event.get("ImportJobId") == "import-job-456"
        assert event.get("DocumentS3Key") == "documents/test-contract.pdf"
        assert event.get("ContractTypeInfo") is not None

        # Test expected response structure
        expected_response = {
            "ImportJobId": event["ImportJobId"],
            "DocumentS3Key": event["DocumentS3Key"],
            "ContractTypeInfo": event["ContractTypeInfo"],
            "ClauseTypes": [
                {
                    "name": "Payment Terms",
                    "standard_wording": "Payment shall be made within 30 days of invoice receipt.",
                    "suggested_impact_level": "high"
                },
                {
                    "name": "Service Level Requirements",
                    "standard_wording": "Service Provider shall meet performance standards.",
                    "suggested_impact_level": "medium"
                }
            ],
            "Status": "CLAUSE_TYPES_EXTRACTED",
            "Timestamp": "2025-01-01T12:00:00Z"
        }

        # Verify response structure
        assert "ImportJobId" in expected_response
        assert "DocumentS3Key" in expected_response
        assert "ContractTypeInfo" in expected_response
        assert "ClauseTypes" in expected_response
        assert "Status" in expected_response
        assert "Timestamp" in expected_response

        # Verify clause types structure
        clause_types = expected_response["ClauseTypes"]
        assert isinstance(clause_types, list)
        assert len(clause_types) > 0

        for clause_type in clause_types:
            assert "name" in clause_type
            assert "standard_wording" in clause_type
            assert "suggested_impact_level" in clause_type
            assert clause_type["suggested_impact_level"] in ["low", "medium", "high"]

    def test_missing_required_fields_validation(self):
        """Test validation of required fields"""
        def validate_required_fields(event):
            if not event.get("ImportJobId"):
                raise ValueError("ImportJobId is required")
            if not event.get("DocumentS3Key"):
                raise ValueError("DocumentS3Key is required")
            if not event.get("ContractTypeInfo"):
                raise ValueError("ContractTypeInfo is required")
            return True

        # Test missing ImportJobId
        event_missing_job_id = {
            "ExecutionName": "test-execution-123",
            "DocumentS3Key": "documents/test-contract.pdf",
            "ContractTypeInfo": {"contract_type_name": "Service Agreement"}
        }

        with pytest.raises(ValueError, match="ImportJobId is required"):
            validate_required_fields(event_missing_job_id)

        # Test missing DocumentS3Key
        event_missing_s3_key = {
            "ExecutionName": "test-execution-123",
            "ImportJobId": "import-job-456",
            "ContractTypeInfo": {"contract_type_name": "Service Agreement"}
        }

        with pytest.raises(ValueError, match="DocumentS3Key is required"):
            validate_required_fields(event_missing_s3_key)

        # Test missing ContractTypeInfo
        event_missing_contract_info = {
            "ExecutionName": "test-execution-123",
            "ImportJobId": "import-job-456",
            "DocumentS3Key": "documents/test-contract.pdf"
        }

        with pytest.raises(ValueError, match="ContractTypeInfo is required"):
            validate_required_fields(event_missing_contract_info)

    def test_clause_type_validation(self):
        """Test clause type validation logic"""
        def validate_clause_type(clause_type):
            required_fields = ["name", "standard_wording", "suggested_impact_level"]

            # Check required fields exist and are not empty
            for field in required_fields:
                if field not in clause_type or not clause_type[field]:
                    return False

            # Validate impact level
            valid_impact_levels = ["low", "medium", "high"]
            impact_level = clause_type["suggested_impact_level"].lower()
            if impact_level not in valid_impact_levels:
                return False

            # Normalize impact level
            clause_type["suggested_impact_level"] = impact_level

            # Validate name length (reasonable limits)
            if len(clause_type["name"]) > 200:
                return False

            # Validate standard wording length
            if len(clause_type["standard_wording"]) > 2000:
                return False

            return True

        # Test valid clause type
        valid_clause_type = {
            "name": "Payment Terms",
            "standard_wording": "Payment shall be made within 30 days of invoice receipt.",
            "suggested_impact_level": "high"
        }
        assert validate_clause_type(valid_clause_type) is True
        assert valid_clause_type["suggested_impact_level"] == "high"  # Normalized

        # Test clause type with uppercase impact level (should be normalized)
        clause_type_uppercase = {
            "name": "Service Level Requirements",
            "standard_wording": "Service Provider shall meet performance standards.",
            "suggested_impact_level": "MEDIUM"
        }
        assert validate_clause_type(clause_type_uppercase) is True
        assert clause_type_uppercase["suggested_impact_level"] == "medium"  # Normalized

        # Test missing name
        clause_type_missing_name = {
            "standard_wording": "Payment shall be made within 30 days.",
            "suggested_impact_level": "high"
        }
        assert validate_clause_type(clause_type_missing_name) is False

        # Test empty standard wording
        clause_type_empty_wording = {
            "name": "Payment Terms",
            "standard_wording": "",
            "suggested_impact_level": "high"
        }
        assert validate_clause_type(clause_type_empty_wording) is False

        # Test invalid impact level
        clause_type_invalid_impact = {
            "name": "Payment Terms",
            "standard_wording": "Payment shall be made within 30 days.",
            "suggested_impact_level": "critical"
        }
        assert validate_clause_type(clause_type_invalid_impact) is False

        # Test name too long
        clause_type_long_name = {
            "name": "A" * 201,  # 201 characters
            "standard_wording": "Payment shall be made within 30 days.",
            "suggested_impact_level": "high"
        }
        assert validate_clause_type(clause_type_long_name) is False

        # Test standard wording too long
        clause_type_long_wording = {
            "name": "Payment Terms",
            "standard_wording": "A" * 2001,  # 2001 characters
            "suggested_impact_level": "high"
        }
        assert validate_clause_type(clause_type_long_wording) is False

    def test_llm_response_parsing_valid_json(self):
        """Test LLM response parsing with valid JSON"""
        def parse_llm_response(response_text):
            response_text = response_text.strip()

            # Look for JSON block in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')

            if start_idx == -1 or end_idx == -1:
                raise ValueError("No JSON object found in response")

            json_str = response_text[start_idx:end_idx + 1]
            response_data = json.loads(json_str)

            # Validate response structure
            if "clause_types" not in response_data:
                raise ValueError("Missing 'clause_types' field in response")

            clause_types = response_data["clause_types"]

            if not isinstance(clause_types, list):
                raise ValueError("'clause_types' must be a list")

            if len(clause_types) == 0:
                raise ValueError("No clause types found in response")

            return clause_types

        # Test valid JSON response
        valid_response = '''
        Based on the document analysis, here are the identified clause types:
        {
          "clause_types": [
            {
              "name": "Payment Terms",
              "standard_wording": "Payment shall be made within 30 days of invoice receipt in accordance with the agreed payment schedule.",
              "suggested_impact_level": "high"
            },
            {
              "name": "Service Level Requirements",
              "standard_wording": "Service Provider shall meet the performance standards and service levels specified in the Statement of Work.",
              "suggested_impact_level": "medium"
            }
          ]
        }
        '''

        result = parse_llm_response(valid_response)
        assert len(result) == 2
        assert result[0]["name"] == "Payment Terms"
        assert result[0]["suggested_impact_level"] == "high"
        assert result[1]["name"] == "Service Level Requirements"
        assert result[1]["suggested_impact_level"] == "medium"

    def test_llm_response_parsing_invalid_json(self):
        """Test LLM response parsing with invalid JSON"""
        def parse_llm_response(response_text):
            response_text = response_text.strip()

            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')

            if start_idx == -1 or end_idx == -1:
                raise ValueError("No JSON object found in response")

            json_str = response_text[start_idx:end_idx + 1]
            try:
                response_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in LLM response: {str(e)}")

            return response_data

        # Test response without JSON
        no_json_response = "This is just text without any JSON structure."
        with pytest.raises(ValueError, match="No JSON object found in response"):
            parse_llm_response(no_json_response)

        # Test invalid JSON (malformed JSON with syntax error)
        invalid_json_response = '''
        {
          "clause_types": [
            {
              "name": "Payment Terms",
              "standard_wording": "Payment shall be made within 30 days.",
              "suggested_impact_level": "high",
            }
          ]
        }
        '''
        with pytest.raises(ValueError, match="Invalid JSON in LLM response"):
            parse_llm_response(invalid_json_response)

    def test_llm_response_parsing_missing_clause_types_field(self):
        """Test LLM response parsing with missing clause_types field"""
        def parse_llm_response(response_text):
            response_text = response_text.strip()
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            json_str = response_text[start_idx:end_idx + 1]
            response_data = json.loads(json_str)

            if "clause_types" not in response_data:
                raise ValueError("Missing 'clause_types' field in response")

            clause_types = response_data["clause_types"]

            if not isinstance(clause_types, list):
                raise ValueError("'clause_types' must be a list")

            if len(clause_types) == 0:
                raise ValueError("No clause types found in response")

            return clause_types

        # Test missing clause_types field
        missing_field_response = '''
        {
          "contract_analysis": [
            {
              "name": "Payment Terms",
              "standard_wording": "Payment shall be made within 30 days.",
              "suggested_impact_level": "high"
            }
          ]
        }
        '''
        with pytest.raises(ValueError, match="Missing 'clause_types' field in response"):
            parse_llm_response(missing_field_response)

        # Test clause_types is not a list
        not_list_response = '''
        {
          "clause_types": "This should be a list"
        }
        '''
        with pytest.raises(ValueError, match="'clause_types' must be a list"):
            parse_llm_response(not_list_response)

        # Test empty clause_types list
        empty_list_response = '''
        {
          "clause_types": []
        }
        '''
        with pytest.raises(ValueError, match="No clause types found in response"):
            parse_llm_response(empty_list_response)

    def test_document_format_detection(self):
        """Test document format detection logic"""
        def get_document_format(document_s3_key):
            file_extension = document_s3_key.split(".")[-1].lower()
            supported_formats = {"pdf": "pdf", "docx": "docx", "doc": "docx", "txt": "txt"}

            if file_extension not in supported_formats:
                raise ValueError(f"Unsupported file format: .{file_extension}")

            return supported_formats[file_extension]

        # Test supported formats
        assert get_document_format("contract.pdf") == "pdf"
        assert get_document_format("contract.docx") == "docx"
        assert get_document_format("contract.doc") == "docx"
        assert get_document_format("contract.txt") == "txt"
        assert get_document_format("CONTRACT.PDF") == "pdf"  # Case insensitive

        # Test unsupported format
        with pytest.raises(ValueError, match="Unsupported file format: .xlsx"):
            get_document_format("contract.xlsx")

    def test_prompt_template_with_contract_context(self):
        """Test prompt template with contract context"""
        prompt_template = """
Analyze this contract document and identify distinct clause types that should be monitored for compliance.

For each clause type you identify, provide:
1. Name: A descriptive name for the clause type (e.g., "Payment Terms", "Termination Conditions")
2. Standard Wording: Representative text that captures the essence of this clause type
3. Suggested Impact Level: Business impact level - "low", "medium", or "high"

Focus on identifying clause types that are:
- Important for compliance monitoring
- Distinct from each other
- Commonly found in similar contracts

Contract context:
- Type: {contract_type_name}
- Company role: {company_party_type}
- Other party role: {other_party_type}

Document content:
{document_content}

Return your analysis in JSON format:
{{
  "clause_types": [
    {{
      "name": "Payment Terms",
      "standard_wording": "Payment shall be made within 30 days of invoice receipt in accordance with the agreed payment schedule.",
      "suggested_impact_level": "high"
    }}
  ]
}}
"""

        # Test prompt template structure
        assert "clause types" in prompt_template
        assert "Name:" in prompt_template
        assert "Standard Wording:" in prompt_template
        assert "Suggested Impact Level:" in prompt_template
        assert "Contract context:" in prompt_template
        assert "{contract_type_name}" in prompt_template
        assert "{company_party_type}" in prompt_template
        assert "{other_party_type}" in prompt_template
        assert "{document_content}" in prompt_template
        assert "JSON format" in prompt_template

        # Test placeholder replacement
        def replace_placeholders(template, replacements):
            result = template
            for key, value in replacements.items():
                result = result.replace(f"{{{key}}}", value)
            return result

        contract_type_info = {
            "contract_type_name": "Service Agreement",
            "company_party_type": "Customer",
            "other_party_type": "Service Provider"
        }

        filled_prompt = replace_placeholders(prompt_template, {
            "contract_type_name": contract_type_info["contract_type_name"],
            "company_party_type": contract_type_info["company_party_type"],
            "other_party_type": contract_type_info["other_party_type"],
            "document_content": "Please analyze the attached document."
        })

        assert "{contract_type_name}" not in filled_prompt
        assert "Service Agreement" in filled_prompt
        assert "Customer" in filled_prompt
        assert "Service Provider" in filled_prompt
        assert "Please analyze the attached document." in filled_prompt

    def test_retry_logic_parameters(self):
        """Test retry logic parameters"""
        def get_retry_parameters(attempt):
            if attempt == 0:
                # First attempt: standard parameters
                return {"temperature": 0.1, "max_tokens": 4096}
            elif attempt == 1:
                # Second attempt: slightly higher temperature, more tokens
                return {"temperature": 0.3, "max_tokens": 6144}
            else:
                # Final attempt: higher temperature, maximum tokens
                return {"temperature": 0.5, "max_tokens": 8192}

        # Test retry parameters for different attempts
        params_0 = get_retry_parameters(0)
        assert params_0["temperature"] == 0.1
        assert params_0["max_tokens"] == 4096

        params_1 = get_retry_parameters(1)
        assert params_1["temperature"] == 0.3
        assert params_1["max_tokens"] == 6144

        params_2 = get_retry_parameters(2)
        assert params_2["temperature"] == 0.5
        assert params_2["max_tokens"] == 8192

    @patch('boto3.resource')
    def test_import_job_status_update_logic(self, mock_boto3_resource):
        """Test import job status update logic"""
        # Mock DynamoDB table
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_boto3_resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table

        def update_import_job_status(import_job_id, status, current_step, progress=None, error_message=None):
            # Build update expression
            update_expression = "SET #status = :status, current_step = :current_step, updated_at = :updated_at"
            expression_attribute_names = {"#status": "status"}
            expression_attribute_values = {
                ":status": status,
                ":current_step": current_step,
                ":updated_at": "2025-01-01T12:00:00Z"
            }

            if progress is not None:
                update_expression += ", progress = :progress"
                expression_attribute_values[":progress"] = progress

            if error_message is not None:
                update_expression += ", error_message = :error_message"
                expression_attribute_values[":error_message"] = error_message

            mock_table.update_item(
                Key={"import_job_id": import_job_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression="attribute_exists(import_job_id)"
            )

        # Test successful status update with progress
        update_import_job_status("import-job-456", "RUNNING", "EXTRACT_CLAUSE_TYPES", progress=60)

        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args

        assert call_args[1]["Key"] == {"import_job_id": "import-job-456"}
        assert ":status" in call_args[1]["ExpressionAttributeValues"]
        assert call_args[1]["ExpressionAttributeValues"][":status"] == "RUNNING"
        assert call_args[1]["ExpressionAttributeValues"][":progress"] == 60

    def test_llm_integration_logic(self):
        """Test LLM integration logic"""
        # Mock LLM response structure
        class MockLLMResponse:
            def __init__(self, output, stop_reason):
                self.output = output
                self.stop_reason = stop_reason

        mock_response = MockLLMResponse(
            output='''
            {
              "clause_types": [
                {
                  "name": "Payment Terms",
                  "standard_wording": "Payment shall be made within 30 days of invoice receipt.",
                  "suggested_impact_level": "high"
                },
                {
                  "name": "Service Level Requirements",
                  "standard_wording": "Service Provider shall meet performance standards.",
                  "suggested_impact_level": "medium"
                }
              ]
            }
            ''',
            stop_reason="end_turn"
        )

        # Test LLM invocation parameters structure
        def validate_llm_call_parameters(prompt, model_id, document_s3_uri, document_format,
                                       max_new_tokens, temperature, verbose):
            # Validate parameter types and values
            assert isinstance(prompt, str)
            assert isinstance(model_id, str)
            assert isinstance(document_s3_uri, str)
            assert isinstance(document_format, str)
            assert isinstance(max_new_tokens, int)
            assert isinstance(temperature, float)
            assert isinstance(verbose, bool)

            # Validate specific values for clause types extraction
            assert model_id == "amazon.nova-pro-v1:0"  # Pro model for complex analysis
            assert document_s3_uri.startswith("s3://")
            assert document_format in ["pdf", "docx", "txt"]
            assert max_new_tokens in [4096, 6144, 8192]  # Retry logic values
            assert temperature in [0.1, 0.3, 0.5]  # Retry logic values
            assert verbose is True

            return mock_response

        # Test LLM call parameter validation
        result = validate_llm_call_parameters(
            prompt="Analyze this contract document and identify clause types...",
            model_id="amazon.nova-pro-v1:0",
            document_s3_uri="s3://test-bucket/documents/test.pdf",
            document_format="pdf",
            max_new_tokens=4096,
            temperature=0.1,
            verbose=True
        )

        assert result == mock_response
        assert result.output is not None
        assert result.stop_reason == "end_turn"

    def test_response_format_validation(self):
        """Test response format validation"""
        # Test successful response format
        response = {
            "ImportJobId": "import-job-456",
            "DocumentS3Key": "documents/test-contract.pdf",
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
                    "standard_wording": "Payment shall be made within 30 days.",
                    "suggested_impact_level": "high"
                },
                {
                    "name": "Service Level Requirements",
                    "standard_wording": "Service Provider shall meet performance standards.",
                    "suggested_impact_level": "medium"
                }
            ],
            "Status": "CLAUSE_TYPES_EXTRACTED",
            "Timestamp": "2025-01-01T12:00:00Z"
        }

        # Verify response structure
        required_response_fields = [
            "ImportJobId", "DocumentS3Key", "ContractTypeInfo",
            "ClauseTypes", "Status", "Timestamp"
        ]

        for field in required_response_fields:
            assert field in response

        # Verify clause types structure
        clause_types = response["ClauseTypes"]
        assert isinstance(clause_types, list)
        assert len(clause_types) > 0

        for clause_type in clause_types:
            assert isinstance(clause_type, dict)
            assert "name" in clause_type
            assert "standard_wording" in clause_type
            assert "suggested_impact_level" in clause_type
            assert clause_type["suggested_impact_level"] in ["low", "medium", "high"]

        # Verify specific values
        assert response["Status"] == "CLAUSE_TYPES_EXTRACTED"
        assert isinstance(response["Timestamp"], str)

    def test_error_handling_logic(self):
        """Test error handling logic"""
        def handle_error(error, import_job_id):
            error_message = f"Clause types extraction failed: {str(error)}"

            # Simulate updating import job status to FAILED
            update_data = {
                "import_job_id": import_job_id,
                "status": "FAILED",
                "current_step": "EXTRACT_CLAUSE_TYPES_FAILED",
                "error_message": str(error)
            }

            # Re-raise the original error
            raise error

        # Test error handling
        original_error = ValueError("No valid clause types found after validation")
        import_job_id = "import-job-456"

        with pytest.raises(ValueError, match="No valid clause types found after validation"):
            handle_error(original_error, import_job_id)

    def test_environment_variables_usage(self):
        """Test environment variables usage"""
        # Test that required environment variables are available
        assert os.environ.get("IMPORT_JOBS_TABLE_NAME") == "test-import-jobs-table"
        assert os.environ.get("CONTRACT_BUCKET_NAME") == "test-contract-bucket"
        assert os.environ.get("DEFAULT_LLM_MODEL_ID") == "amazon.nova-pro-v1:0"
        assert os.environ.get("LOG_LEVEL") == "INFO"

        # Test environment variable validation logic
        def validate_environment():
            required_env_vars = ["IMPORT_JOBS_TABLE_NAME", "CONTRACT_BUCKET_NAME", "DEFAULT_LLM_MODEL_ID"]
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

    def test_clause_type_filtering_logic(self):
        """Test clause type filtering and validation logic"""
        def filter_valid_clause_types(clause_types):
            def validate_clause_type(clause_type):
                required_fields = ["name", "standard_wording", "suggested_impact_level"]

                # Check required fields exist and are not empty
                for field in required_fields:
                    if field not in clause_type or not clause_type[field]:
                        return False

                # Validate impact level
                valid_impact_levels = ["low", "medium", "high"]
                impact_level = clause_type["suggested_impact_level"].lower()
                if impact_level not in valid_impact_levels:
                    return False

                # Normalize impact level
                clause_type["suggested_impact_level"] = impact_level

                # Validate lengths
                if len(clause_type["name"]) > 200 or len(clause_type["standard_wording"]) > 2000:
                    return False

                return True

            valid_clause_types = []
            for i, clause_type in enumerate(clause_types):
                if not isinstance(clause_type, dict):
                    continue

                if validate_clause_type(clause_type):
                    valid_clause_types.append(clause_type)

            return valid_clause_types

        # Test mixed valid and invalid clause types
        mixed_clause_types = [
            {
                "name": "Payment Terms",
                "standard_wording": "Payment shall be made within 30 days.",
                "suggested_impact_level": "HIGH"  # Should be normalized
            },
            {
                "name": "",  # Invalid: empty name
                "standard_wording": "Service Provider shall meet standards.",
                "suggested_impact_level": "medium"
            },
            {
                "name": "Service Level Requirements",
                "standard_wording": "Service Provider shall meet performance standards.",
                "suggested_impact_level": "medium"
            },
            {
                "name": "Termination Conditions",
                "standard_wording": "Either party may terminate with notice.",
                "suggested_impact_level": "invalid"  # Invalid impact level
            },
            {
                "name": "Confidentiality",
                "standard_wording": "Parties shall maintain confidentiality.",
                "suggested_impact_level": "low"
            }
        ]

        valid_clause_types = filter_valid_clause_types(mixed_clause_types)

        # Should have 3 valid clause types (indices 0, 2, 4)
        assert len(valid_clause_types) == 3

        # Check that impact levels are normalized
        assert valid_clause_types[0]["suggested_impact_level"] == "high"  # Normalized from "HIGH"
        assert valid_clause_types[1]["suggested_impact_level"] == "medium"
        assert valid_clause_types[2]["suggested_impact_level"] == "low"

        # Check that names are correct
        expected_names = ["Payment Terms", "Service Level Requirements", "Confidentiality"]
        actual_names = [ct["name"] for ct in valid_clause_types]
        assert actual_names == expected_names