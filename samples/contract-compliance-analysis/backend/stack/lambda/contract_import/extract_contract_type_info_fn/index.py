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
Extract Contract Type Info Step Lambda Function

This function uses LLM to extract contract type metadata from the uploaded document.
"""

import json
import logging
import os
import boto3
from datetime import datetime
from typing import Dict, Any

# Import from layers
from llm import invoke_llm_with_document
from util import replace_placeholders, extract_last_item_from_tagged_list
from app_properties_manager import AppPropertiesManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Environment variables
IMPORT_JOBS_TABLE_NAME = os.environ["IMPORT_JOBS_TABLE_NAME"]
APP_TASK_NAME = 'ContractTypeExtraction'

# Prompt template for contract type info extraction
EXTRACT_CONTRACT_TYPE_INFO_PROMPT = """
Analyze this contract document and extract the contract type information needed to set up compliance analysis.

Your task is to identify:
1. Language: What language is the contract written in? (ISO code: "en", "es", or "pt_BR")
2. Contract Type Name: What type of contract is this?
3. Description: Brief description of the contract's purpose and scope
4. Company Party Type: What role does the company play?
5. Other Party Type: What role does the other party play?

CRITICAL: All extracted text values (contract_type_name, description, company_party_type, other_party_type) MUST be in the SAME language as the contract document itself. Extract the text as-is without translating.

Document content:
{document_content}

You MUST return ONLY valid JSON matching this exact schema, wrapped in <answer> tags:

<answer>
{{
  "language": "en" | "es" | "pt_BR",
  "contract_type_name": "<contract type in detected language>",
  "description": "<description in detected language>",
  "company_party_type": "<company role in detected language>",
  "other_party_type": "<other party role in detected language>"
}}
</answer>

Examples for different languages:
<json_payload_examples>
<example_1>
<answer>
{{
  "language": "en",
  "contract_type_name": "Contract Type Name",
  "description": "Brief description of the contract purpose and scope",
  "company_party_type": "Company Role",
  "other_party_type": "Other Party Role"
}}
</answer>
</example_1>

<example_2>
<answer>
{{
  "language": "es",
  "contract_type_name": "Nombre del Tipo de Contrato",
  "description": "Breve descripción del propósito y alcance del contrato",
  "company_party_type": "Rol de la Empresa",
  "other_party_type": "Rol de la Otra Parte"
}}
</answer>
</example_2>

<example_3>
<answer>
{{
  "language": "pt_BR",
  "contract_type_name": "Nome do Tipo de Contrato",
  "description": "Breve descrição do propósito e escopo do contrato",
  "company_party_type": "Papel da Empresa",
  "other_party_type": "Papel da Outra Parte"
}}
</answer>
</example_3>
</json_payload_examples>

DO NOT include any text before or after the <answer> tags.

