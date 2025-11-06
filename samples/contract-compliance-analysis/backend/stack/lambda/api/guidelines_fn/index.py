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

import os
import json
import base64
from typing import Optional, List
from datetime import datetime, timezone
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.exceptions import NotFoundError, BadRequestError
from aws_lambda_powertools import Logger

# Import from common layer (will be available at runtime)
from llm import invoke_llm
from model import Guideline, ContractType
from app_properties_manager import AppPropertiesManager
from schema import (
    GuidelineResponse, CreateGuidelineRequest, UpdateGuidelineRequest, GuidelinesListResponse,
    GenerateQuestionsRequest, GenerateQuestionsResponse, GenerateExamplesRequest, GenerateExamplesResponse
)
from repository.dynamodb_guidelines_repository import DynamoDBGuidelinesRepository
from repository.dynamo_db_contract_type_repository import DynamoDBContractTypeRepository

cors_config = CORSConfig()
app = APIGatewayRestResolver(cors=cors_config, enable_validation=True)
logger = Logger()

# Task names for parameter lookup
APP_TASK_NAME_QUESTIONS = 'GenerateEvaluationQuestions'
APP_TASK_NAME_EXAMPLES = 'GenerateClauseExamples'

guidelines_repository = DynamoDBGuidelinesRepository(
    table_name=os.getenv("GUIDELINES_TABLE", "test-guidelines-table")
)
contract_type_repository = DynamoDBContractTypeRepository(
    table_name=os.getenv("CONTRACT_TYPES_TABLE", "test-contract-types-table")
)

# AI Content Generation Prompt Templates
QUESTIONS_GENERATION_PROMPT = """You are a Senior Specialist in Law and you are very skilled in understanding of contracts.
You work for company {company_name}.
You are working on establishing validation standards for contracts of type {contract_type}, having as parties involved the {other_party_type} and company {company_name} ({company_party_type}).
A contract contains several clauses.
As part of your work, you are defining criteria of whether contract clauses are in accordance with an example of gold standard wording.

The gold standard wording is the following:
<standard_wording>
{standard_wording}
</standard_wording>

Rules of thought process:
<rules_of_thought_process>
- Making deductions is forbidden
- Proposing premises is forbidden.
- Making generalizations is forbidden.
- Making implications/deductions about implicit content is forbidden.
- Asking questions about the usage of specific terms or specific phrases is forbidden.
- Asking questions that mention the standard draft wording is also forbidden.
</rules_of_thought_process>

Your task is to write questions you could ask about a clause of the contract to assess whether it is in accordance with the gold standard wording (the content between <standard_wording> tags).
Only ask questions that can be answered with "Yes" or "No".
Make sure each question validates a key statement that has not been checked by previous questions. Make sure every question you ask is answered as "Yes" if applied to the gold standard wording (the content between <standard_wording> tags).

CRITICAL LANGUAGE REQUIREMENT:
- ALL questions must be written ONLY in {language} language
- Do NOT mix languages or use any other language
- Every single question must be in {language}
- If you write a question in the wrong language, it will be rejected

IMPORTANT: You must write each question between <question_translated></question_translated> XML tags, in {language} language. This format is mandatory.

Start by identifying all key statements from the gold standard wording (the content between <standard_wording> tags). Write between <statements> tags.

You will have the assistance of a Critic that will doublecheck your questions.
Both you and the Critic need to perform the following steps for each key statement, in a loop. I will identify who (whether you or the Critic) is assigned each step.
- [You] Then before writing each question, take some time to think step by step on your next question, following the rules of thought process (the content between <rules_of_thought_process> tags). Make sure the question is answered as "Yes" if applied to the gold standard wording (the content between <standard_wording> tags). Write your thoughts between <thinking> tags
- [Critic] Apply the question to the gold standard wording (the content between <standard_wording> tags). Check if the question answered with "Not Sure", "No" or "Yes". Write Critic thoughts between <critic_analysis> tags
- [You] If the question was answered as "No" or "Not Sure" by the Critic once applied to the gold standard wording (the content between <standard_wording> tags), discard the question. Otherwise, write the question between <question_translated></question_translated> XML tags, in {language} language

CRITICAL: Each question must be wrapped in <question_translated></question_translated> tags and written in {language} language.

The number of questions should be determined by the complexity and content of the standard wording - simple clauses may need fewer questions, while complex clauses with multiple obligations, conditions, or requirements may need more questions to ensure comprehensive validation.

If {language} is Portuguese/Português, use format like:
<question_translated>A cláusula especifica claramente os termos de pagamento?</question_translated>
<question_translated>As obrigações de entrega estão definidas na cláusula?</question_translated>

If {language} is English, use format like:
<question_translated>Does the clause specify the payment terms clearly?</question_translated>
<question_translated>Are the delivery obligations defined in the clause?</question_translated>

Remember: ALL questions must be in {language} language only."""

