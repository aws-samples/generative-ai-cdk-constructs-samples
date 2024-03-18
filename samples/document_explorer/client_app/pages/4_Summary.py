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
                "summary_job_id": summary_job_id
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

    summary_status = message.get("updateSummaryJobStatus")
    if not summary_status:
        return

    files = summary_status.get("files")
    if not files:
        return

    first_file = files[0]
    status = first_file.get("status")
    if status != "Completed":
        return

    encoded_summary = first_file.get("summary")
    if not encoded_summary:
        return

    summary_widget = st.session_state['summary_widget']
    text_height = st.session_state['summary_widget_height']
    
    if summary_widget and text_height > 0:
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

# Streamlit page configuration

st.set_page_config(page_title="Summary", page_icon="🏷️", layout="wide", initial_sidebar_state="expanded")
add_indentation() 
# selected = option_menu(
#         menu_title="AWS-GENERATIVE-AI-CDK-CONSTRUCTS SAMPLE APPS",
#         options=["Document Explorer", 'Content Generation'], 
#         icons=['💬', '📸'],
#         menu_icon="cast", 
#         #default_index=0,
#         orientation='horizontal'
#         )
# if selected == "Content Generation":
#     hide_pages(["Q&A","Select Document","Summary","Visual Q&A"])
#     st.session_state['selected_nav_index']=1
#     st.switch_page("pages/5_Image_Generation.py")
    
# elif selected == "Document Explorer":
#     hide_pages(["Image Generation","Image Search"])
    #st.switch_page("pages/1_Select_Document.py")

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
        if(selected_file.endswith(".jpeg")):
            st.info(' No summary available for the image file :: '+selected_file)

        else:
            s3 = boto3.client('s3',
                            aws_access_key_id=credentials['AccessKeyId'],
                            aws_secret_access_key=credentials['SecretAccessKey'],
                            aws_session_token=credentials['SessionToken'])

            pdf_object = s3.get_object(Bucket=S3_INPUT_BUCKET, Key=selected_file)
            pdf_content = pdf_object['Body'].read()

            st.write("Preview")
            display_pdf(pdf_content, pdf_width, pdf_height)

            with col2:
                # Display summary widget
                text_width = int(st_javascript("window.innerWidth", key="text_width") - 20)
                text_height = int(text_width * 4/3)

                summary_widget = st.empty()
                if summary_widget and text_height > 0:
                    summary_widget.text_area(f"Summary for **{selected_file}**", "Processing...", height=text_height)
                    st.session_state['summary_widget'] = summary_widget
                    st.session_state['summary_widget_height'] = text_height
                    subscribe_to_summary_updates()

# Guest user UI 
elif not auth.is_authenticated():
    st.write("Please login and select a document!")
    st.stop()
else:
    st.write("Please select a document!")
    st.stop()