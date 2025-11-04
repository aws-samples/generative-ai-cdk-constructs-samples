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
Extract Clause Types Step Lambda Function

This function uses LLM to analyze the contract document and identify distinct clause types
with their standard wording and suggested impact levels.
"""

import json
import logging
import os
import boto3
from datetime import datetime
from typing import Dict, Any, List

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
APP_TASK_NAME = 'ExtractClauseTypes'

# Prompt template for clause types extraction
EXTRACT_CLAUSE_TYPES_PROMPT = """
Analyze this contract document and identify ONLY the clause types that are ACTUALLY PRESENT in the document.

DO NOT infer or suggest clause types that should be in the contract but are not explicitly present.

For each clause type you identify, provide:
1. Name: A descriptive name for the clause type
2. Standard Wording: Representative text that captures the essence of this clause type
3. Suggested Impact Level: Business impact level - "low", "medium", or "high"

Focus on identifying clause types that are:
- Important for compliance monitoring
- Distinct from each other
- Actually present in the document text

IMPORTANT: This contract is written in {language}. All extracted text values (name, standard_wording) MUST be in {language}.

Contract context:
- Type: {contract_type_name}
- Language: {language}
- Company role: {company_party_type}
- Other party role: {other_party_type}

Document content:
{document_content}

You MUST return ONLY valid JSON matching this exact schema, wrapped in <answer> tags:

<answer>
{{
  "clause_types": [
    {{
      "name": "<clause type name in {language}>",
      "standard_wording": "<representative text in {language}>",
      "suggested_impact_level": "low" | "medium" | "high"
    }}
  ]
}}
</answer>

Example for {language}: 
<json_payload_example>
<answer>
{language_example}
</answer>
</json_payload_example>

DO NOT include any text before or after the <answer> tags.