EXAMPLES_GENERATION_PROMPT = """You are a Senior Specialist in Law and you are very skilled in understanding of contracts.
You work for company {company_name}.
You are working on establishing validation standards for contracts of type {contract_type}, having as parties involved the {other_party_type} and company {company_name} ({company_party_type}).

You have a gold standard wording for a specific clause type:
<standard_wording>
{standard_wording}
</standard_wording>

Your task is to generate 2-4 alternative wording examples that express the same legal concept as the gold standard wording but with different phrasing, formality levels, or detail levels.

Requirements:
- Examples should be legally accurate and complete
- Examples should demonstrate different ways to express the same concept
- Examples should be realistic and practical for use in contracts
- Examples should maintain the same legal intent as the gold standard wording

CRITICAL LANGUAGE REQUIREMENT:
- ALL examples must be written ONLY in {language} language
- Do NOT mix languages or use any other language
- Every single example must be in {language}
- If you write an example in the wrong language, it will be rejected

Write each example between separate <example></example> XML tags.

Think step by step about each example before writing it, considering:
- Different levels of formality (formal vs. plain language)
- Different levels of detail (comprehensive vs. concise)
- Different structural approaches (bullet points vs. paragraph form)
- Industry-specific variations while maintaining legal accuracy

Remember: ALL examples must be in {language} language only."""


def get_model_for_task(task_type: str) -> str:
    """Select appropriate model based on task complexity using app properties"""
    properties = AppPropertiesManager()

    task_name_mapping = {
        'questions_generation': APP_TASK_NAME_QUESTIONS,
        'examples_generation': APP_TASK_NAME_EXAMPLES,
    }

    task_name = task_name_mapping.get(task_type)
    if task_name:
        # Get task-specific model ID from Parameter Store
        return properties.get_parameter('LanguageModelId', task_name=task_name, default='amazon.nova-pro-v1:0')
    else:
        # Fallback to global model ID
        return properties.get_parameter('LanguageModelId', default='amazon.nova-pro-v1:0')


def generate_evaluation_questions(contract_type_id: str, clause_type_id: str, standard_wording: str) -> List[str]:
    """Generate evaluation questions for a specific guideline using LLM"""
    try:
        # Get contract type context
        contract_type = contract_type_repository.get_contract_type(contract_type_id)
        if not contract_type:
            raise ValueError(f"Contract type '{contract_type_id}' not found")

        # Get guideline for additional context
        guideline = guidelines_repository.get_guideline(contract_type_id, clause_type_id)
        if not guideline:
            raise ValueError(f"Guideline not found for contract type '{contract_type_id}' and clause type '{clause_type_id}'")

        # Normalize language name for better LLM understanding
        language = contract_type.default_language
        if language.lower() in ['pt', 'portuguese', 'português', 'portugues']:
            language_display = "Portuguese (Português)"
        elif language.lower() in ['en', 'english', 'inglês', 'ingles']:
            language_display = "English"
        else:
            language_display = language

        logger.info(f"Generating questions in language: {language_display}")

        # Build prompt with context
        prompt = QUESTIONS_GENERATION_PROMPT.format(
            company_name="[Company Name]",  # Generic placeholder
            contract_type=contract_type.name,
            other_party_type=contract_type.other_party_type,
            company_party_type=contract_type.company_party_type,
            standard_wording=standard_wording,
            language=language_display
        )

        # Get appropriate model
        model_id = get_model_for_task('questions_generation')

        # Call LLM with retry logic
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response_content, usage_data, stop_reason = invoke_llm(
                    prompt=prompt,
                    model_id=model_id,
                    temperature=0.7 + (attempt * 0.1),  # Increase temperature on retries
                    max_new_tokens=2048,
                    verbose=True
                )
                break
            except Exception as llm_error:
                logger.warning(f"LLM call attempt {attempt + 1} failed: {llm_error}")
                if attempt == max_retries:
                    raise ValueError(f"LLM service failed after {max_retries + 1} attempts: {llm_error}")
                continue

        # Parse questions from response
        questions = []
        import re

        # Log the raw response for debugging
        logger.info(f"LLM response content (first 500 chars): {response_content[:500]}")

        # Extract questions from XML tags
        question_matches = re.findall(r'<question_translated>(.*?)</question_translated>', response_content, re.DOTALL)

        # If no matches with the expected format, try alternative formats
        if not question_matches:
            logger.warning("No questions found with <question_translated> tags, trying alternative formats")

            # Try <question> tags as fallback
            question_matches = re.findall(r'<question>(.*?)</question>', response_content, re.DOTALL)

            # If still no matches, try to extract questions from numbered lists
            if not question_matches:
                # Look for numbered questions (1., 2., etc.)
                numbered_questions = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', response_content, re.DOTALL | re.MULTILINE)
                if numbered_questions:
                    question_matches = numbered_questions
                    logger.info(f"Found {len(numbered_questions)} numbered questions as fallback")

        for match in question_matches:
            question = match.strip()
            # Clean up the question text
            question = re.sub(r'\s+', ' ', question)  # Normalize whitespace
            question = question.replace('\n', ' ').strip()

            if question and len(question) <= 500 and question.endswith('?'):  # Validate length and format
                questions.append(question)

        # Log what we found
        logger.info(f"Extracted {len(questions)} valid questions from LLM response")

        # Ensure we have at least 1 question
        if not questions:
            logger.error(f"No valid questions were generated. Raw response: {response_content}")
            raise ValueError("No valid questions were generated from the LLM response. The response may not contain properly formatted questions.")

        logger.info(f"Generated {len(questions)} evaluation questions for guideline {contract_type_id}/{clause_type_id}")

        return questions

    except Exception as e:
        logger.error(f"Failed to generate evaluation questions: {str(e)}")
        raise


