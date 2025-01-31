#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import re
import uuid

import streamlit as st

from utils import upload_file_to_s3, start_step_functions_execution

MODELS_CRIS = {  # cross-region inference
    "us.anthropic.claude-3-5-haiku-20241022-v1:0": "Claude 3.5 Haiku",
    "us.anthropic.claude-3-5-sonnet-20240620-v1:0": "Claude 3.5 Sonnet",
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0": "Claude 3.5 Sonnet v2",
    "us.amazon.nova-micro-v1:0": "Nova Micro",
    "us.amazon.nova-lite-v1:0": "Nova Lite",
    "us.amazon.nova-pro-v1:0": "Nova Pro",
}
MODELS_NO_CRIS = {
    "anthropic.claude-3-haiku-20240307-v1:0": "Claude 3 Haiku",
    "anthropic.claude-3-5-haiku-20241022-v1:0": "Claude 3.5 Haiku",
    "anthropic.claude-3-5-sonnet-20240620-v1:0": "Claude 3.5 Sonnet",
    "anthropic.claude-3-5-sonnet-20241022-v2:0": "Claude 3.5 Sonnet v2",
    "amazon.nova-micro-v1:0": "Nova Micro",
    "amazon.nova-lite-v1:0": "Nova Lite",
    "amazon.nova-pro-v1:0": "Nova Pro",
}


def generate_execution_name(filename):
    filename_no_extension = filename.rsplit(".", maxsplit=1)[0]
    filename_allowed_chars = re.sub("[^a-zA-Z0-9_-]+", "", filename_no_extension)
    suffix = str(uuid.uuid4())[:8]
    return f"{filename_allowed_chars[:70]}_{suffix}"


st.header("Start execution", anchor=False)

single_element_container = st.empty()
with single_element_container.container():
    uploaded_file = st.file_uploader("Repository zip file", type="zip")
    multiple_evaluation = st.checkbox(
        "Multiple evaluation", value=True, help="Evaluate multiple rules in one model invocation"
    )
    cris = st.checkbox("Cross-region inference", value=False,
                       help="Distribute traffic across multiple AWS Regions, enabling higher throughput")
    models = MODELS_CRIS if cris else MODELS_NO_CRIS
    model_id = st.selectbox(
        "Model", models.keys(), index=None, format_func=lambda x: models[x], placeholder="Choose a model"
    )
    start_button = st.button("Start new execution", type="primary", disabled=not uploaded_file or not model_id)

if start_button:
    with single_element_container, st.spinner(f"Uploading file..."):
        execution_name = generate_execution_name(uploaded_file.name)
        repo_key = upload_file_to_s3(execution_name, uploaded_file.getvalue())
    with single_element_container, st.spinner(f"Starting new execution..."):
        execution_arn = start_step_functions_execution(
            execution_name,
            {
                "repo_key": repo_key,
                "model_id": model_id,
                "multiple_evaluation": multiple_evaluation,
            },
        )
    if execution_arn:
        # Remove the executions from the session state so that the new execution is included
        if "sorted_executions" in st.session_state:
            del st.session_state["sorted_executions"]
        single_element_container.success(f"New execution **{execution_name}** started!")
    else:
        single_element_container.error("Error starting new execution")
