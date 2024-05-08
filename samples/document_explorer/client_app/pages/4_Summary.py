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
# Third party imports
import streamlit as st
from dotenv import load_dotenv
import boto3
from streamlit_javascript import st_javascript
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
S3_INPUT_BUCKET = os.environ.get("S3_INPUT_BUCKET")
S3_PROCESSED_BUCKET = os.environ.get("S3_PROCESSED_BUCKET")
GRAPHQL_ENDPOINT = os.environ.get("GRAPHQL_ENDPOINT")  



def get_selected_source_filename():
    """Get selected source filename from session state."""
    
    selected_file = st.session_state.get('selected_file')
    if not selected_file:
        return None

    #if a image then don't change the extension
    image_ext = ['.jpg','.jpeg','.png','.svg']
    if selected_file.endswith(tuple(image_ext)):
        return selected_file
    else:
        return f"{selected_file}.pdf"

# Get selected source file if authenticated
selected_file = get_selected_source_filename()

#========================================================================================
# [Controller] Networking: GraphQL mutation helper functions 
#========================================================================================
def generate_summary(source_filename):
    """Send summary job request to GraphQL API."""

    if auth.is_authenticated():

        # Get user tokens
        access_token, id_token = auth.get_user_tokens()
        
        # Decode ID token
        decoded_token = auth.decode_id_token(id_token)
        
        # Get summary job ID 
        summary_job_id = decoded_token.get("cognito:username", id_token[:10])

        # Call GraphQL mutation
        mutation_client = GraphQLMutationClient(GRAPHQL_ENDPOINT, id_token)
        variables = {
            "summaryInput": {
                "files": [{"status": "", "name": source_filename}],
                "summary_job_id": summary_job_id,
                "language":st.session_state["language"],
                "ignore_existing":False,
                "summary_model": {
                    "modality":st.session_state["modality"],
                    "modelId": st.session_state["model_id"],
                    "provider": st.session_state["model_provider"],
                    "streaming":st.session_state["streaming"],
                    "model_kwargs":"{\n \"temperature\":"+str(st.session_state["temperature"])+",\"top_p\":"+str(st.session_state['top_p'])+",\"top_k\":"+str(st.session_state['top_k'])+"}"

                }
            }
        }
        return mutation_client.execute(Mutations.GENERATE_SUMMARY, "GenerateSummary", variables)

    return None

#========================================================================================
# [Controller] Manage realtime data subscriptions
#========================================================================================
#----------------------------------------------------------------------------------------
# Subscription callbacks
#----------------------------------------------------------------------------------------
def on_subscription_registered():
    """Callback when subscription is registered."""
    
    source_filename = get_selected_source_filename()
    if source_filename:
        generate_summary(source_filename)

def on_message_update(message, subscription_client):
    """Callback when summary job status update is received."""


    summary_response = message.get("updateSummaryJobStatus")
    print(f" summary_status:: {summary_response}")
    if not summary_response:
        return

    status = summary_response.get("status")
    print(f'status :: {status}') 
 
   
    summary_widget = st.session_state['summary_widget']
    text_height = st.session_state['summary_widget_height']
    
    if status == "New LLM token":
        encoded_summary = summary_response.get("summary")
        if not encoded_summary:
            return
    
        if summary_widget and text_height > 0:
            summary_text = base64.b64decode(encoded_summary).decode("utf-8")
            st.session_state.summary_widget_text += summary_text
            summary_widget.text_area(f"Summary for **{selected_file}**", st.session_state.summary_widget_text + " ▌", height=text_height)

    elif status == "LLM streaming ended":
        file_processed=selected_file
        summary_generated=st.session_state.summary_widget_text
        st.session_state['file_processed']=file_processed
        st.session_state['summary_generated']=summary_generated
        subscription_client.unsubscribe()
    else:
        encoded_summary = summary_response.get("summary")
        if not encoded_summary:
            return
        summary_text = base64.b64decode(encoded_summary).decode("utf-8")
        summary_widget.text_area(f"Summary for **{selected_file}**", summary_text, height=text_height)
        subscription_client.unsubscribe()
    
#----------------------------------------------------------------------------------------
# Subscription registration
#----------------------------------------------------------------------------------------
def subscribe_to_summary_updates():
    """Subscribe to GraphQL subscription for summary job status updates."""

    if auth.is_authenticated():
        # Get user tokens
        access_token, id_token = auth.get_user_tokens()

        # Decode ID token
        decoded_token = auth.decode_id_token(id_token)

        # Get summary job ID

        summary_job_id = decoded_token.get("cognito:username", id_token[:10])
        
        # Subscribe to GraphQL subscription
        subscription_client = GraphQLSubscriptionClient(GRAPHQL_ENDPOINT, id_token)
        variables = {"summary_job_id": summary_job_id}
        summary_widget_text = ""
        st.session_state['summary_widget_text'] = summary_widget_text
        subscription_client.subscribe(
            Subscriptions.UPDATE_SUMMARY_JOB_STATUS,
            "UpdateSummaryJobStatus",
            variables,
            on_message_callback=on_message_update,
            on_subscription_registered_callback=on_subscription_registered
        )