def generate_clause_examples(contract_type_id: str, clause_type_id: str, standard_wording: str) -> List[str]:
    """Generate alternative clause wording examples using LLM"""
    try:
        # Get contract type context
        contract_type = contract_type_repository.get_contract_type(contract_type_id)
        if not contract_type:
            raise ValueError(f"Contract type '{contract_type_id}' not found")

        # Get guideline for additional context
        guideline = guidelines_repository.get_guideline(contract_type_id, clause_type_id)
        if not guideline:
            raise ValueError(f"Guideline not found for contract type '{contract_type_id}' and clause type '{clause_type_id}'")

        # Normalize language name for better LLM understanding
        language = contract_type.default_language
        if language.lower() in ['pt', 'portuguese', 'português', 'portugues']:
            language_display = "Portuguese (Português)"
        elif language.lower() in ['en', 'english', 'inglês', 'ingles']:
            language_display = "English"
        else:
            language_display = language

        logger.info(f"Generating examples in language: {language_display}")

        # Build prompt with context
        prompt = EXAMPLES_GENERATION_PROMPT.format(
            company_name="[Company Name]",  # Generic placeholder
            contract_type=contract_type.name,
            other_party_type=contract_type.other_party_type,
            company_party_type=contract_type.company_party_type,
            standard_wording=standard_wording,
            language=language_display
        )

        # Get appropriate model
        model_id = get_model_for_task('examples_generation')

        # Call LLM with retry logic
        response_content, usage_data, stop_reason = invoke_llm(
            prompt=prompt,
            model_id=model_id,
            temperature=0.7,  # Higher temperature for creative generation
            max_new_tokens=2048,
            verbose=True
        )

        # Parse examples from response
        examples = []
        import re

        # Extract examples from XML tags
        example_matches = re.findall(r'<example>(.*?)</example>', response_content, re.DOTALL)

        for match in example_matches:
            example = match.strip()
            if example and len(example) <= 1000:  # Validate length
                examples.append(example)

        # Ensure we have at least 2 examples and at most 4
        if len(examples) < 2:
            raise ValueError("At least 2 examples must be generated")

        # Limit to 4 examples maximum
        examples = examples[:4]

        logger.info(f"Generated {len(examples)} clause examples for guideline {contract_type_id}/{clause_type_id}")

        return examples

    except Exception as e:
        logger.error(f"Failed to generate clause examples: {str(e)}")
        raise


def _validate_contract_type_exists(contract_type_id: str) -> ContractType:
    """Validate that contract type exists and is active"""
    contract_type = contract_type_repository.get_contract_type(contract_type_id)
    if not contract_type:
        available_types = contract_type_repository.get_contract_types()
        available_type_ids = [ct.contract_type_id for ct in available_types if ct.is_active]
        raise BadRequestError(f"Contract type '{contract_type_id}' not found. Available contract types: {available_type_ids}")

    return contract_type

