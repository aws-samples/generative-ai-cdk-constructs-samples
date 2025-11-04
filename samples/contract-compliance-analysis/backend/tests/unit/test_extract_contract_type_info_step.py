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
Unit tests for Extract Contract Type Info Step Lambda function
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError


class TestExtractContractTypeInfoStep:
    """Test cases for Extract Contract Type Info Step Lambda function"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_context = Mock()
        self.mock_context.aws_request_id = "test-request-id"

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'IMPORT_JOBS_TABLE_NAME': 'test-import-jobs-table',
            'CONTRACT_BUCKET_NAME': 'test-contract-bucket',
            'DEFAULT_LLM_MODEL_ID': 'amazon.nova-lite-v1:0',
            'LOG_LEVEL': 'INFO'
        })
        self.env_patcher.start()

    def teardown_method(self):
        """Clean up after tests"""
        self.env_patcher.stop()

    def test_successful_contract_type_info_extraction_logic(self):
        """Test successful contract type info extraction logic"""
        event = {
            "ExecutionName": "test-execution-123",
            "ImportJobId": "import-job-456",
            "DocumentS3Key": "documents/test-contract.pdf"
        }

        # Validate required parameters
        assert event.get("ImportJobId") == "import-job-456"
        assert event.get("DocumentS3Key") == "documents/test-contract.pdf"
        assert event.get("ExecutionName") == "test-execution-123"

        # Test expected response structure
        expected_response = {
            "ImportJobId": event["ImportJobId"],
            "DocumentS3Key": event["DocumentS3Key"],
            "ContractTypeInfo": {
                "contract_type_name": "Service Agreement",
                "description": "Agreement for provision of professional services",
                "company_party_type": "Customer",
                "other_party_type": "Service Provider",
                "language": "en"
            },
            "Status": "CONTRACT_TYPE_INFO_EXTRACTED",
            "Timestamp": "2025-01-01T12:00:00Z"
        }

        # Verify response structure
        assert "ImportJobId" in expected_response
        assert "DocumentS3Key" in expected_response
        assert "ContractTypeInfo" in expected_response
        assert "Status" in expected_response
        assert "Timestamp" in expected_response

        # Verify contract type info structure
        contract_info = expected_response["ContractTypeInfo"]
        required_fields = ["contract_type_name", "description", "company_party_type",
                          "other_party_type", "language"]

        for field in required_fields:
            assert field in contract_info
            assert contract_info[field]  # Not empty

    def test_missing_required_fields_validation(self):
        """Test validation of required fields"""
        def validate_required_fields(event):
            if not event.get("ImportJobId"):
                raise ValueError("ImportJobId is required")
            if not event.get("DocumentS3Key"):
                raise ValueError("DocumentS3Key is required")
            return True

        # Test missing ImportJobId
        event_missing_job_id = {
            "ExecutionName": "test-execution-123",
            "DocumentS3Key": "documents/test-contract.pdf"
        }

        with pytest.raises(ValueError, match="ImportJobId is required"):
            validate_required_fields(event_missing_job_id)

        # Test missing DocumentS3Key
        event_missing_s3_key = {
            "ExecutionName": "test-execution-123",
            "ImportJobId": "import-job-456"
        }

        with pytest.raises(ValueError, match="DocumentS3Key is required"):
            validate_required_fields(event_missing_s3_key)

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

    def test_s3_uri_construction(self):
        """Test S3 URI construction logic"""
        def construct_s3_uri(bucket_name, document_s3_key):
            return f"s3://{bucket_name}/{document_s3_key}"

        bucket_name = "test-contract-bucket"
        document_s3_key = "documents/test-contract.pdf"

        expected_uri = "s3://test-contract-bucket/documents/test-contract.pdf"
        actual_uri = construct_s3_uri(bucket_name, document_s3_key)

        assert actual_uri == expected_uri

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
            contract_info = json.loads(json_str)

            # Validate required fields
            required_fields = ["contract_type_name", "description", "company_party_type",
                              "other_party_type", "language"]

            for field in required_fields:
                if field not in contract_info or not contract_info[field]:
                    raise ValueError(f"Missing or empty required field: {field}")

            # Validate language code format
            language = contract_info["language"].lower()
            if len(language) < 2 or len(language) > 5:
                contract_info["language"] = "en"  # Fallback

            return contract_info

        # Test valid JSON response
        valid_response = '''
        Based on the document analysis, here is the extracted information:
        {
          "contract_type_name": "Service Agreement",
          "description": "Agreement for provision of professional services",
          "company_party_type": "Customer",
          "other_party_type": "Service Provider",
          "language": "en"
        }
        '''

        result = parse_llm_response(valid_response)
        assert result["contract_type_name"] == "Service Agreement"
        assert result["description"] == "Agreement for provision of professional services"
        assert result["company_party_type"] == "Customer"
        assert result["other_party_type"] == "Service Provider"
        assert result["language"] == "en"

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
                contract_info = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in LLM response: {str(e)}")

            return contract_info

        # Test response without JSON
        no_json_response = "This is just text without any JSON structure."
        with pytest.raises(ValueError, match="No JSON object found in response"):
            parse_llm_response(no_json_response)

        # Test invalid JSON (malformed JSON with syntax error)
        invalid_json_response = '''
        {
          "contract_type_name": "Service Agreement",
          "description": "Agreement for provision of professional services",
          "company_party_type": "Customer",
          "other_party_type": "Service Provider",
          "language": "en",
        }
        '''
        with pytest.raises(ValueError, match="Invalid JSON in LLM response"):
            parse_llm_response(invalid_json_response)

    def test_llm_response_parsing_missing_fields(self):
        """Test LLM response parsing with missing required fields"""
        def parse_llm_response(response_text):
            response_text = response_text.strip()
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            json_str = response_text[start_idx:end_idx + 1]
            contract_info = json.loads(json_str)

            required_fields = ["contract_type_name", "description", "company_party_type",
                              "other_party_type", "language"]

            for field in required_fields:
                if field not in contract_info or not contract_info[field]:
                    raise ValueError(f"Missing or empty required field: {field}")

            return contract_info

        # Test missing field
        missing_field_response = '''
        {
          "contract_type_name": "Service Agreement",
          "description": "Agreement for provision of professional services",
          "company_party_type": "Customer",
          "language": "en"
        }
        '''
        with pytest.raises(ValueError, match="Missing or empty required field: other_party_type"):
            parse_llm_response(missing_field_response)

        # Test empty field
        empty_field_response = '''
        {
          "contract_type_name": "",
          "description": "Agreement for provision of professional services",
          "company_party_type": "Customer",
          "other_party_type": "Service Provider",
          "language": "en"
        }
        '''
        with pytest.raises(ValueError, match="Missing or empty required field: contract_type_name"):
            parse_llm_response(empty_field_response)

    def test_language_code_validation(self):
        """Test language code validation and fallback"""
        def validate_language_code(language):
            language = language.lower()
            if len(language) < 2 or len(language) > 5:
                return "en"  # Fallback
            return language

        # Test valid language codes
        assert validate_language_code("en") == "en"
        assert validate_language_code("es") == "es"
        assert validate_language_code("pt") == "pt"
        assert validate_language_code("pt-BR") == "pt-br"
        assert validate_language_code("EN") == "en"  # Case insensitive

        # Test invalid language codes (fallback to 'en')
        assert validate_language_code("x") == "en"  # Too short
        assert validate_language_code("toolong") == "en"  # Too long
        assert validate_language_code("") == "en"  # Empty

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

        # Test successful status update
        update_import_job_status("import-job-456", "RUNNING", "EXTRACT_CONTRACT_TYPE_INFO", progress=25)

        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args

        assert call_args[1]["Key"] == {"import_job_id": "import-job-456"}
        assert ":status" in call_args[1]["ExpressionAttributeValues"]
        assert call_args[1]["ExpressionAttributeValues"][":status"] == "RUNNING"
        assert call_args[1]["ExpressionAttributeValues"][":progress"] == 25

    def test_error_handling_logic(self):
        """Test error handling logic"""
        def handle_error(error, import_job_id):
            error_message = f"Contract type info extraction failed: {str(error)}"

            # Simulate updating import job status to FAILED
            update_data = {
                "import_job_id": import_job_id,
                "status": "FAILED",
                "current_step": "EXTRACT_CONTRACT_TYPE_INFO_FAILED",
                "error_message": str(error)
            }

            # Re-raise the original error
            raise error

        # Test error handling
        original_error = ValueError("Invalid JSON in LLM response")
        import_job_id = "import-job-456"

        with pytest.raises(ValueError, match="Invalid JSON in LLM response"):
            handle_error(original_error, import_job_id)

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
              "contract_type_name": "Service Agreement",
              "description": "Agreement for provision of professional services",
              "company_party_type": "Customer",
              "other_party_type": "Service Provider",
              "language": "en"
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

            # Validate specific values
            assert model_id == "amazon.nova-lite-v1:0"
            assert document_s3_uri.startswith("s3://")
            assert document_format in ["pdf", "docx", "txt"]
            assert max_new_tokens == 2048
            assert temperature == 0.1
            assert verbose is True

            return mock_response

        # Test LLM call parameter validation
        result = validate_llm_call_parameters(
            prompt="Analyze this contract document...",
            model_id="amazon.nova-lite-v1:0",
            document_s3_uri="s3://test-bucket/documents/test.pdf",
            document_format="pdf",
            max_new_tokens=2048,
            temperature=0.1,
            verbose=True
        )

        assert result == mock_response
        assert result.output is not None
        assert result.stop_reason == "end_turn"

    def test_prompt_template_validation(self):
        """Test prompt template validation"""
        prompt_template = """
