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
import boto3
from boto3.dynamodb.conditions import Key
from collections import defaultdict
from llm import invoke_llm
from util import extract_first_item_from_tagged_list, extract_items_from_tagged_list
from app_properties_manager import AppPropertiesManager
from repository.dynamo_db_contract_type_repository import DynamoDBContractTypeRepository

# Task name for parameter lookup
APP_TASK_NAME = 'ContractEvaluation'

# Import Powertools
from aws_lambda_powertools import Logger

# Initialize Powertools logger
logger = Logger(service="contract-compliance-analysis")

CLAUSE_EVALUATION_PROMPT_TEMPLATE = """You are a Senior Specialist in Law, very skilled in understanding of contracts, and you work for company {company_name}.
You are carefully reading a contract ({contract_type}), having as parties involved the {other_party_type} and company {company_name} ({company_party_type}).

Rules of thought process:
<rules_of_thought_process>
- Making deductions is forbidden
- Proposing premises is forbidden.
- Making generalizations is forbidden.
- Making implications/deductions about implicit content is forbidden.
- If you don't know the answer to a question, answer 'Not sure'.
<rules_of_thought_process>

The contract clause is the following:
<clause>
{clause}
</clause>

Excerpt from the contract where the clause is included:
<contract>
{context}
</contract>

The ascending clauses according to the contract hierarchy may provide more context to the clause and complement the information in the clause.

Your task is read a contract clause and answer a series of questions about the clause.

Questions:
<questions>
{questions}
</questions>

Please look at each question one by one, having all your output placed inside separate <answering></answering> tags. This is the expected schema of your response:
<response_schema>
    <answering><question_replica></<question_replica><reasoning_translated>...</reasoning_translated><answer_english>...<answer_english><answer_translated>...</answer_translated></answering>
    <answering><question_replica></<question_replica><reasoning_translated>...</reasoning_translated><answer_english>...<answer_english><answer_translated>...</answer_translated></answering>
    ...
    <answering><question_replica></<question_replica><reasoning_translated>...</reasoning_translated><answer_english>...<answer_english><answer_translated>...</answer_translated></answering>
<response_schema>

For each question, follow these steps:
- Replicate the question between <question_replica> tags .
- Take a deep breath and think step by step on the answer to the question, following the rules of thought process (the content between <rules_of_thought_process> tags). The answer must be fully grounded in the contract clause (the content between <clause> tags) and complemented if needed with the context from ascendings clause in the contract. Write between <reasoning_translated> tags your thoughts in the language specified by ISO code "{language}".
- Write between <answer_english> tags your answer as "Not sure", "Yes" or "No" (always in English)
- Write between <answer_translated> tags your answer translated to the language specified by ISO code: {language}
"""

PROMPT_VARS = os.environ.get('PROMPT_VARS', "")

clauses_table = boto3.resource('dynamodb').Table(os.environ['CLAUSES_TABLE_NAME'])
guidelines_table = boto3.resource('dynamodb').Table(os.environ['GUIDELINES_TABLE_NAME'])


def get_clause(job_id, clause_number):
    clause_item = clauses_table.get_item(Key={
        "job_id": job_id,
        "clause_number": clause_number,
    })
    if "Item" not in clause_item:
        logger.error("Clause not found")
        raise ValueError("Clause not found")
    return clause_item["Item"]


def get_clause_context(job_id, clause_number):
    projection_expression = "#cn, #txt"
    expression_attribute_names = {
        "#cn": "clause_number",
        "#txt": "text"
    }

    results = clauses_table.query(
        KeyConditionExpression=Key('job_id').eq(job_id) & Key('clause_number').between(max(0, clause_number - 20),
                                                                                       clause_number),
        ProjectionExpression=projection_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ScanIndexForward=True,
    )
    context = "\n".join([item['text'] for item in results['Items']]) if len(results) else ""

    logger.info(f"Context: {context}")

    return context


def get_guidelines_rule(contract_type_id, clause_type_id):
    """
    Get guidelines rule using composite key (contract_type_id, clause_type_id).

    Args:
        contract_type_id: Contract type identifier (e.g., "service-agreement")
        clause_type_id: Clause type identifier (e.g., "payment-terms")

    Returns:
        Guidelines rule item from DynamoDB

    Raises:
        ValueError: If rule is not found for the given contract and clause type
    """
    rule_item = guidelines_table.get_item(Key={
        "contract_type_id": contract_type_id,
        "clause_type_id": clause_type_id,
    })
    if "Item" not in rule_item:
        logger.error(f"Clause type {clause_type_id} not found for contract type {contract_type_id}")
        raise ValueError(f"Clause type {clause_type_id} not found for contract type {contract_type_id}")
    rule = rule_item["Item"]
    return rule


def build_questions_string(questions):
    questions_str = ""
    for question in questions:
        questions_str += f'<question>{question}</question>\n'

    return questions_str


def generate_prompt(prompt_template, inputs):
    return prompt_template.format_map(defaultdict(str, **inputs))


