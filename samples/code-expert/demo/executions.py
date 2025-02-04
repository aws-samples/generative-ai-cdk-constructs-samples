#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import json

import streamlit as st

from args import Args
from utils import get_object_from_s3, get_step_functions_executions, get_step_functions_execution_details

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
EXECUTION_MARKDOWN_TEMPLATE = '''**Name:** {name}  
**Start date:** {start_date}  
**Status:** {status}'''
FINDING_MARKDOWN_TEMPLATE = '''**:material/description: Description:**  
{description}

**:material/prompt_suggestion: Suggestion:**  
{suggestion}'''


def execution_option_display(execution):
    return f"{execution['name']} ({execution['startDate'].strftime(DATE_FORMAT)}) - {execution['status']}"


def print_errors(errors):
    errors_by_file = {}
    for error in errors:
        if error['file'] in errors_by_file:
            errors_by_file[error['file']].append(error)
        else:
            errors_by_file[error['file']] = [error]
    for file, file_errors in errors_by_file.items():
        with st.expander(f'{file} ({len(file_errors)})'):
            for index, error in enumerate(file_errors):
                st.markdown(f"**Rule(s):** {', '.join(error['rules'])}")
                st.code(error['error'])
                if index != len(file_errors) - 1:  # Add a divider after each error but the last
                    st.divider()


def print_chart(findings):
    findings_by_rule = {}
    for finding in findings:
        if finding['rule'] in findings_by_rule:
            findings_by_rule[finding['rule']] += 1
        else:
            findings_by_rule[finding['rule']] = 1
    st.text('')  # Just to add some vertical space
    st.bar_chart({'data': findings_by_rule}, x_label='Number of findings', y_label='Rule', horizontal=True)


def print_findings(findings):
    findings_by_file = {}
    for finding in findings:
        if finding['file'] in findings_by_file:
            findings_by_file[finding['file']].append(finding)
        else:
            findings_by_file[finding['file']] = [finding]
    for file, file_findings in findings_by_file.items():
        with st.expander(f'{file} ({len(file_findings)})'):
            for index, finding in enumerate(file_findings):
                help = Args.rule_text_by_id[finding['rule']] if finding['rule'] in Args.rule_text_by_id else ''
                st.markdown(f"**Rule:** {finding['rule']}", help=help)
                st.code(finding['snippet'], language='java')
                st.markdown(FINDING_MARKDOWN_TEMPLATE.format(description=finding['description'],
                                                             suggestion=finding['suggestion']))
                if index != len(file_findings) - 1:  # Add a divider after each finding but the last
                    st.divider()


st.header('Executions', anchor=False)

if 'sorted_executions' not in st.session_state:
    with st.spinner(f'Loading executions...'):
        executions_result = get_step_functions_executions()
        sorted_executions = sorted(executions_result['executions'], key=lambda d: d['startDate'], reverse=True)
        st.session_state['sorted_executions'] = sorted_executions

column1, column2 = st.columns([9, 1], vertical_alignment='bottom')
selected_execution = column1.selectbox('Executions',
                                       st.session_state.sorted_executions,
                                       index=None,
                                       format_func=execution_option_display,
                                       placeholder='Choose an execution',
                                       label_visibility='hidden')
refresh_button = column2.button('',
                                icon=':material/refresh:',
                                use_container_width=True)
if refresh_button:
    del st.session_state['sorted_executions']
    st.rerun()

if selected_execution:
    st.markdown(EXECUTION_MARKDOWN_TEMPLATE.format(name=selected_execution['name'],
                                                   status=selected_execution['status'],
                                                   start_date=selected_execution['startDate'].strftime(DATE_FORMAT)))
    if selected_execution['status'] == 'SUCCEEDED':
        with st.spinner(f'Loading findings...'):
            execution_result = get_step_functions_execution_details(selected_execution['executionArn'])
            execution_output = json.loads(execution_result['output'])
            execution_findings_str = get_object_from_s3(execution_output['processFindings']['bucket'],
                                                        execution_output['processFindings']['key'])
        all_findings = json.loads(execution_findings_str)
        if len(all_findings):
            st.download_button('Download findings',
                               execution_findings_str,
                               file_name=f"{selected_execution['name']}.json",
                               mime='application/json',
                               icon=':material/download:')
            st.subheader(f'Findings ({len(all_findings)}):', anchor=False)
            print_chart(all_findings)
            print_findings(all_findings)
        else:
            st.info('No findings')
        if 'errors_key' in execution_output['processFindings']:
            with st.spinner(f'Loading errors...'):
                errors_str = get_object_from_s3(execution_output['processFindings']['bucket'],
                                                execution_output['processFindings']['errors_key'])
                all_errors = json.loads(errors_str)
                if len(all_errors):
                    st.subheader(f':red[Errors ({len(all_errors)}):]', anchor=False)
                    print_errors(all_errors)
