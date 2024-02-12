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
import base64
from copy import copy
# Third party imports 
import streamlit as st
from dotenv import load_dotenv
# Local imports
from common.cognito_helper import CognitoHelper
from common.streamlit_utils import hide_deploy_button
from graphql.graphql_mutation_client import GraphQLMutationClient  
from graphql.graphql_subscription_client import GraphQLSubscriptionClient
from graphql.mutations import Mutations
from graphql.subscriptions import Subscriptions
import boto3

#========================================================================================
# [Model] Load configuration and environment variables
#========================================================================================
# Load environment variables from .env file
load_dotenv() 

# Configure buckets and API endpoint  
GRAPHQL_ENDPOINT = os.environ.get("GRAPHQL_ENDPOINT")  

def get_selected_filename():
    selected_file = st.session_state.get("selected_file")
    if not selected_file:
        return None
    
    return selected_file

def get_selected_transformed_filename():
    """Get selected source filename from session state."""
    
    selected_file = st.session_state.get('selected_file')
    if not selected_file:
        return None
    #todo - update this logic 
    if selected_file.endswith(".png"):
        return selected_file
    return f"{selected_file}.txt"

selected_filename = get_selected_filename()

#========================================================================================
# [Controller] Networking: GraphQL mutation helper functions 
#========================================================================================
def post_question_about_selected_file():
    """Send summary job request to GraphQL API."""

    selected_transformed_filename = get_selected_transformed_filename()
    generative_method = st.session_state.get("generative_method", "LONG_CONTEXT")
    if auth.is_authenticated() and selected_transformed_filename:
        # Get user tokens
        access_token, id_token = auth.get_user_tokens()
        
        # Decode ID token
        decoded_token = auth.decode_id_token(id_token)
        
        # Get summary job ID 
        summary_job_id = decoded_token.get("cognito:username", id_token[:10])

        # Call GraphQL mutation
        mutation_client = GraphQLMutationClient(GRAPHQL_ENDPOINT, id_token)
        print(f' posting question now :: ')
        variables = {
             "embeddings_model": {
                "modelId": "",
                "provider": "",
                "streaming":True
            },
            "jobid": summary_job_id,
            "jobstatus": "",
            "filename": selected_transformed_filename,
            "presignedurl":'https://persistencestack-processedassets6ba25f4c-5cxemxijzhlx.s3.us-east-1.amazonaws.com/test.png?response-content-disposition=inline&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEIj%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJIMEYCIQD2VtSl7gmPddhrNWpcAB9ooXQFdTYPfyNx0CkzTQu0%2BgIhAKhfGxO60Zv4QAhZHgBTT%2B90QqR7fo8IxnVgtT6Cnw8hKuYCCGEQABoMNTg3OTYyMDkzNzMwIgxJWIF9iKcuCsHBIlwqwwIRAu3eUqMBKFZ%2FBQ3JofLWh5CmSgiPezR6MUkcek2kbrknjQDerkKWN%2BxzcaK83nO5dcTVgzxNSD300XhnJlVvDSopFaTQtJuK76igLufXH6F2mdawWN3ThQNznCXFGUP1O8mw50cvYiCv0Gg2rcTaWxUjS5scYAG%2FIlIxIuFyrXDHe0U3BvrFAgVozu8uun%2BlUR3%2F3hQW8JJFfeC4aIt223oTfmIgIWPuqaJ5uYY8IHCYgGMTCWMmtXDsv14edZAF5LJh2NyQicZh0fTLRMRMeNG5vdaBCU0TRv0P8wlI%2FdDlk1QFuZHmiPN%2FvcdXEGvLVu77K7OCsWI0oQ4omNord0UEAVIOA0IG352ujLhH8nqF%2BhZtqPp6etk%2Fv043F9td6Ld5KprLV2tKX4AVBBMhYzDi5v8E972rD5wz0t0NFKM8PTCIgKmuBjqGAl9sbVrj6alHOwK8kBpsgVOOX4bp%2Bqsm8g%2B%2FKrXmQeqiv8kGqd1LieUs8VB4BKGcPiYdnkV8nEHh1j5TM7yn74Rr3fRhZ54mOlMiDsjdBBmuE8f8CScy%2F7A1dw8OvCkeJT0D8Zt%2F0goS4qupYEsVV0Ivbk97qtsXMj5xt5EVfA362SVbNfproU8Y6LRx7rnFMh%2B3p76aCAqnNXnqNUOiY2J7x2AijoYLGC95SCdFRNtkFyfjKWYIFeh%2BNqKeM3xhpkt%2FD1Bx86jfTcHIzh28zjt4h26RO%2FHrg1x8MIbUoxbJqK5spVfLQKUK88GbeTJpOuZNIwXix%2B5z3xaJHRuLpJqjH%2FaMV9g%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20240212T221742Z&X-Amz-SignedHeaders=host&X-Amz-Expires=7200&X-Amz-Credential=ASIAYRZKFSCRAGHJV4M3%2F20240212%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=f270757211a1b2c3d6ccd3a68f118ebb49fd635f41562c94abb55d031f2b8884',
            "qa_model": {
                "modelId": "",
                "provider": "",
                "streaming":""
            },
            "retrieval":{
                "max_docs": 1,
	            "index_name": "",
	            "filter_filename": ""
            },
            "verbose": False,
            "question": st.session_state.get("encoded_question", ""),
            "responseGenerationMethod": generative_method

        }
        
        return mutation_client.execute(Mutations.POST_QUESTION, "PostQuestion", variables)

    return None


