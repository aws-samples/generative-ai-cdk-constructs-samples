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

import sys
import os
import argparse
import pandas as pd
from collections import defaultdict
from utils.llm import invoke_llm, extract_items_from_tagged_list

# Add parent folder to the `sys.path`, in order to properly import modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from stack.config.properties import AppProperties

CLAUSE_TYPE_ID_COL = 'Id'
CLAUSE_TYPE_NAME_COL = 'Clause Type'
CLAUSE_TYPE_STD_WORDING_COL = 'Standard Wording'

GUIDELINES_EXCEL_COLUMN_TO_TYPE = {
    CLAUSE_TYPE_ID_COL: str,
    CLAUSE_TYPE_NAME_COL: str,
    CLAUSE_TYPE_STD_WORDING_COL: str,
}

CLAUDE_HAIKU_MODEL_ID = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

PROMPT_TEMPLATE = """You are a Senior Specialist in Law and you are very skilled in understanding of contracts.
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
Make sure each question validates a key statement that has not been checked by previous questions. Make sure every question you ask is answered as "Yes" if applied to the gold standard wording (the content between <standard_wording> tags). Write each question, one by one, between separate <question></question> XML tags

Start by identifying all key statements from the gold standard wording (the content between <standard_wording> tags). Write between <statements> tags.

You will have the assistance of a Critic that will doublecheck your questions.
Both you and the Critic need to perform the following steps for each key statement, in a loop. I will identify who (whether you or the Critic) is assigned each step.  
- [You] Then before writing each question, take some time to think step by step on your next question, following the rules of thought process (the content between <rules_of_thought_process> tags). Make sure the question is answered as "Yes" if applied to the gold standard wording (the content between <standard_wording> tags). Write your thoughts between <thinking> tags
- [Critic] Apply the question to the gold standard wording (the content between <standard_wording> tags). Check if the question answered with "Not Sure", "No" or "Yes". Write Critic thoughts between <critic_analysis> tags
- [You] If the question was answered as "No" or "Not Sure" by the Critic once applied to the gold standard wording (the content between <standard_wording> tags), discard the question. Otherwise, write the question between <question></question> XML tags, in {language}
"""

def generate_prompt(prompt_template, inputs):
    return prompt_template.format_map(defaultdict(str, **inputs))


def generate_questions(guidelines_file_path, properties: AppProperties):
    excel_file = pd.ExcelFile(guidelines_file_path)
    filtered_columns = list(GUIDELINES_EXCEL_COLUMN_TO_TYPE.keys())
    guidelines_df = pd.read_excel(excel_file, 'Taxonomy', converters=GUIDELINES_EXCEL_COLUMN_TO_TYPE)[filtered_columns]
    guidelines_df = guidelines_df[guidelines_df[CLAUSE_TYPE_ID_COL].notnull()]
    clause_type_ids = []
    clause_type_names = []
    generated_questions = []

    for index, guidelines_clause_type in guidelines_df.iterrows():
        number_attempts = 6
        questions_list = []

        # Generate questions, already prepared for retries in case the LLM refuses to perform the task
        while not questions_list and number_attempts > 0:

            number_attempts -= 1

            questions_generation_prompt = generate_prompt(PROMPT_TEMPLATE, {
                'standard_wording': guidelines_clause_type[CLAUSE_TYPE_STD_WORDING_COL],
                'language': properties.get_value('language'),
                'company_name': properties.get_value('company_name'),
                'contract_type': properties.get_value('contract_type'),
                'company_party_type': properties.get_value('company_party_type'),
                'other_party_type': properties.get_value('other_party_type')
            })

            if number_attempts <= 3:
                # Fallback to Haiku, in case current model refuses to discuss about Legal
                llm_output, usage_data, stop_reason = invoke_llm(questions_generation_prompt, temperature=0.3, model_id=CLAUDE_HAIKU_MODEL_ID,
                                        verbose=args.verbose)
            else:
                llm_output, usage_data, stop_reason = invoke_llm(questions_generation_prompt, temperature=0.3,
                                        model_id=properties.get_value("llm_model_id"), verbose=args.verbose)

            questions_list = extract_items_from_tagged_list(llm_output, "question")

            if not questions_list:
                print(">>> No question generated. To retry")

            clause_type_ids.append(guidelines_clause_type[CLAUSE_TYPE_ID_COL])
            clause_type_names.append(guidelines_clause_type[CLAUSE_TYPE_NAME_COL])
            generated_questions.append("\n".join(questions_list))

        print(f"{guidelines_clause_type[CLAUSE_TYPE_ID_COL]} | {guidelines_clause_type[CLAUSE_TYPE_NAME_COL]}")
        print(">> ", guidelines_clause_type[CLAUSE_TYPE_STD_WORDING_COL])
        print(" - " + "\n - ".join(questions_list))

    # Create a DataFrame from the data
    questions_df = pd.DataFrame({
        'Id': clause_type_ids,
        'Clause Type': clause_type_names,
        'Evaluation Questions': generated_questions
    })

    # Specify the Excel file path
    excel_file_path = 'evaluation_questions.xlsx'
    # Save the DataFrame to an Excel file
    questions_df.to_excel(excel_file_path, index=False)
    print(f'Questions saved on Excel file: {excel_file_path}')


# Script invocation example:
# python generate_evaluation_questions.py --guidelines_file_path ../guidelines/guidelines_example.xlsx
if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--guidelines_file_path", type=str, dest="guidelines_file_path", required=True,
                            help="Guidelines Excel sheet file")
    arg_parser.add_argument('--properties', type=str, default="../app_properties.yaml",
                            help=f'App properties YAML file')
    arg_parser.add_argument('--verbose', action='store_true',
                            help='Enable verbose output for LLM calls')

    args = arg_parser.parse_args()

    app_properties = AppProperties(args.properties)

    generate_questions(args.guidelines_file_path, app_properties)
