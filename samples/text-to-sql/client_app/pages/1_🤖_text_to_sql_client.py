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
# Standard library imports
from io import BytesIO
import os
import re
import json
import base64
import uuid
import time
import requests
import streamlit as st
from dotenv import load_dotenv
from st_pages import add_indentation
import boto3
# Local imports
from common.cognito_helper import CognitoHelper
from common.streamlit_utils import hide_deploy_button

# ========================================================================================
# [Model] Load configuration and environment variables
# ========================================================================================
# Load environment variables from .env file
load_dotenv()

# Configure Queue
FEEDBACK_QUEUE_URL = os.environ.get("FEEDBACK_QUEUE")
TEXT_TO_SQL_API_ENDPOINT = os.environ.get("API_ENDPOINT")
FEEDBACK_ENDPOINT = os.environ.get("FEEDBACK_ENDPOINT")
RESULT_QUEUE_URL = os.environ.get("RESULT_QUEUE")
CONFIG_BUCKET = os.environ.get("CONFIG_BUCKET")


poll_feedback_queue = True
st.session_state["poll_feedback_queue"] = poll_feedback_queue
poll_result_queue = True
st.session_state["poll_result_queue"] = poll_result_queue
start_next_question = True
st.session_state["start_next_question"] = start_next_question

reformulated_ques_key = "REFORMULATED_Q "
generated_query_key = "GENERATED_Q "

sqs = boto3.client('sqs')
# ========================================================================================
# [Response]: Long Polling
# ========================================================================================


def receive_messages():
    # Long poll for messages
    response = sqs.receive_message(
        QueueUrl=FEEDBACK_QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=3  # Long polling for up to 20 seconds
    )
    # Check if messages are available
    if 'Messages' in response:
        messages = response['Messages']
        for message in messages:
            # Display the message body on the UI
            message_body = json.loads(message['Body'])

            print(f"Message received:: {message_body}")
            # if(st.session_state["unique_id"]==)

            reformulated_question = message_body.get(
                'reformualted_question', {}).get('value', '')
            st.session_state["reformulated_question"] = reformulated_question

            print(f'set reformulated_question :: {reformulated_question} ')
            original_user_question = message_body.get(
                'user_question', {}).get('value', '')
            st.session_state["original_user_question"] = original_user_question

            execute_sql_strategy = message_body.get(
                'execute_sql_strategy', {}).get('value', '')
            st.session_state["execute_sql_strategy"] = execute_sql_strategy

            print(f'set original_user_question :: {original_user_question} ')

            generated_query = message_body.get('generated_query', None)
            st.session_state["generated_query"] = generated_query

            print(f'generated_query :: {generated_query} ')
            task_token = message_body.get('TaskToken', None)
            st.session_state["task_token"] = task_token

            print(f'task_token :: {task_token} ')
            assitatnt_response = ""
            if generated_query:
                with st.chat_message("assistant"):
                    assitatnt_response = " The Generated query is :: "+generated_query + \
                        " If you  fine with the generated question , Please type yes, if not then please enter the new query starting with "+generated_query_key
                    st.markdown(assitatnt_response)
                st.session_state["poll_result_queue"] = True
                # st.session_state["poll_feedback_queue"] =  False

            elif reformulated_question:
                with st.chat_message("assistant"):
                    assitatnt_response = " Reformulated question is :: "+reformulated_question + \
                        " The question has been reformulated as per the DB tables. If you are fine with the reformulated question , Please type yes, if not then please enter the question starting with "+reformulated_ques_key
                    st.markdown(assitatnt_response)
            else:
                with st.chat_message("assistant"):
                    st.markdown(
                        "No reformulated question found in the message. proceding with query generation..")

            print(" Message displayed...")
            st.session_state.messages.append(
                {"role": "assistant", "content": assitatnt_response})

            # Delete the processed message from the queue
            print(" Deleting the message...")
            sqs.delete_message(
                QueueUrl=FEEDBACK_QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )

    else:
        print("No messages in the queue, polling..")


def receive_result():
    # Long poll for messages
    response = sqs.receive_message(
        QueueUrl=RESULT_QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=4  # Long polling for up to 20 seconds
    )
    # Check if messages are available
    if 'Messages' in response:
        messages = response['Messages']
        for message in messages:
            # Display the message body on the UI
            result_received = True
            message_body = json.loads(message['Body'])

            print(f"Result received:")
            # if(st.session_state["unique_id"]==)
            result = message_body.get('result', {}).get('value', '')
            if result:
                with st.chat_message("assistant"):
                    st.markdown(result)
                st.session_state.messages.append(
                    {"role": "assistant", "content": result})

            else:
                with st.chat_message("assistant"):
                    resp = "My apologies , something went wrong. Not able to generate the query result ."
                    st.markdown(resp)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": resp})

            print(" Result displayed...")

            # Delete the processed message from the queue
            print(" Deleting the result message...")
            sqs.delete_message(
                QueueUrl=RESULT_QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )
            st.session_state["start_next_question"] = True
            st.session_state["poll_result_queue"] = False
            st.session_state["poll_feedback_queue"] = False

            print(" Stop polling for result")
            print(" Stop polling for feedback")
    else:
        print("No result in the queue, polling..")


def display_config_files():
    # Download the selected file from S3
    key = "config/"+workflow
    print(f"get file: {key} from  {CONFIG_BUCKET}")
    obj = s3.get_object(Bucket=CONFIG_BUCKET, Key=key)
    file_content = obj['Body'].read().decode('utf-8')

    # Display the file content on the UI
    with st.expander("File Content", expanded=True):
        # Display the file content inside the expander
        st.code(file_content, language='python')

        # Add a "Hide" button inside the expander
        if st.button("Hide"):
            # Close the expander when the "Hide" button is clicked
            st.expander.empty()