def run_evaluation(clause, clause_context, rule, properties, contract_type_id, output_language="en"):
    """
    Run evaluation of a clause against guidelines rules using contract type-specific data.

    Args:
        clause: Clause data from DynamoDB
        clause_context: Context from surrounding clauses
        rule: Guidelines rule for evaluation
        properties: AppPropertiesManager instance
        contract_type_id: Contract type identifier
        output_language: ISO language code for output

    Returns:
        Dictionary with evaluation results (compliant, analysis)
    """
    questions = rule['evaluation_questions']

    # Get contract type-specific data from ContractTypesTable
    contract_type_repo = DynamoDBContractTypeRepository(table_name=os.environ.get('CONTRACT_TYPES_TABLE'))
    contract_data = contract_type_repo.get_contract_type(contract_type_id)
    
    if not contract_data:
        raise ValueError(f"Contract type '{contract_type_id}' not found")
    if not contract_data.is_active:
        raise ValueError(f"Contract type '{contract_type_id}' is not active")

    evaluation_prompt = generate_prompt(CLAUSE_EVALUATION_PROMPT_TEMPLATE, {
        'clause': clause["text"],
        'context': clause_context,
        'questions': build_questions_string(questions),
        'language': output_language,
        'company_name': properties.get_parameter('CompanyName', default=''),
        'contract_type': contract_data.description or contract_data.name,
        'company_party_type': contract_data.company_party_type,
        'other_party_type': contract_data.other_party_type
    })

    logger.info(f"Answer prompt: {evaluation_prompt}")

    # Get model ID from Parameter Store
    model_id = properties.get_parameter('LanguageModelId', task_name=APP_TASK_NAME, default='us.amazon.nova-pro-v1:0')

    llm_response, model_usage, stop_reason = invoke_llm(
        prompt=evaluation_prompt,
        model_id=model_id,
        temperature=0.01,
        max_new_tokens=2000,
        verbose=True
    )

    answering_steps = extract_items_from_tagged_list(llm_response, "answering")

    compliant = True
    analysis = []

    for i, answering_step in enumerate(answering_steps):
        question = extract_first_item_from_tagged_list(answering_step, "question_replica")
        reasoning = extract_first_item_from_tagged_list(answering_step, "reasoning_translated")
        answer = extract_first_item_from_tagged_list(answering_step, "answer_translated")
        answer_english = extract_first_item_from_tagged_list(answering_step, "answer_english")
        analysis.append(f"Q{i + 1}: {question}\n{answer}: {reasoning}")

        if not answer_english.lower().strip().startswith("yes"):
            compliant = False

    all_analysis_str = "\n\n".join(analysis)

    return {
        "compliant": compliant,
        "analysis": all_analysis_str,
    }


def update_clause(clause):
    clauses_table.update_item(
        Key={
            "job_id": clause["job_id"],
            "clause_number": clause["clause_number"],
        },
        UpdateExpression="SET #types = :types",
        ExpressionAttributeNames={
            "#types": "types",
        },
        ExpressionAttributeValues={
            ":types": clause["types"],
        }
    )


@logger.inject_lambda_context(log_event=True)
def handler(event, context):
    """Lambda to evaluate contract clauses against guidelines rules
    """
    # Extract Step Functions execution name and set as correlation ID
    job_id = event.get("JobId", "unknown")
    logger.set_correlation_id(job_id)  # Use JobId as correlation ID (which is the execution name)

    logger.info("Received event", extra={"event": event})
    clause = get_clause(event["JobId"], event["ClauseNumber"])
    logger.info("Retrieved clause", extra={"clause_number": event["ClauseNumber"], "has_types": "types" in clause})
    contract_type_id = event.get("ContractTypeId")  # Get contract type from event
    output_language = event.get("OutputLanguage", "en")  # Get ISO language code from event
    request_id = context.aws_request_id

    if not contract_type_id:
        logger.error("ContractTypeId not provided in event")
        raise ValueError("ContractTypeId is required")

    # Initialize properties manager
    properties = AppPropertiesManager(cache_ttl=0)

    if "types" not in clause:
        logger.error("Missing types in clause")
        raise ValueError("Missing types in clause")

    clause_context = get_clause_context(event["JobId"], event["ClauseNumber"])

    for type_ in clause["types"]:
        clause_type_id = type_["type_id"]  # This is actually the clause_type_id in the new schema
        try:
            rule = get_guidelines_rule(contract_type_id, clause_type_id)
            logger.info("Processing rule", extra={
                "contract_type_id": contract_type_id,
                "clause_type_id": clause_type_id,
                "rule_name": rule.get("name", "unknown")
            })
        except ValueError:
            logger.warning("Rule not found, skipping", extra={
                "contract_type_id": contract_type_id,
                "clause_type_id": clause_type_id
            })
            continue  # rule not found, skip it.

        eval_result = run_evaluation(clause, clause_context, rule, properties, contract_type_id, output_language)
        logger.info("Evaluation completed", extra={
            "contract_type_id": contract_type_id,
            "clause_type_id": clause_type_id,
            "compliant": eval_result["compliant"]
        })
        type_["compliant"] = eval_result["compliant"]
        type_["analysis"] = eval_result["analysis"]
        type_["level"] = rule["level"]
        type_["evaluation_request_id"] = request_id

    update_clause(clause)
    logger.info("Clause evaluation completed", extra={"clause_number": event["ClauseNumber"]})

    return {
        "Status": "OK"
    }
