# Standard library imports
import os
import base64
from copy import copy
# Third party imports 
import streamlit as st
from dotenv import load_dotenv
from streamlit_extras.switch_page_button import switch_page
# Local imports
from common.cognito_helper import CognitoHelper
from common.streamlit_utils import hide_deploy_button
from graphql.graphql_mutation_client import GraphQLMutationClient  
from graphql.graphql_subscription_client import GraphQLSubscriptionClient
from graphql.mutations import Mutations
from graphql.subscriptions import Subscriptions

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

    return f"{selected_file}.txt"

selected_filename = get_selected_filename()

#========================================================================================
# [Controller] Networking: GraphQL mutation helper functions 
#========================================================================================
def post_question_about_selected_file():
    """Send summary job request to GraphQL API."""

    selected_transformed_filename = get_selected_transformed_filename()
    if auth.is_authenticated() and selected_transformed_filename:
        # Get user tokens
        access_token, id_token = auth.get_user_tokens()
        
        # Decode ID token
        decoded_token = auth.decode_id_token(id_token)
        
        # Get summary job ID 
        summary_job_id = decoded_token.get("cognito:username", id_token[:10])

        # Call GraphQL mutation
        mutation_client = GraphQLMutationClient(GRAPHQL_ENDPOINT, id_token)
        variables = {
            "jobid": summary_job_id,
            "jobstatus": "",
            "filename": selected_transformed_filename,
            "question": st.session_state.get("encoded_question", ""),
            "max_docs": 1,
            "verbose": False,
            "streaming": True
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

    response_obj = message.get("updateQAJobStatus")
    if not response_obj:
        return

    status = response_obj.get("jobstatus")
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

    # Initialize chat history
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
    if st.button("Go to the document selection page"):
       switch_page("Select_Document")
    st.stop()