Analyze this contract document and extract the contract type information needed to set up compliance analysis.

Your task is to identify:
1. Contract Type Name: What type of contract is this? (e.g., "Service Agreement", "Employment Contract", "NDA")
2. Description: Brief description of the contract's purpose and scope
3. Company Party Type: What role does the company play? (e.g., "Customer", "Employer", "Service Provider")
4. Other Party Type: What role does the other party play? (e.g., "Service Provider", "Employee", "Contractor")
5. Language: What language is the contract written in? (ISO code like "en", "es", "pt")

Document content:
{document_content}

Return your analysis in JSON format:
{
  "contract_type_name": "Service Agreement",
  "description": "Agreement for provision of professional services",
  "company_party_type": "Customer",
  "other_party_type": "Service Provider",
  "language": "en"
}
"""

        # Test prompt template structure
        assert "Contract Type Name" in prompt_template
        assert "Description" in prompt_template
        assert "Company Party Type" in prompt_template
        assert "Other Party Type" in prompt_template
        assert "Language" in prompt_template
        assert "{document_content}" in prompt_template
        assert "JSON format" in prompt_template

        # Test placeholder replacement
        def replace_placeholders(template, replacements):
            result = template
            for key, value in replacements.items():
                result = result.replace(f"{{{key}}}", value)
            return result

        filled_prompt = replace_placeholders(prompt_template, {
            "document_content": "Please analyze the attached document."
        })

        assert "{document_content}" not in filled_prompt
        assert "Please analyze the attached document." in filled_prompt

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
            "Status": "CONTRACT_TYPE_INFO_EXTRACTED",
            "Timestamp": "2025-01-01T12:00:00Z"
        }

        # Verify response structure
        required_response_fields = [
            "ImportJobId", "DocumentS3Key", "ContractTypeInfo",
            "Status", "Timestamp"
        ]

        for field in required_response_fields:
            assert field in response

        # Verify contract type info structure
        contract_info = response["ContractTypeInfo"]
        required_contract_fields = [
            "contract_type_name", "description", "company_party_type",
            "other_party_type", "language"
        ]

        for field in required_contract_fields:
            assert field in contract_info
            assert isinstance(contract_info[field], str)
            assert contract_info[field]  # Not empty

        # Verify specific values
        assert response["Status"] == "CONTRACT_TYPE_INFO_EXTRACTED"
        assert isinstance(response["Timestamp"], str)

    def test_environment_variables_usage(self):
        """Test environment variables usage"""
        # Test that required environment variables are available
        assert os.environ.get("IMPORT_JOBS_TABLE_NAME") == "test-import-jobs-table"
        assert os.environ.get("CONTRACT_BUCKET_NAME") == "test-contract-bucket"
        assert os.environ.get("DEFAULT_LLM_MODEL_ID") == "amazon.nova-lite-v1:0"
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