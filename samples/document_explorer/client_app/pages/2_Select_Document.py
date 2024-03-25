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
import logging
import os
import sys
from datetime import datetime
# Third party imports
import boto3  
import pandas as pd
from dotenv import load_dotenv
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import streamlit as st
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
def process_document(params):
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
                "embeddings_model":{"provider":params['embedding_provider'],
                                     "modelId":params['embedding_model_id']
                                     },
                "files": [{"status": "", "name": params['uploaded_filename']}],
                "ingestionjobid": ingestion_job_id,
                "ignore_existing": True
            }
        }
        print(f' mutation query arguments :: {variables}')
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
    
    params={
        "uploaded_filename":st.session_state["uploaded_filename"],
        "embedding_model_id":st.session_state["embedding_model_id"],
        "embedding_provider":st.session_state["embedding_provider"],
        
    }
    
    print(f'on_subscription_registered :: {uploaded_filename}')
    
    process_document(params)



def on_message_update(message, subscription_client):
    """Callback when summary job status update is received.

    Args:
        message (dict): Message payload
        subscription_client (GraphQLSubscriptionClient): Client instance
    """
    ingestion_status = message.get("updateIngestionJobStatus")
    print(f'ingestion_status :: {ingestion_status}')
    if not ingestion_status:
        return

    files = ingestion_status.get("files")
    if not files:
        return

    first_file = files[0]
    status = first_file.get("status")
    image_url = first_file.get("imageurl")
    if not status:
        return

    status = status.lower()
    is_still_processing = True
    if status in ['ingested', 'file already exists']:
        is_still_processing = False
        logging.info(f"Ingestion completed. Status: {status}")
        st.session_state['image_url'] = image_url
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

# Streamlit page configuration

st.set_page_config(page_title="Select Document",
                    page_icon="📁",layout="wide",
                    initial_sidebar_state="expanded",)
add_indentation() 


st.session_state['selected_nav_index']=0

if st.session_state.get('switch_button', False):
    st.session_state['menu_option'] = (st.session_state.get('menu_option', 0) + 1) % 4
    manual_select = st.session_state['menu_option']
else:
    manual_select = None

    

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
    
    # sidebar
    EMBEDDING_MODEL_ID_OPTIONS=['amazon.titan-embed-image-v1','amazon.titan-embed-text-v1']
    EMBEDDING_MODEL_ID_PROVIDER=['Bedrock','Sagemaker']

    with st.sidebar:
            st.header("Settings")
        
            st.subheader("Data Ingestion Configuration")

            embedding_provider = st.selectbox(
                label="Select embedding model provider:",
                options=EMBEDDING_MODEL_ID_PROVIDER,
                key="embedding_provider",
                help="Select model provider.",
            )

            embedding_model_id = st.selectbox(
                label="Select embedding model id:",
                options=EMBEDDING_MODEL_ID_OPTIONS,
                key="embedding_model_id",
                help="Select model type to create and store embeddings in open search cluster as per your use case.",
            )


    # File uploader
    with st.form("file-uploader", clear_on_submit=True):

            uploaded_file = st.file_uploader('Upload a document', type=['pdf','jpeg','png','jpg'])
            submitted = st.form_submit_button("Submit", use_container_width=True)
            submit= True
            if(uploaded_file and uploaded_file.name.endswith(tuple(['.png','.jpeg','.jpg'])) and embedding_model_id=='amazon.titan-embed-text-v1'):
                st.warning("Invalid model id,Please select multimodality modal for image files")
                submit=False
            st.session_state['progress_bar_widget'] = st.empty()
            if submit and uploaded_file and submitted:
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
        print(f' file :: {df["Transformed Filename"]}')
        print(f' dulicate :: {df[df.duplicated()]}')
        
        #df = df.drop(df[df['Transformed Filename'].str.endswith(r'.txt')].index)
        

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
            st.session_state['selected_file'] = selected_filename
            print(st.session_state['selected_file'])

    else:
        st.write("This bucket is empty!")
        st.stop()

# Guest user UI 
else:
    st.write("Please login!")
    st.stop()

