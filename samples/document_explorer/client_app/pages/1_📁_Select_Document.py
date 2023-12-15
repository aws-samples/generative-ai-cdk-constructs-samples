# Standard library imports
import logging
import os
import sys
from datetime import datetime
# Third party imports
import boto3  
import pandas as pd
from dotenv import load_dotenv
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from streamlit_extras.switch_page_button import switch_page
import streamlit as st
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
S3_INPUT_BUCKET = os.environ.get("S3_INPUT_BUCKET")
S3_PROCESSED_BUCKET = os.environ.get("S3_PROCESSED_BUCKET")
GRAPHQL_ENDPOINT = os.environ.get("GRAPHQL_ENDPOINT")

# Initialize logger
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class DocumentStatus(int):
    SUBSCRIBING = 10
    SUBSCRIPTION_ACTIVE = 30
    PROCESSING_STARTED = 50
    DOCUMENT_TYPE_CHECKED = 70
    DOCUMENT_TRANSFORMED = 80
    PROCESSING_COMPLETE = 100

#========================================================================================
# [Controller] Networking: GraphQL mutation helper functions 
#========================================================================================
def process_document(uploaded_filename):
    """Send document to ingestion pipeline
    
    Args:
        uploaded_filename (str): Name of uploaded file
        
    """
    
    if auth.is_authenticated():
        # Get user tokens
        access_token, id_token = auth.get_user_tokens()
        
        # Decode ID token
        decoded = auth.decode_id_token(id_token)
        
        # Get ingestion ID
        ingestion_job_id = decoded.get("cognito:username", id_token[:10])

        # Call GraphQL mutation
        mutation_client = GraphQLMutationClient(GRAPHQL_ENDPOINT, id_token)
        variables = {
            "ingestionInput": {
                "files": [{"status": "", "name": uploaded_filename}],
                "ingestionjobid": ingestion_job_id
            }
        }
        response = mutation_client.execute(Mutations.INGEST_DOCUMENTS, "IngestDocuments", variables)

        return response

    return None


#========================================================================================
# [Controller] Manage realtime data subscriptions
#========================================================================================
#----------------------------------------------------------------------------------------
# Subscription callbacks
#----------------------------------------------------------------------------------------
def on_subscription_registered():
    """Callback when subscription is registered."""

    st.session_state['progress_bar_widget'].progress(DocumentStatus.SUBSCRIPTION_ACTIVE)
    uploaded_filename = st.session_state.get('uploaded_filename')
    if not uploaded_filename:
        return

    st.session_state['progress_bar_widget'].progress(DocumentStatus.PROCESSING_STARTED)
    process_document(uploaded_filename)


def on_message_update(message, subscription_client):
    """Callback when summary job status update is received.

    Args:
        message (dict): Message payload
        subscription_client (GraphQLSubscriptionClient): Client instance
    """

    ingestion_status = message.get("updateIngestionJobStatus")
    if not ingestion_status:
        return

    files = ingestion_status.get("files")
    if not files:
        return

    first_file = files[0]
    status = first_file.get("status")
    if not status:
        return

    status = status.lower()
    is_still_processing = True
    if status in ['ingested', 'file already exists']:
        is_still_processing = False
        logging.info(f"Ingestion completed. Status: {status}")
        st.session_state['progress_bar_widget'].progress(DocumentStatus.PROCESSING_COMPLETE)

    elif status in ['unsupported', 'unable to load document']:
        is_still_processing = False
        logging.error(f"Failed to ingest document: {status}")
        st.session_state['progress_bar_widget'].progress(DocumentStatus.PROCESSING_COMPLETE)

    elif status == 'supported':
        st.session_state['progress_bar_widget'].progress(DocumentStatus.DOCUMENT_TYPE_CHECKED)

    elif status == 'file transformed':
        st.session_state['progress_bar_widget'].progress(DocumentStatus.DOCUMENT_TRANSFORMED)

    else:
        logging.info(f"on_message_update - status: {status}")

    if not is_still_processing:
        st.session_state['progress_bar_widget'].empty()
        subscription_client.unsubscribe()

