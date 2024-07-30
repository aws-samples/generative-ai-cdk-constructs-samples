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
from streamlit_option_menu import option_menu
from st_pages import show_pages,Section, Page, hide_pages,add_indentation
from streamlit_extras.switch_page_button import switch_page

#========================================================================================
# [Model] Load configuration and environment variables
#========================================================================================
# Load environment variables from .env file
load_dotenv() 

# Configure buckets and API endpoint  
GRAPHQL_ENDPOINT = os.environ.get("GRAPHQL_ENDPOINT")  

def get_selected_filenames():
    selected_files = st.session_state.get("selected_files")
    if not selected_files:
        return None
    
    return selected_files

def get_selected_transformed_filenames():
    """Get selected source filename from session state."""
    
    selected_files = st.session_state.get('selected_files')
    if not selected_files:
        return None

    return f"{selected_files[0]}.txt"

selected_filenames = get_selected_filenames()

#========================================================================================
# [Controller] Networking: GraphQL mutation helper functions 
#========================================================================================
def post_question_about_selected_files(params):
    """Send QA job request to GraphQL API."""

    selected_transformed_filename = get_selected_transformed_filenames()
    generative_method = st.session_state.get("generative_method", "LONG_CONTEXT")
    if auth.is_authenticated() and selected_transformed_filename:
        # Get user tokens
        access_token, id_token = auth.get_user_tokens()
        
        # Decode ID token
        decoded_token = auth.decode_id_token(id_token)
        
        # Get QA job ID 
        qa_job_id = decoded_token.get("cognito:username", id_token[:10])

        # Call GraphQL mutation
        mutation_client = GraphQLMutationClient(GRAPHQL_ENDPOINT, id_token)
        
        filenames = '.txt, '.join(selected_filenames) + '.txt'
        
        variables = {
             "embeddings_model": {
                "modelId": params['embedding_model_id'],
                "provider": params['embedding_provider'],
                "streaming":params['streaming'],
            },
            "jobid": qa_job_id,
            "jobstatus": "",
            "filename": filenames,
            "qa_model": {
                "modelId": params['qa_model_id'],
                "provider": params['qa_provider'],
                "streaming":params['streaming'],
                "model_kwargs":"{\n \"temperature\":"+str(params['temperature'])+",\"top_p\":"+str(params['top_p'])+",\"top_k\":"+str(params['top_k'])+",\"length\":\""+str(params['length'])+"\"}"
            },
            "retrieval":{
                "max_docs": params['max_docs'],
	            "index_name": "",
	            "filter_filename": ""
            },
            "verbose": False,
            "question": st.session_state.get("encoded_question", ""),
            "responseGenerationMethod": generative_method

        }
        print(f'ask question::: {variables} ')
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
    params={
        "embedding_model_id":st.session_state["embedding_model_id"],
        "qa_model_id":st.session_state["qa_model_id"],
        "streaming":st.session_state["streaming"],
        "embedding_provider":st.session_state["embedding_provider"],
        "qa_provider":st.session_state["qa_provider"],
        "temperature":st.session_state["temperature"] ,  
        "top_p":st.session_state["top_p"] ,
        "top_k":st.session_state["top_k"] , 
        "length":st.session_state["length"] ,   
        "max_docs":st.session_state["max_docs"] ,              
    }
    post_question_about_selected_files(params)

selected_files = get_selected_transformed_filenames()

def on_message_update(message, subscription_client):
    """Callback when QA job status update is received."""

    response_obj = message.get("updateQAJobStatus")
    if not response_obj:
        return

    status = response_obj.get("jobstatus")
    print(f'status :: {status}')
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

        # Get QA job ID
        qa_job_id = decoded_token.get("cognito:username", id_token[:10])

        # Subscribe to GraphQL subscription
        subscription_client = GraphQLSubscriptionClient(GRAPHQL_ENDPOINT, id_token)
        variables = {"jobid": qa_job_id}
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
add_indentation() 