# ========== ==============================================================================
# [Controller] send message
# ========================================================================================
def send_text_to_api(input_text, unique_id):
    st.session_state["start_next_question"] = False
    payload = {'user_question': input_text,
               'unique_id': unique_id}

    response = requests.post(TEXT_TO_SQL_API_ENDPOINT,
                             headers=headers, json=payload)
    st.session_state["poll_feedback_queue"] = True

    if response.status_code == 200:
        print(f"Text sent to API: {input_text}")
    else:
        print(f"Error sending text to API: {response.text}")


def send_feedback(feedback_type, input_text, unique_id):
    if "original_user_question" not in st.session_state:
        st.error("Original user question not found in session state.")
    else:
        original_user_question = st.session_state["original_user_question"]

    if feedback_type == reformulated_ques_key:
        reformualted_question = input_text
    else:
        reformualted_question = st.session_state["reformualted_question"]

    print(f'requesting to start feedback polling ')

    if feedback_type == generated_query_key:
        generated_query = input_text

    else:
        generated_query = st.session_state["generated_query"]

    print(f'requesting to start result polling ')

    payload = {'user_question': original_user_question,
               'unique_id': unique_id,
               "task_token": st.session_state["task_token"],
               "reformualted_question": reformualted_question,
               "generated_query": generated_query,
               }
    print(f"Payload: {payload}")

    response = requests.post(FEEDBACK_ENDPOINT, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"Feedback sent to API: {input_text}")
    else:
        print(f"Error sending feedback to API: {response.text}")


# ========================================================================================
# [Controller] Manage realtime data subscriptions
# ========================================================================================
# ----------------------------------------------------------------------------------------
# Subscription callbacks
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
# Subscription registration
# ----------------------------------------------------------------------------------------
# ========================================================================================
# [View] Render UI components
# ========================================================================================


# Streamlit page configuration
st.set_page_config(page_title="Text To SQL Conversion", page_icon="🏷️",
                   layout="wide", initial_sidebar_state="expanded")
add_indentation()

hide_deploy_button()

# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper()
auth.set_session_state()
auth.print_login_logout_buttons()

# Logged in user UI
if auth.is_authenticated():
    st.title("Insight to Data")

    credentials = auth.get_user_temporary_credentials()
    access_token, id_token = auth.get_user_tokens()
    decoded_token = auth.decode_id_token(id_token)
    headers = {
        'Authorization': id_token,
        'X-Amz-Access-Token': access_token
    }
    session_id = decoded_token.get(
        "cognito:username", id_token[:10])
    st.session_state["session_id"] = session_id
    s3 = boto3.client('s3',
                      aws_access_key_id=credentials['AccessKeyId'],
                      aws_secret_access_key=credentials['SecretAccessKey'],
                      aws_session_token=credentials['SessionToken'])

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Enter user question
    if prompt := st.chat_input("Please ask your question"):
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # unique id for each question
        unique_id = st.session_state["session_id"]+"-"+uuid.uuid4().hex
        st.session_state["unique_id"] = unique_id

        reformulate_key_match = re.search(
            rf'{reformulated_ques_key}\s*(.*)', prompt)
        generate_query_key_match = re.search(
            rf'{generated_query_key}\s*(.*)', prompt)

        print(F"prompt.lower :: {prompt.lower()}")
        print(F"reformulate_key_match :: {reformulate_key_match}")
        print(F"generate_query_key_match :: {generate_query_key_match}")
        if reformulate_key_match or prompt.lower() == "yes":
            print("SEND FEEDBACK 1")
            if (prompt.lower() == "yes"):
                overwrite_reformulated_question = st.session_state["reformulated_question"]
            else:
                overwrite_reformulated_question = reformulate_key_match.group(
                    1).strip()

            send_feedback(reformulated_ques_key,
                          overwrite_reformulated_question, unique_id)

        elif generate_query_key_match or prompt.lower() == "yes":
            print("SEND FEEDBACK 2")
            if (prompt.lower() == "yes"):
                overwrite_generated_query = st.session_state["generated_query"]
            else:
                overwrite_generated_query = generate_query_key_match.group(
                    1).strip()

            send_feedback(generated_query_key,
                          overwrite_generated_query, unique_id)
        else:
            # send user input question
            if st.session_state["start_next_question"] is True:
                send_text_to_api(prompt, unique_id)
            else:
                print("waiting for feedback or result to be displayed..")
            print(f'Start polling for feedback... {
                  st.session_state["poll_feedback_queue"]}')

        while st.session_state["poll_feedback_queue"] is True:
            receive_messages()
            receive_result()  # change it later
            time.sleep(5)  # Wait for 5 seconds before checking again

        print(" feedback polling ended..")
        print(f'Start polling for result... {
              st.session_state["poll_result_queue"]}')
        while st.session_state["poll_result_queue"] is True:
            receive_result()
            time.sleep(5)  # Wait for 5 seconds before checking again

elif not auth.is_authenticated():
    st.info("Please login !")
    st.stop()
else:
    st.stop()

#########################
#        SIDEBAR
#########################

with st.sidebar:
    st.header("Settings")
    st.subheader("Workflow Configuration")

    workflow = st.selectbox(
        label="Select config file:",
        options=["workflow_config.json", "knowledge_layer.json",
                 "knowledge_layer_prompt.json",
                 "kb_schema_linking_prompt.json",
                 "few_shots.json"],
        key="workflow",
        help="Select workflow",
    )

    if st.button("View"):
        display_config_files()