#----------------------------------------------------------------------------------------
# Subscription registration
#----------------------------------------------------------------------------------------
def subscribe_to_file_ingestion_updates():
    """Subscribe to GraphQL subscription for file ingestion job status updates."""

    if auth.is_authenticated():
        st.session_state['progress_bar_widget'].progress(DocumentStatus.SUBSCRIBING)

        # Get user tokens
        access_token, id_token = auth.get_user_tokens()

        # Decode ID token
        decoded_token = auth.decode_id_token(id_token)

        # Get ingestion job ID
        ingestion_job_id = decoded_token.get("cognito:username", id_token[:10])

        # Subscribe to GraphQL subscription
        subscription_client = GraphQLSubscriptionClient(GRAPHQL_ENDPOINT, id_token)
        variables = {"ingestionjobid": ingestion_job_id}
        subscription_client.subscribe(
            Subscriptions.UPDATE_INGESTION_JOB_STATUS,
            "UpdateIngestionJobStatus",
            variables,
            on_message_callback=on_message_update,
            on_subscription_registered_callback=on_subscription_registered
        )

#========================================================================================
# [View] Render UI components  
#========================================================================================
def format_last_modified(last_modified):
    """Convert last modified date to MM/DD/YYYY format
    
    Args:
        last_modified (datetime): Last modified date
        
    Returns:
        str: Formatted date
    """
    return datetime.strftime(last_modified, "%m/%d/%Y")


def to_tuple(s3_object):
    """Convert S3 object metadata to tuple

    Args:
        s3_object (dict): S3 object metadata

    Returns:
        tuple: (filename, last_modified)
    """
    return (
        s3_object['Key'].replace('.txt',''),
        format_last_modified(s3_object['LastModified'])
    )

def navigate_to_summary(selected_filename):
    """Update selected file and redirect to summary page

    Args:
        selected_filename (str): Selected file name
    """
        
    st.session_state['selected_file'] = selected_filename
    print(st.session_state['selected_file'])
    switch_page("Summary")

# Streamlit page configuration
st.set_page_config(page_title="Select Document", page_icon="📁")
hide_deploy_button()

# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper()
auth.set_session_state()
auth.print_login_logout_buttons()

# Logged in user UI
if auth.is_authenticated():
    st.markdown("# Select a document")
    st.write("Doc explorer lets you upload, summarize, and ask questions about your documents using GenAI.")

    # Create S3 client
    credentials = auth.get_user_temporary_credentials()
    s3 = boto3.client(
        's3',
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"]
    )
    
    # File uploader
    uploaded_file = st.file_uploader('Upload a document', type=['pdf'])
    st.session_state['progress_bar_widget'] = st.empty()
    if uploaded_file:
        s3.upload_fileobj(uploaded_file, S3_INPUT_BUCKET, uploaded_file.name)
        st.session_state['uploaded_filename'] = uploaded_file.name
        subscribe_to_file_ingestion_updates()

    # Transformed file grid
    transformed_files = s3.list_objects_v2(Bucket=S3_PROCESSED_BUCKET)
    if 'Contents' in transformed_files:
        df = pd.DataFrame(
            pd.Series(transformed_files['Contents']).apply(to_tuple).tolist(),
            columns=["Transformed Filename", "Last Modified"]
        )

        options = GridOptionsBuilder.from_dataframe(df)
        options.configure_selection("single")
        options.configure_column("Last Modified", headerName="Last Modified", width=40)
            
        selection = AgGrid(
            df,
            gridOptions=options.build(),
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=True
        )
            
        if selection["selected_rows"]:
            selected_filename = selection["selected_rows"][0]["Transformed Filename"]
            navigate_to_summary(selected_filename)

    else:
        st.write("This bucket is empty!")
        st.stop()

# Guest user UI 
else:
    st.write("Please login!")
    st.stop()