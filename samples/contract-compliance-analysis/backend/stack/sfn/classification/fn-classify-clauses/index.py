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

import boto3
import json
import concurrent.futures
import os
from boto3.dynamodb.conditions import Attr
from collections import defaultdict
from more_itertools import divide, unique_everseen
import difflib

from llm import invoke_llm, supports_prompt_caching

SYSTEM_PROMPT_TEMPLATE = """You are a Senior Specialist in Law, very skilled in understanding of contracts, and you work for company {company_name}.
You are carefully reading a contract ({contract_type}), having as parties involved the {other_party_type} and company {company_name} ({company_party_type}).

You task is to say whether any of the following possible types is highly applicable to the clause: 
<possible_types>
{possible_types}
</possible_types>

Rules of thought process:
<rules_of_thought_process>
- Making deductions is forbidden
- Proposing premises is forbidden.
- Making generalizations is forbidden. 
- Making implications/deductions about implicit content is forbidden.
</rules_of_thought_process>

Examples:
<examples>
{examples}
</examples>

Follow these steps:
- Replicate between <clause_replica> tags the original text of the clause you are reading (the content between <current_clause> tags)
- For each possible type, look at the corresponding examples (the content between <examples> tags) and distill them into a definition for the clause type. Write all type / distillation pairs between a single <distilled_type_definition></distilled_type_definition> tag pair.  
- Thinking step by step and following the rules of thought process (the content between <rules_of_thought_process> tags), look at all possible types (the content between <possible_types> tags) one by one, together with each corresponding distilled type definition, and determine if a type is highly applicable for the clause you are reading (the content between <current_clause> tags). Write all your thoughts, in full, between <thinking> tags. 
- For your answer, write each highly applicable type between separate <type></type> tags, including an attribute 'reason' having the reason (write in {language}) of why you selected the type. For example: <type reason="reason for selecting the type">a type</type>. If none of the possible types is highly applicable, then write <no_highly_applicable_types/>
"""

from util import get_prompt_vars_dict, extract_first_item_from_tagged_list, extract_items_and_attributes_from_tagged_list

# Import Powertools
from aws_lambda_powertools import Logger

# Initialize Powertools logger
logger = Logger(service="contract-compliance-analysis")

VERBOSE_LLM = True
BEDROCK_MAX_CONCURRENCY = int(os.environ.get('BEDROCK_MAX_CONCURRENCY', 10))
PROMPT_VARS = os.environ.get('PROMPT_VARS', "")

dynamodb_client = boto3.resource("dynamodb")
guidelines_table = dynamodb_client.Table(os.environ['GUIDELINES_TABLE_NAME'])
clauses_table = dynamodb_client.Table(os.environ['CLAUSES_TABLE_NAME'])