@app.get("/guidelines")
def get_guidelines(contract_type_id: str, search: Optional[str] = None,
                  level: Optional[str] = None, limit: int = 50,
                  last_evaluated_key: Optional[str] = None):
    """List guidelines with filtering and pagination"""

    # Validate contract type exists
    contract_type = contract_type_repository.get_contract_type(contract_type_id)
    if not contract_type:
        available_types = contract_type_repository.get_contract_types()
        available_type_ids = [ct.contract_type_id for ct in available_types if ct.is_active]
        raise BadRequestError(f"Invalid contract type '{contract_type_id}'. Available contract types: {available_type_ids}")

    # Validate limit parameter
    if limit < 1 or limit > 100:
        raise BadRequestError("Limit must be between 1 and 100")

    # Parse last_evaluated_key if provided
    parsed_last_key = None
    if last_evaluated_key:
        try:
            import base64
            parsed_last_key = json.loads(base64.b64decode(last_evaluated_key).decode('utf-8'))
        except Exception:
            raise BadRequestError("Invalid last_evaluated_key format")

    try:
        result = guidelines_repository.list_guidelines(
            contract_type_id=contract_type_id,
            search=search,
            level=level,
            limit=limit,
            last_evaluated_key=parsed_last_key
        )

        # Encode last_evaluated_key for response
        encoded_last_key = None
        if result.get('last_evaluated_key'):
            import base64
            encoded_last_key = base64.b64encode(
                json.dumps(result['last_evaluated_key']).encode('utf-8')
            ).decode('utf-8')

        # Convert guidelines to response format
        guidelines_response = [
            GuidelineResponse.model_validate(guideline.model_dump()).model_dump(by_alias=True)
            for guideline in result['guidelines']
        ]

        return GuidelinesListResponse(
            guidelines=guidelines_response,
            last_evaluated_key=encoded_last_key,
            total_count=result['count']
        ).model_dump(by_alias=True)

    except Exception as e:
        logger.error(f"Failed to list guidelines: {e}")
        raise BadRequestError(f"Failed to list guidelines: {str(e)}")


@app.get("/guidelines/<contract_type_id>/<clause_type_id>")
def get_guideline(contract_type_id: str, clause_type_id: str):
    """Get specific guideline"""
    guideline = guidelines_repository.get_guideline(contract_type_id, clause_type_id)
    if not guideline:
        raise NotFoundError(f"Guideline not found for contract type '{contract_type_id}' and clause type '{clause_type_id}'")

    return GuidelineResponse.model_validate(guideline.model_dump()).model_dump(by_alias=True)

@app.post("/guidelines")
def create_guideline(request: CreateGuidelineRequest):
    """Create a new guideline"""
    # Validate contract type exists and is active
    _validate_contract_type_exists(request.contract_type_id)

    # Create guideline (clause_type_id will be auto-generated)
    now = datetime.now(timezone.utc).isoformat()
    guideline = Guideline(
        contract_type_id=request.contract_type_id,
        clause_type_id=None,  # Will be auto-generated
        name=request.name,
        standard_wording=request.standard_wording,
        level=request.level,
        evaluation_questions=request.evaluation_questions or [],
        examples=request.examples or [],
        created_at=now,
        updated_at=now
    )

    try:
        created_guideline = guidelines_repository.create_guideline(guideline)
        return GuidelineResponse.model_validate(created_guideline.model_dump()).model_dump(by_alias=True)
    except ValueError as e:
        raise BadRequestError(str(e))
    except Exception as e:
        logger.error(f"Failed to create guideline: {e}")
        raise BadRequestError("Failed to create guideline")

@app.put("/guidelines/<contract_type_id>/<clause_type_id>")
def update_guideline(contract_type_id: str, clause_type_id: str, request: UpdateGuidelineRequest):
    """Update an existing guideline"""
    # Check if guideline exists
    existing_guideline = guidelines_repository.get_guideline(contract_type_id, clause_type_id)
    if not existing_guideline:
        raise NotFoundError(f"Guideline not found for contract type '{contract_type_id}' and clause type '{clause_type_id}'")

    # Prepare updates dictionary
    updates = {}
    if request.name is not None:
        updates['name'] = request.name
    if request.standard_wording is not None:
        updates['standard_wording'] = request.standard_wording
    if request.level is not None:
        updates['level'] = request.level
    if request.evaluation_questions is not None:
        updates['evaluation_questions'] = request.evaluation_questions
    if request.examples is not None:
        updates['examples'] = request.examples

    # Always update the timestamp
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()

    try:
        updated_guideline = guidelines_repository.update_guideline(contract_type_id, clause_type_id, updates)
        return GuidelineResponse.model_validate(updated_guideline.model_dump()).model_dump(by_alias=True)
    except ValueError as e:
        raise BadRequestError(str(e))
    except Exception as e:
        logger.error(f"Failed to update guideline: {e}")
        raise BadRequestError("Failed to update guideline")