Before writing the answer, think step by step, writing all your thoughts in full between <thinking> tags.
"""


def update_import_job_status(import_job_id: str, status: str, current_step: str,
                           progress: int = None, error_message: str = None):
    """Update import job status in DynamoDB"""
    try:
        table = dynamodb.Table(IMPORT_JOBS_TABLE_NAME)

        # Build update expression dynamically
        update_expression = "SET #status = :status, current_step = :current_step, updated_at = :updated_at"
        expression_attribute_names = {"#status": "status"}
        expression_attribute_values = {
            ":status": status,
            ":current_step": current_step,
            ":updated_at": datetime.utcnow().isoformat()
        }

        if progress is not None:
            update_expression += ", progress = :progress"
            expression_attribute_values[":progress"] = progress

        if error_message is not None:
            update_expression += ", error_message = :error_message"
            expression_attribute_values[":error_message"] = error_message

        table.update_item(
            Key={"import_job_id": import_job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ConditionExpression="attribute_exists(import_job_id)"
        )
        logger.info(f"Updated import job {import_job_id} status to {status}")

    except Exception as e:
        logger.error(f"Failed to update import job status: {str(e)}")
        # Don't raise here as this is a side effect, not critical to the main flow


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse and validate LLM response JSON"""
    try:
        # Try to extract content from answer tags first
        answer_content = extract_last_item_from_tagged_list(response_text, "answer")
        
        # Use extracted content if found, otherwise use full response
        response_text = answer_content if answer_content else response_text
        response_text = response_text.strip()

        # Look for JSON block in the content
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

        # Validate language code format (basic check)
        language = contract_info["language"]
        valid_languages = ["en", "es", "pt_BR"]
        if language not in valid_languages:
            logger.warning(f"Unusual language code: {language}, using 'en' as fallback")
            contract_info["language"] = "en"

        return contract_info

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM response: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {str(e)}")


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Extract contract type information from document using LLM

    Args:
        event: Step Functions event containing:
            - ExecutionName: Step Functions execution name
            - ImportJobId: Import job identifier
            - DocumentS3Key: S3 key of the document to analyze

    Returns:
        Dict containing extracted contract type information
    """
    import_job_id = None

    try:
        logger.info(f"Starting contract type info extraction: {json.dumps(event)}")

        # Initialize properties manager
        properties = AppPropertiesManager()
        model_id = properties.get_parameter('LanguageModelId', task_name=APP_TASK_NAME, default='amazon.nova-pro-v1:0')

        # Extract input parameters
        execution_name = event.get("ExecutionName")
        import_job_id = event.get("ImportJobId")
        document_s3_key = event.get("DocumentS3Key")

        # Validate required parameters
        if not import_job_id:
            raise ValueError("ImportJobId is required")
        if not document_s3_key:
            raise ValueError("DocumentS3Key is required")

        # Update import job status to indicate we're processing
        update_import_job_status(
            import_job_id,
            "RUNNING",
            "EXTRACT_CONTRACT_TYPE_INFO",
            progress=25
        )

        # Determine document format from S3 key
        file_extension = document_s3_key.split(".")[-1].lower()
        supported_formats = {"pdf": "pdf", "docx": "docx", "doc": "docx", "txt": "txt"}

        if file_extension not in supported_formats:
            raise ValueError(f"Unsupported file format: .{file_extension}")

        document_format = supported_formats[file_extension]

        # Construct S3 URI for the document
        bucket_name = os.environ.get("CONTRACT_BUCKET_NAME", "contract-analysis-bucket")
        document_s3_uri = f"s3://{bucket_name}/{document_s3_key}"

        logger.info(f"Processing document: {document_s3_uri} (format: {document_format})")

        # Build prompt
        prompt = replace_placeholders(EXTRACT_CONTRACT_TYPE_INFO_PROMPT, {
            "document_content": "Please analyze the attached document."
        })

        # Call LLM with document with retry logic
        max_retries = 3
        contract_type_info = None

        for attempt in range(max_retries):
            try:
                logger.info(f"LLM call attempt {attempt + 1}/{max_retries}")

                response = invoke_llm_with_document(
                    prompt=prompt,
                    model_id=model_id,
                    document_s3_uri=document_s3_uri,
                    document_format=document_format,
                    max_new_tokens=2048,
                    temperature=0,
                    verbose=True
                )

                logger.info(f"LLM response received, stop_reason: {response.stop_reason}")

                # Parse and validate the response
                contract_type_info = parse_llm_response(response.output)
                break  # Success, exit retry loop

            except ValueError as parse_error:
                logger.warning(f"LLM response parsing failed on attempt {attempt + 1}: {str(parse_error)}")
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to extract valid contract type info after {max_retries} attempts: {str(parse_error)}")
                # Continue to next attempt

            except Exception as llm_error:
                logger.warning(f"LLM call failed on attempt {attempt + 1}: {str(llm_error)}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"LLM call failed after {max_retries} attempts: {str(llm_error)}")
                # Continue to next attempt

        logger.info(f"Extracted contract type info: {json.dumps(contract_type_info)}")

        # Update import job progress
        update_import_job_status(
            import_job_id,
            "RUNNING",
            "CONTRACT_TYPE_INFO_EXTRACTED",
            progress=50
        )

        # Return success response
        response_data = {
            "ImportJobId": import_job_id,
            "DocumentS3Key": document_s3_key,
            "ContractTypeInfo": contract_type_info,
            "Status": "CONTRACT_TYPE_INFO_EXTRACTED",
            "Timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"Contract type info extraction completed: {json.dumps(response_data)}")
        return response_data

    except Exception as e:
        error_message = f"Contract type info extraction failed: {str(e)}"
        logger.error(error_message, extra={
            "import_job_id": import_job_id,
            "error_type": type(e).__name__,
            "event": event
        })

        # Update import job status to failed
        if import_job_id:
            update_import_job_status(
                import_job_id,
                "FAILED",
                "EXTRACT_CONTRACT_TYPE_INFO_FAILED",
                error_message=error_message
            )

        # Return error response instead of raising to allow graceful handling
        return {
            "Error": "ContractTypeInfoExtractionFailed",
            "Cause": error_message,
            "ImportJobId": import_job_id,
            "Status": "FAILED"
        }