#========================================================================================
# [View] Render UI components  
#========================================================================================
def display_pdf(pdf_content, pdf_viewer_width, pdf_viewer_height):
    """Display first page of PDF file in Streamlit."""
    
    first_page = pdf_content.split(b"\n%%PAGESEP%%\n")[0] 
    base64_pdf = base64.b64encode(first_page).decode("utf-8")
    pdf_html = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="{pdf_viewer_width}" height="{pdf_viewer_height}" type="application/pdf"></iframe>'
    st.markdown(pdf_html, unsafe_allow_html=True)

def display_image(key):
    """Display image Streamlit."""
    
    if key is not None:
        response = s3.get_object(Bucket=S3_PROCESSED_BUCKET, Key=key)
        file_stream = BytesIO(response['Body'].read())
        print('displaying image')
        st.image(file_stream,400)

    return response

# Streamlit page configuration

st.set_page_config(page_title="Summary", page_icon="🏷️", layout="wide", initial_sidebar_state="expanded")
add_indentation() 

hide_deploy_button()

# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper() 
auth.set_session_state()
auth.print_login_logout_buttons()

# Logged in user UI
if auth.is_authenticated() and selected_file:
    col1, col2 = st.columns(2)
    with col1:
        # Display PDF preview
        pdf_width = int(st_javascript("window.innerWidth", key="pdf_width") - 20)  
        pdf_height = int(pdf_width * 4/3)

        credentials = auth.get_user_temporary_credentials()  
        # if(selected_file.endswith(".jpeg")):
        #     st.info(' No summary available for the image file :: '+selected_file)

        # else:
        s3 = boto3.client('s3',
                        aws_access_key_id=credentials['AccessKeyId'],
                        aws_secret_access_key=credentials['SecretAccessKey'],
                        aws_session_token=credentials['SessionToken'])

        pdf_object = s3.get_object(Bucket=S3_INPUT_BUCKET, Key=selected_file)
        pdf_content = pdf_object['Body'].read()

        st.write("Preview")
        if(selected_file.endswith(".pdf") or selected_file.endswith(".txt")):
            display_pdf(pdf_content, pdf_width, pdf_height)
        else:
           display_image(selected_file)

        with col2:
            # Display summary widget
            text_width = int(st_javascript("window.innerWidth", key="text_width") - 20)
            text_height = int(text_width * 3/4)

            summary_widget = st.empty()
            if('file_processed' not in st.session_state): 
                    st.session_state['file_processed']=''
           

            #     st.session_state.message_widget_text = ""
            if summary_widget and text_height > 0:
                summary_widget.text_area(f"Summary for **{selected_file}**", height=text_height)
                st.session_state['summary_widget'] = summary_widget
                st.session_state['summary_widget_height'] = text_height
                
            if st.button("Generate Summary",type="primary"):
                with st.spinner('Processing...'):
                    if (st.session_state['file_processed']==selected_file):
                        summary_text = st.session_state['summary_generated']                
                        summary_widget.text_area(f"Summary for **{selected_file}**", summary_text + " ▌", height=text_height)
                        st.success('Generated Summary!')
                    else:
                        subscribe_to_summary_updates()
                        st.success('Generated Summary!')


# Guest user UI 
elif not auth.is_authenticated():
    st.write("Please login and select a document!")
    st.stop()
else:
    st.write("Please select a document!")
    st.stop()


#########################
#        SIDEBAR
#########################

# sidebar

MODEL_ID_OPTIONS=['anthropic.claude-3-sonnet-20240229-v1:0',
                     'anthropic.claude-3-haiku-20240307-v1:0',
                     'anthropic.claude-v2:1',
                     'anthropic.claude-v2',
                     'anthropic.claude-instant-v1',
                     'amazon.titan-text-lite-v1',
                     'amazon.titan-text-express-v1',
                     'amazon.titan-text-premier-v1:0',
                     'IDEFICS']
MODEL_ID_PROVIDER=['Bedrock','Sagemaker']
LANGUAGE_OPTIONS=['English','Spanish','French']

with st.sidebar:
        st.header("Settings")
        st.subheader("Summarization Configuration")

        
        model_provider = st.selectbox(
                label="Select  model provider:",
                options=MODEL_ID_PROVIDER,
                key="model_provider",
                help="Select model provider.",
            )

        model_id = st.selectbox(
                label="Select embedding model id:",
                options=MODEL_ID_OPTIONS,
                key="model_id",
                help="Select model type to generate summary.",
            )

        streaming = st.selectbox(
                label="Select streaming:",
                options=[True,False],
                key="streaming",
                help="Enable or disable streaming on response",
            )
        language = st.selectbox(
                label="Select language:",
                options=LANGUAGE_OPTIONS,
                key="language",
                help="Select response language",
            )
        modality = st.selectbox(
                label="Select modality:",
                options=["Text","Image"],
                key="modality",
                help="Select modality",
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
            