@app.delete("/guidelines/<contract_type_id>/<clause_type_id>")
def delete_guideline(contract_type_id: str, clause_type_id: str):
    """Delete a guideline"""
    try:
        success = guidelines_repository.delete_guideline(contract_type_id, clause_type_id)
        if not success:
            raise NotFoundError(f"Guideline not found for contract type '{contract_type_id}' and clause type '{clause_type_id}'")

        return {"message": f"Guideline deleted successfully for contract type '{contract_type_id}' and clause type '{clause_type_id}'"}

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to delete guideline: {e}")
        raise BadRequestError("Failed to delete guideline")
@app.post("/guidelines/<contract_type_id>/<clause_type_id>/generate-questions")
def generate_questions_endpoint(contract_type_id: str, clause_type_id: str, request: GenerateQuestionsRequest):
  """Generate evaluation questions for a specific guideline using AI"""

  logger.info(f"Starting question generation for contract_type_id={contract_type_id}, clause_type_id={clause_type_id}")

  # Validate contract type exists
  contract_type = contract_type_repository.get_contract_type(contract_type_id)
  if not contract_type:
    available_types = contract_type_repository.get_contract_types()
    available_type_ids = [ct.contract_type_id for ct in available_types if ct.is_active]
    raise BadRequestError(f"Invalid contract type '{contract_type_id}'. Available contract types: {available_type_ids}")

  # Validate guideline exists
  guideline = guidelines_repository.get_guideline(contract_type_id, clause_type_id)
  if not guideline:
    raise NotFoundError(f"Guideline not found for contract type '{contract_type_id}' and clause type '{clause_type_id}'")

  logger.info(f"Standard wording length: {len(request.standard_wording)} characters")

  try:
    # Generate evaluation questions using LLM
    questions = generate_evaluation_questions(
      contract_type_id=contract_type_id,
      clause_type_id=clause_type_id,
      standard_wording=request.standard_wording
    )

    logger.info(f"Successfully generated {len(questions)} questions")
    return GenerateQuestionsResponse(questions=questions).model_dump(by_alias=True)

  except ValueError as e:
    logger.error(f"Question generation validation error: {str(e)}")
    raise BadRequestError("Generation failed: Question generation failed - please try again")
  except Exception as e:
    logger.error(f"Failed to generate questions: {e}", exc_info=True)
    raise BadRequestError("Question generation failed - please try again")


@app.post("/guidelines/<contract_type_id>/<clause_type_id>/generate-examples")
def generate_examples_endpoint(contract_type_id: str, clause_type_id: str, request: GenerateExamplesRequest):
  """Generate alternative clause wording examples for a specific guideline using AI"""

  # Validate contract type exists
  contract_type = contract_type_repository.get_contract_type(contract_type_id)
  if not contract_type:
    available_types = contract_type_repository.get_contract_types()
    available_type_ids = [ct.contract_type_id for ct in available_types if ct.is_active]
    raise BadRequestError(f"Invalid contract type '{contract_type_id}'. Available contract types: {available_type_ids}")

  # Validate guideline exists
  guideline = guidelines_repository.get_guideline(contract_type_id, clause_type_id)
  if not guideline:
    raise NotFoundError(f"Guideline not found for contract type '{contract_type_id}' and clause type '{clause_type_id}'")

  try:
    # Generate clause examples using LLM
    examples = generate_clause_examples(
      contract_type_id=contract_type_id,
      clause_type_id=clause_type_id,
      standard_wording=request.standard_wording
    )

    return GenerateExamplesResponse(examples=examples).model_dump(by_alias=True)

  except ValueError as e:
    raise BadRequestError(f"Generation failed: {str(e)}")
  except Exception as e:
    logger.error(f"Failed to generate examples: {e}")
    raise BadRequestError("Example generation failed - please try again")


def handler(event, context: LambdaContext):
    return app.resolve(event, context)