Before writing the answer, think step by step, writing all your thoughts in full between <thinking> tags.
"""

# Language-specific examples
LANGUAGE_EXAMPLES = {
    "en": '''{{
  "clause_types": [
    {{
      "name": "Payment Terms",
      "standard_wording": "Payment shall be made within 30 days of invoice receipt.",
      "suggested_impact_level": "high"
    }}
  ]
}}''',
    "es": '''{{
  "clause_types": [
    {{
      "name": "Términos de Pago",
      "standard_wording": "El pago se realizará dentro de los 30 días posteriores a la recepción de la factura.",
      "suggested_impact_level": "high"
    }}
  ]
}}''',
    "pt_BR": '''{{
  "clause_types": [
    {{
      "name": "Termos de Pagamento",
      "standard_wording": "O pagamento será efetuado no prazo de 30 dias após o recebimento da fatura.",
      "suggested_impact_level": "high"
    }}
  ]
}}'''
}


def get_language_example(language_code: str) -> str:
    """Get example in the specified language, fallback to English"""
    lang = language_code.lower().replace("_", "-") if language_code else "en"
    # Handle pt_BR -> pt_BR, pt-br -> pt_BR
    if lang.startswith("pt"):
        lang = "pt_BR"
    elif lang.startswith("es"):
        lang = "es"
    else:
        lang = "en"
    return LANGUAGE_EXAMPLES.get(lang, LANGUAGE_EXAMPLES["en"])


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


def validate_clause_type(clause_type: Dict[str, Any]) -> bool:
    """Validate a single clause type object"""
    required_fields = ["name", "standard_wording", "suggested_impact_level"]

    # Check required fields exist and are not empty
    for field in required_fields:
        if field not in clause_type or not clause_type[field]:
            logger.warning(f"Clause type missing or empty field: {field}")
            return False

    # Validate impact level
    valid_impact_levels = ["low", "medium", "high"]
    impact_level = clause_type["suggested_impact_level"].lower()
    if impact_level not in valid_impact_levels:
        logger.warning(f"Invalid impact level: {impact_level}")
        return False

    # Normalize impact level
    clause_type["suggested_impact_level"] = impact_level

    # Validate name length (reasonable limits)
    if len(clause_type["name"]) > 200:
        logger.warning(f"Clause type name too long: {len(clause_type['name'])} characters")
        return False

    # Validate standard wording length
    if len(clause_type["standard_wording"]) > 2000:
        logger.warning(f"Standard wording too long: {len(clause_type['standard_wording'])} characters")
        return False

    return True


def parse_llm_response(response_text: str) -> List[Dict[str, Any]]:
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
        response_data = json.loads(json_str)

        # Validate response structure
        if "clause_types" not in response_data:
            raise ValueError("Missing 'clause_types' field in response")

        clause_types = response_data["clause_types"]

        if not isinstance(clause_types, list):
            raise ValueError("'clause_types' must be a list")

        if len(clause_types) == 0:
            raise ValueError("No clause types found in response")

        # Validate each clause type
        valid_clause_types = []
        for i, clause_type in enumerate(clause_types):
            if not isinstance(clause_type, dict):
                logger.warning(f"Clause type {i} is not a dictionary, skipping")
                continue

            if validate_clause_type(clause_type):
                valid_clause_types.append(clause_type)
            else:
                logger.warning(f"Clause type {i} failed validation, skipping")

        if len(valid_clause_types) == 0:
            raise ValueError("No valid clause types found after validation")

        logger.info(f"Successfully parsed {len(valid_clause_types)} clause types")
        return valid_clause_types

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM response: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {str(e)}")


def retry_llm_with_fallback(prompt: str, document_s3_uri: str, document_format: str,
                           contract_type_info: Dict[str, Any], model_id: str, max_retries: int = 2) -> List[Dict[str, Any]]:
    """Retry LLM call with different strategies if initial attempt fails"""

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"LLM attempt {attempt + 1}/{max_retries + 1}")
            
            response = invoke_llm_with_document(
                prompt=prompt,
                model_id=model_id,
                document_s3_uri=document_s3_uri,
                document_format=document_format,
                max_new_tokens=5000,
                temperature=0,
                verbose=True
            )

            logger.info(f"LLM response received, stop_reason: {response.stop_reason}")

            # Parse and validate the response
            clause_types = parse_llm_response(response.output)

            logger.info(f"Successfully extracted {len(clause_types)} clause types on attempt {attempt + 1}")
            return clause_types

        except Exception as e:
            logger.warning(f"LLM attempt {attempt + 1} failed: {str(e)}")

            if attempt == max_retries:
                # Final attempt failed, re-raise the exception
                raise e

            # Continue to next attempt
            continue

    # This should never be reached, but just in case
    raise Exception("All LLM retry attempts failed")


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Extract clause types from document using LLM

    Args:
        event: Step Functions event containing:
            - ExecutionName: Step Functions execution name
            - ImportJobId: Import job identifier
            - DocumentS3Key: S3 key of the document to analyze
            - ContractTypeInfo: Contract type metadata from previous step

    Returns:
        Dict containing extracted clause types information
    """
    import_job_id = None

    try:
        logger.info(f"Starting clause types extraction: {json.dumps(event)}")

        # Initialize properties manager
        properties = AppPropertiesManager()
        model_id = properties.get_parameter('LanguageModelId', task_name=APP_TASK_NAME, default='amazon.nova-pro-v1:0')

        # Extract input parameters
        execution_name = event.get("ExecutionName")
        import_job_id = event.get("ImportJobId")
        document_s3_key = event.get("DocumentS3Key")
        contract_type_info = event.get("ContractTypeInfo", {})

        # Validate required parameters
        if not import_job_id:
            raise ValueError("ImportJobId is required")
        if not document_s3_key:
            raise ValueError("DocumentS3Key is required")
        if not contract_type_info:
            raise ValueError("ContractTypeInfo is required")

        # Update import job status to indicate we're processing
        update_import_job_status(
            import_job_id,
            "RUNNING",
            "EXTRACT_CLAUSE_TYPES",
            progress=60
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

        # Build prompt with contract type context
        language = contract_type_info.get("language", "en")
        prompt = replace_placeholders(EXTRACT_CLAUSE_TYPES_PROMPT, {
            "contract_type_name": contract_type_info.get("contract_type_name", "Unknown"),
            "language": language,
            "language_example": get_language_example(language),
            "company_party_type": contract_type_info.get("company_party_type", "Company"),
            "other_party_type": contract_type_info.get("other_party_type", "Other Party"),
            "document_content": "Please analyze the attached document."
        })

        # Call LLM with retry logic
        clause_types = retry_llm_with_fallback(
            prompt=prompt,
            document_s3_uri=document_s3_uri,
            document_format=document_format,
            contract_type_info=contract_type_info,
            model_id=model_id
        )

        logger.info(f"Extracted clause types: {json.dumps(clause_types, indent=2)}")

        # Update import job progress
        update_import_job_status(
            import_job_id,
            "RUNNING",
            "CLAUSE_TYPES_EXTRACTED",
            progress=80
        )

        # Return success response
        response_data = {
            "ImportJobId": import_job_id,
            "DocumentS3Key": document_s3_key,
            "ContractTypeInfo": contract_type_info,
            "ClauseTypes": clause_types,
            "Status": "CLAUSE_TYPES_EXTRACTED",
            "Timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"Clause types extraction completed: {len(clause_types)} clause types extracted")
        return response_data

    except Exception as e:
        error_message = f"Clause types extraction failed: {str(e)}"
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
                "EXTRACT_CLAUSE_TYPES_FAILED",
                error_message=error_message
            )

        # Return error response instead of raising to allow graceful handling
        return {
            "Error": "ClauseTypesExtractionFailed",
            "Cause": error_message,
            "ImportJobId": import_job_id,
            "Status": "FAILED"
        }