#========================================================================================
# [Controller] Manage realtime data subscriptions
#========================================================================================
#----------------------------------------------------------------------------------------
# Subscription callbacks
#----------------------------------------------------------------------------------------
def on_subscription_registered():
    """Callback when subscription is registered"""
    post_question_about_selected_file()

selected_file = get_selected_transformed_filename()

def on_message_update(message, subscription_client):
    """Callback when summary job status update is received."""
    print(f'listenning....')
    response_obj = message.get("updateQAJobStatus")
    print(f'response received or not :: {response_obj}')
    if not response_obj:
        return

    status = response_obj.get("jobstatus")

    print(f'response received  :: {status}')

    ## TODO - Check with @Heitor why status Done  was not enabled ?
    if status == "Done":
        encoded_answer = response_obj.get("answer")
        if not encoded_answer:
            return
        answer_text = base64.b64decode(encoded_answer).decode("utf-8")
        st.session_state.message_widget_text += answer_text
        st.session_state.message_widget.markdown(st.session_state.message_widget_text + " ▌")           

    if status == "New LLM token":
        encoded_answer = response_obj.get("answer")
        if not encoded_answer:
            return
        answer_text = base64.b64decode(encoded_answer).decode("utf-8")
        st.session_state.message_widget_text += answer_text
        st.session_state.message_widget.markdown(st.session_state.message_widget_text + " ▌")           

    elif status == "LLM streaming ended":
        st.session_state.message_widget.markdown(st.session_state.message_widget_text)
        if st.session_state.messages[-1]['role'] == 'assistant':
            st.session_state.messages[-1]['content'] = copy(st.session_state.message_widget_text)
        subscription_client.unsubscribe()


#----------------------------------------------------------------------------------------
# Subscription registration
#----------------------------------------------------------------------------------------
def subscribe_to_answering_updates():
    """Subscribe to GraphQL subscription for bot answering status updates."""

    if auth.is_authenticated():
        # Get user tokens
        access_token, id_token = auth.get_user_tokens()

        # Decode ID token
        decoded_token = auth.decode_id_token(id_token)

        # Get summary job ID
        summary_job_id = decoded_token.get("cognito:username", id_token[:10])

        # Subscribe to GraphQL subscription
        subscription_client = GraphQLSubscriptionClient(GRAPHQL_ENDPOINT, id_token)
        variables = {"jobid": summary_job_id}

        print(f'start subscription :: ')
        subscription_client.subscribe(
            Subscriptions.UPDATE_QA_JOB_STATUS,
            "UpdateQAJobStatus",
            variables,
            on_message_callback=on_message_update,
            on_subscription_registered_callback=on_subscription_registered
        )

#========================================================================================
# [View] Render UI components  
#========================================================================================
# Streamlit page configuration
st.set_page_config(page_title="Q&A", page_icon="💬", layout="wide") 
hide_deploy_button()

# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper() 
auth.set_session_state()
auth.print_login_logout_buttons()

# Logged in user UI
if auth.is_authenticated() and selected_filename:
    # Add a radio button for method selection
    generative_method = st.radio(
        "Select Response Generation Method:",
        ('RAG', 'LONG_CONTEXT')
    )
    # Add a divider here
    st.markdown("---")
    st.session_state['generative_method'] = generative_method

    # Initialize chat history
    # if selected_filename has jpg or png or jpeg

    print(f'start  QA on :: {selected_filename}')
    if selected_filename.endswith(".jpg") or selected_filename.endswith(".jpeg")  or selected_filename.endswith(".png") or selected_filename.endswith(".jpeg"):
        st.session_state.messages = [{"role": "assistant", "content": f"Ask me anything about **{selected_filename}**!"}]
        # display image from s3 using presigned url
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket='persistencestack-processedassets6ba25f4c-5cxemxijzhlx', Key=selected_filename)
        file_stream = BytesIO(response['Body'].read())
        st.image(file_stream,width=400)



    if "messages_filename" not in st.session_state or st.session_state.messages_filename != selected_filename:
        st.session_state.messages_filename = selected_filename
        st.session_state.messages = [{"role": "assistant", "content": f"Ask me anything about **{selected_filename}**!"}]

    # Add Clear button
    if st.button("Clear"):
        st.session_state.messages = [{"role": "assistant", "content": f"Ask me anything about **{selected_filename}**!"}]
        st.session_state.message_widget_text = ""

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle user input
    if prompt := st.chat_input():
        # Display user message
        st.chat_message("user").markdown(prompt)
            
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            message_widget = st.empty()
            message_widget_text = ""
            message_widget.markdown("Processing ...")
            st.session_state['message_widget'] = message_widget
            st.session_state['message_widget_text'] = message_widget_text
            st.session_state['encoded_question'] = base64.b64encode(prompt.encode("utf-8")).decode("utf-8") 
            st.session_state.messages.append({"role": "assistant", "content": message_widget_text})
            subscribe_to_answering_updates()

# Guest user UI 
elif not auth.is_authenticated():
    st.write("Please login and select a document!")
    st.stop()
else:
    st.write("Please select a document!")
    st.stop()