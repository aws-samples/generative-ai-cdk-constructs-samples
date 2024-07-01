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

import awswrangler as wr
import pandas as pd
import argparse
import boto3

DEFAULT_BACKEND_STACK_NAME = "MainBackendStack"

DDB_COLUMNS = {
    'ID': {'name': 'type_id', 'type': str},
    'NAME': {'name': 'name', 'type': str},
    'WORDING': {'name': 'standard_wording', 'type': str},
    'LEVEL': {'name': 'level', 'type': str},
    'EVALUATION_QUESTIONS': {'name': 'evaluation_questions', 'type': str},
    'EXAMPLES': {'name': 'examples', 'type': str},  # actual type is <list<str>>
}
GUIDELINES_EXCEL_COLUMN_TO_DDB_COLUMN = {
    'Id': 'ID',
    'Clause Type': 'NAME',
    'Standard Wording': 'WORDING',
    'Impact': 'LEVEL',
    'Evaluation Questions': 'EVALUATION_QUESTIONS',
}
EXAMPLES_EXCEL_COLUMN_TO_DDB_COLUMN = {
    'Id': 'ID',
    'Example': 'EXAMPLES',
}
VALID_IMPACT_VALUES = ['low', 'medium', 'high']


def get_guidelines_ddb_table_name(backend_stack_name):
    cf_client = boto3.client('cloudformation')

    response = cf_client.describe_stacks(StackName=backend_stack_name)
    outputs = response["Stacks"][0]["Outputs"]

    for output in outputs:
        key_name = output["OutputKey"]
        if key_name == "GuidelinesTableName":
            table_name = output["OutputValue"]

    return table_name


def load_into_table(guidelines_file_path, ddb_guidelines_table):
    # Guidelines spreadsheet
    excel_file = pd.ExcelFile(guidelines_file_path)
    type_converters = {excel_column: DDB_COLUMNS[ddb_column]['type'] for excel_column, ddb_column in
                       GUIDELINES_EXCEL_COLUMN_TO_DDB_COLUMN.items()}
    filtered_columns = list(GUIDELINES_EXCEL_COLUMN_TO_DDB_COLUMN.keys())
    guidelines_df = pd.read_excel(excel_file, 'Taxonomy', converters=type_converters)[filtered_columns]

    invalid_rows = guidelines_df[~guidelines_df['Impact'].isin(VALID_IMPACT_VALUES)]
    if not invalid_rows.empty:
        invalid_values = invalid_rows['Impact'].unique()
        raise ValueError(
            f"The following invalid values were found in the 'Impact' column: {', '.join(invalid_values)}")

    print("Guidelines table name: " + ddb_guidelines_table)

    print("Removing existing records ...")
    df = wr.dynamodb.read_items(
        table_name=ddb_guidelines_table,
        columns=[DDB_COLUMNS['ID']['name']],
        allow_full_scan=True,
        consistent=True
    )
    dict_list = df.to_dict(orient='records')
    wr.dynamodb.delete_items(
        table_name=ddb_guidelines_table,
        items=dict_list
    )
    print("Adding records from spreadsheet ...")

    column_names = {excel_column: DDB_COLUMNS[ddb_column]['name'] for excel_column, ddb_column in
                    GUIDELINES_EXCEL_COLUMN_TO_DDB_COLUMN.items()}
    guidelines_df = guidelines_df.rename(columns=column_names)
    guidelines_df = guidelines_df[guidelines_df['type_id'].notnull()]

    # Convert multiline question string into list
    evaluate_questions_col_name = DDB_COLUMNS['EVALUATION_QUESTIONS']['name']
    guidelines_df[evaluate_questions_col_name] = guidelines_df[evaluate_questions_col_name].astype(str)
    guidelines_df[evaluate_questions_col_name] = guidelines_df[evaluate_questions_col_name].str.split('\n')
    guidelines_df[evaluate_questions_col_name] = guidelines_df[evaluate_questions_col_name].apply(
        lambda x: [line.strip() for line in x if line.strip()])

    # Examples spreadsheet
    type_converters = {excel_column: DDB_COLUMNS[ddb_column]['type'] for excel_column, ddb_column in
                       EXAMPLES_EXCEL_COLUMN_TO_DDB_COLUMN.items()}
    filtered_columns = list(EXAMPLES_EXCEL_COLUMN_TO_DDB_COLUMN.keys())
    examples_df = pd.read_excel(excel_file, 'Examples', converters=type_converters)[filtered_columns]
    column_names = {excel_column: DDB_COLUMNS[ddb_column]['name'] for excel_column, ddb_column in
                    EXAMPLES_EXCEL_COLUMN_TO_DDB_COLUMN.items()}

    examples_df = examples_df.rename(columns=column_names)

    # Group examples by type_id
    examples_df = examples_df.groupby(DDB_COLUMNS['ID']['name'])[DDB_COLUMNS['EXAMPLES']['name']].apply(list)

    # Left join guidelines and examples on type_Id
    result = pd.merge(guidelines_df, examples_df, how='left', on='type_id')

    # Write to DynamoDB
    wr.dynamodb.put_df(df=result, table_name=ddb_guidelines_table)


# Script invocation example:
# python load_guidelines.py --guidelines_file_path ../guidelines/guidelines_example.xlsx
if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--guidelines_file_path", type=str, dest="guidelines_file_path", required=True,
                            help="Guidelines Excel sheet file")
    arg_parser.add_argument("--backend_stack_name", type=str, dest="backend_stack_name",
                            default=DEFAULT_BACKEND_STACK_NAME,
                            required=False, help="CloudFormation Backend Stack Name")
    args = arg_parser.parse_args()

    ddb_guidelines_table = get_guidelines_ddb_table_name(args.backend_stack_name)

    load_into_table(args.guidelines_file_path, ddb_guidelines_table)