hide_deploy_button()

# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper() 
auth.set_session_state()
auth.print_login_logout_buttons()

# Logged in user UI
if auth.is_authenticated() and selected_filenames:
    # Add a radio button for method selection
    generative_method = st.radio(
        "Select Response Generation Method:",
        ('RAG', 'LONG_CONTEXT')
    )
    # Add a divider here
    st.markdown("---")
    st.session_state['generative_method'] = generative_method
   

    # Initialize chat history
    if "messages_filenames" not in st.session_state or st.session_state.messages_filenames != selected_filenames:
        st.session_state.messages_filenames = selected_filenames
        st.session_state.messages = [{"role": "assistant", "content": f"Ask me anything about **{', '.join(selected_filenames)}**!"}]

    # Add Clear button
    if st.button("Clear"):
        st.session_state.messages = [{"role": "assistant", "content": f"Ask me anything about **{', '.join(selected_filenames)}**!"}]
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
    st.warning("Please login and select a document!")
    st.stop()
else:
    st.warning("Please select a document!")
    st.stop()

#########################
#        SIDEBAR
#########################

# sidebar
EMBEDDING_MODEL_ID_OPTIONS=['amazon.titan-embed-image-v1',
                            'amazon.titan-embed-text-v1',
                            ]
QA_MODEL_ID_OPTIONS=['anthropic.claude-3-sonnet-20240229-v1:0',
                     'anthropic.claude-3-haiku-20240307-v1:0',
                     'anthropic.claude-v2:1',
                     'anthropic.claude-v2',
                     'anthropic.claude-instant-v1',
                     'amazon.titan-text-lite-v1',
                     'amazon.titan-text-express-v1',
                     'amazon.titan-text-premier-v1:0',
                     'IDEFICS']
EMBEDDING_MODEL_ID_PROVIDER=['Bedrock','Sagemaker']
QA_MODEL_ID_PROVIDER=['Bedrock','Sagemaker']

with st.sidebar:
    st.divider()
    st.header('Selected Files')
    if selected_filenames:
            for file in selected_filenames:
                st.write('- ' + file)
    else:
        st.write("No files selected")
    st.divider()
    st.header("Settings")
    st.subheader("Q&A Configuration")

    
    embedding_provider = st.selectbox(
            label="Select embedding model provider:",
            options=EMBEDDING_MODEL_ID_PROVIDER,
            key="embedding_provider",
            help="Select model provider.",
        )
    qa_provider = st.selectbox(
            label="Select qa model provider:",
            options=QA_MODEL_ID_PROVIDER,
            key="qa_provider",
            help="Select model provider.",
        )

    embedding_model_id = st.selectbox(
            label="Select embedding model id:",
            options=EMBEDDING_MODEL_ID_OPTIONS,
            key="embedding_model_id",
            help="Select model type to create and store embeddings in open search cluster as per your use case.",
        )

    qa_model_id = st.selectbox(
            label="Select qa model id:",
            options=QA_MODEL_ID_OPTIONS,
            key="qa_model_id",
            help="Select model type to generate response for your questions.",
        )

    streaming = st.selectbox(
            label="Select streaming:",
            options=[True,False],
            key="streaming",
            help="Enable or disable streaming on response",
        )
    
    max_docs = st.number_input(
            label="Max docs for RAG",
            value=100,
            min_value=0,
            max_value=200,
            key="max_docs",
        )

    temperature = st.slider(
            label="Temperature:",
            value=1.0,
            min_value=0.0,
            max_value=1.0,
            key="temperature",
        )
    top_p = st.slider(
            label="Top P:",
            value=0.999,
            min_value=0.0,
            max_value=0.999,
            key="top_p",
        )
    top_k = st.slider(
            label="Top K:",
            value=250,
            min_value=0,
            max_value=500,
            key="top_k",
        )
    
        
    length = st.number_input(
            label="Maximum Length",
            value=50000,
            min_value=0,
            max_value=200000,
            key="length",
        )