def get_guidelines_clauses():
    logger.info('Getting guidelines from DynamoDB')
    clauses = []
    scan_kwargs = {}
    done = False
    start_key = None
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key

        response = guidelines_table.scan(
            FilterExpression=~Attr('complements_type').exists(),
            **scan_kwargs)

        clauses.extend(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None

    logger.info(f'{len(clauses)} types fetched from guidelines')
    if not clauses:
        raise RuntimeError('No clause types found, please run load_guidelines script')

    return clauses


class MalformedRequest(ValueError):
    pass


def parse_event(event):
    if "JobId" in event and "ClauseNumber" in event:
        job_id = event["JobId"]
        clause_number = event["ClauseNumber"]
    else:
        raise MalformedRequest("Unknown event structure")

    logger.info(f"Got job_id and execution_name from event: {job_id} {clause_number}")

    return job_id, clause_number


def generate_prompt(prompt_template, inputs):
    return prompt_template.format_map(defaultdict(str, **inputs))


ANSWER_TYPE_TAG = 'type'
ANSWER_REASON_ATTR = 'reason'


def build_tagged_examples_string(clause_types):
    examples_str = ""

    template = """<example><current_clause>{clause}</current_clause><corresponding_type>{type}</corresponding_type></example>\n"""

    for clause_type in clause_types:
        for example in clause_type['examples']:
            examples_str += generate_prompt(template, {"clause": example, "type": clause_type['name']})

    return examples_str


def classify_clause(clause, request_id, number_of_classification_prompts=1):
    if number_of_classification_prompts > 1:
        logger.info(f"Recursive call (number_of_classification_prompts = {number_of_classification_prompts}")

    clause_types = get_guidelines_clauses()

    # prompt_template = GROUP_CLASSIFICATION_PROMPT_TEMPLATE

    clause_type_name_to_id = {clause_type['name']: clause_type['type_id'] for clause_type in clause_types}

    clause_type_names = list(clause_type_name_to_id.keys())

    prompt_vars_dict = get_prompt_vars_dict(PROMPT_VARS)

    with concurrent.futures.ThreadPoolExecutor(max_workers=BEDROCK_MAX_CONCURRENCY) as executor:
        yes_answers = []
        ddb_values = []
        futures = []
        clause_types_groups = divide(number_of_classification_prompts, clause_types)

        logger.info(f"Number of clause_types_groups: {len(clause_types_groups)}")

        for i, clause_types_group in enumerate(clause_types_groups):
            # Converting iterator to list, otherwise items traversal would only work once
            clause_types_group = list(clause_types_group)

            examples_str = ""
            examples_str += build_tagged_examples_string(clause_types_group)

            possible_types_str = "\n".join([f"- {clause_type['name']}" for clause_type in clause_types_group])

            # Always build system prompt (guidelines) and user prompt (clause analysis)
            system_prompt = _build_system_prompt(
                possible_types_str, examples_str, prompt_vars_dict
            )
            user_prompt = _build_user_prompt(clause)
            
            # Enable caching only if model supports it
            enable_caching = supports_prompt_caching(prompt_vars_dict.get("llm_model_id", ''))

            futures.append(
                executor.submit(invoke_llm, prompt=user_prompt, temperature=0.01,
                                max_new_tokens=4096, model_id=prompt_vars_dict.get("llm_model_id", ''), 
                                verbose=VERBOSE_LLM, system_prompt=system_prompt, enable_caching=enable_caching)
            )

        llm_output_limit_detected = False

        for future in concurrent.futures.as_completed(futures):
            if llm_output_limit_detected:
                continue

            llm_response, model_usage, stop_reason = future.result()

            if stop_reason == "max_tokens":
                llm_output_limit_detected = True
                continue  # Not breaking the loop though, to make sure all Future executions are completed

            input_replica = extract_first_item_from_tagged_list(llm_response, 'clause_replica')

            items_attrs = extract_items_and_attributes_from_tagged_list(llm_response, ANSWER_TYPE_TAG,
                                                                        ANSWER_REASON_ATTR)

            for item_attr in items_attrs:
                classification_type, classification_reason = item_attr[ANSWER_TYPE_TAG], item_attr[ANSWER_REASON_ATTR]

                # Doing an approximate search over possible clause types, to cover the scenario where the LLM returns a
                # clause type that is not exactly worded as it is in the guidelines
                best_clause_type_match = difflib.get_close_matches(classification_type, clause_type_names, n=1)

                if best_clause_type_match:
                    type_name = best_clause_type_match[0]
                    type_id = clause_type_name_to_id[type_name]

                    parsed_result = {'type_id': type_id,
                                     'type_name': type_name,
                                     'input_replica': input_replica,
                                     'classification_reason': classification_reason,
                                     }

                    yes_answers.append(parsed_result)

                    ddb_values.append(
                        {
                            'type_id': str(type_id),
                            'type_name': type_name,
                            'classification_analysis': classification_reason,
                            'classification_request_id': request_id
                        }
                    )

        if llm_output_limit_detected:
            # Output longer than LLM max token limits.
            # To split input into more pieces and retry

            return classify_clause(clause, request_id, number_of_classification_prompts + 1)
        else:
            logger.info(f"LLM classification - yes answers:\n{json.dumps(yes_answers, indent=4, ensure_ascii=False)}")

            if ddb_values:
                ddb_values = list(unique_everseen(ddb_values, key=lambda d: d['type_id']))
                yes_answers = list(unique_everseen(yes_answers, key=lambda d: d['type_id']))
            else:
                ddb_values.append(
                    {
                        'type_id': 'UNKNOWN',
                        'classification_request_id': request_id
                    }
                )

            return ddb_values, yes_answers


def _build_system_prompt(possible_types_str, examples_str, prompt_vars_dict):
    """Build the system prompt with guidelines and examples (cacheable)."""
    return generate_prompt(SYSTEM_PROMPT_TEMPLATE, {
        'possible_types': possible_types_str,
        'examples': examples_str,
        'language': prompt_vars_dict.get('language', 'English'),
        'company_name': prompt_vars_dict.get('company_name', ''),
        'contract_type': prompt_vars_dict.get('contract_type', ''),
        'company_party_type': prompt_vars_dict.get('company_party_type', ''),
        'other_party_type': prompt_vars_dict.get('other_party_type', '')
    })


def _build_user_prompt(clause):
    """Build the user prompt with the specific clause to analyze."""
    return f"""This is the clause you are reading right now:
<current_clause>
{clause}
</current_clause>"""


@logger.inject_lambda_context(log_event=True)
def handler(event, context):
    # Extract Step Functions execution name and set as correlation ID
    job_id = event.get("JobId", "unknown")
    logger.set_correlation_id(job_id)  # Use JobId as correlation ID (which is the execution name)
    
    logger.info("Received event", extra={"event": event})

    job_id, clause_number = parse_event(event)
    request_id = context.aws_request_id

    response = clauses_table.get_item(
        Key={
            'job_id': job_id,
            'clause_number': clause_number
        }
    )
    clause_record = response.get('Item')
    logger.info(f"Clause record: {clause_record}")

    if not clause_record:
        return "MISSING"

    clause_context = ""

    ddb_values, yes_answers = classify_clause(clause_record['text'], request_id)

    clause_record['types'] = ddb_values

    ddb_response = clauses_table.put_item(Item=clause_record)

    logger.info("DynamoDB update response", extra={"ddb_response": ddb_response})

    return "OK"
