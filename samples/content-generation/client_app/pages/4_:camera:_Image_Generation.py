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
import requests
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
IMAGE_OUTPUT_BUCKET = os.environ.get("S3_PROCESSED_BUCKET") 

# read image from s3
def get_image():
    image_url = st.session_state.get("image_url")
    if not image_url:
        print(f'no image url present , not able to display image ')
        return None
    
    return image_url

#========================================================================================
# [Controller] Networking: GraphQL mutation helper functions 
#========================================================================================
def generate_image_based_on_text(params):
    """Send generate image job request to GraphQL API."""
    
    if auth.is_authenticated():
        # Get user tokens
        access_token, id_token = auth.get_user_tokens()
        
        # Decode ID token
        decoded_token = auth.decode_id_token(id_token)
        
        # Get job ID 
        job_id = decoded_token.get("cognito:username", id_token[:10])

        # Call GraphQL mutation
        mutation_client = GraphQLMutationClient(GRAPHQL_ENDPOINT, id_token)
        print(f' generating image now :: ')
        variables = {
             "model_config": {
                "modelId": params['model_id'],
                "provider": params['provider'],
                "model_kwargs":{
                    "cfg_scale":params['cfg_scale'],
                    "seed":params['seed'],
                    "steps":params['steps']
                }
            },
            "jobid": job_id,
            "filename": '',            
            #"input_text": st.session_state.get("encoded_question", ""),
            "input_text": params['input_text'],

        }
        
        return mutation_client.execute(Mutations.GENERATE_IMAGE, "GenerateImage", variables)

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
        "model_id":st.session_state["model_id"],
        "provider":st.session_state["provider"],
        "input_text":st.session_state.encode_input_text,
        "cfg_scale":st.session_state["cfg_scale"],
        "seed":st.session_state["seed"],
        "steps":st.session_state["steps"]
    }
    generate_image_based_on_text(params)


def on_message_update(message, subscription_client):
    """Callback when image generation job status update is received."""
    response_obj = message.get("updateGenerateImageStatus")
    print(f'response received or not :: {response_obj}')
    if not response_obj:
        return

    status = response_obj.get("status")
    image_generated=response_obj.get("filename")

    print(f'response received  :: {status}')

    if status == "Completed":
       
       # display image
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=IMAGE_OUTPUT_BUCKET, Key=image_generated)
        file_stream = BytesIO(response['Body'].read())
        st.image(file_stream,width=400)
    else:
        print(' No image to display')
                   

#----------------------------------------------------------------------------------------
# Subscription registration
#----------------------------------------------------------------------------------------
def subscribe_to_imagegen_updates():
    """Subscribe to GraphQL subscription for image generation status updates."""

    if auth.is_authenticated():
        # Get user tokens
        access_token, id_token = auth.get_user_tokens()

        # Decode ID token
        decoded_token = auth.decode_id_token(id_token)

        # Get  job ID
        job_id = decoded_token.get("cognito:username", id_token[:10])

        # Subscribe to GraphQL subscription
        subscription_client = GraphQLSubscriptionClient(GRAPHQL_ENDPOINT, id_token)
        variables = {"jobid": job_id}

        print(f'start subscription :: ')
        subscription_client.subscribe(
            Subscriptions.UPDATE_GENERATE_IMAGE_JOB_STATUS,
            "updateGenerateImageStatus",
            variables,
            on_message_callback=on_message_update,
            on_subscription_registered_callback=on_subscription_registered
        )

#========================================================================================
# [View] Render UI components  
#========================================================================================
# Streamlit page configuration
st.set_page_config(page_title="Q&A", page_icon=":camera:", layout="wide") 
hide_deploy_button()

# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper() 
auth.set_session_state()
auth.print_login_logout_buttons()

# Logged in user UI
if auth.is_authenticated():
    
    # Add a divider here
    st.markdown("---")

    #Display text
    st.markdown("Enter text to Generate Image!")

    # Add Clear button
    if st.button("Clear"):
        st.session_state.encode_input_text = ""
        st.text_input=st.empty

    input_text = st.text_input('Generate Image', 'Please enter text to Generate Image!')
    encode_input_text= base64.b64encode(input_text.encode("utf-8")).decode("utf-8") 
    st.session_state.encode_input_text=encode_input_text

    if st.button("Generate"):
        if not st.session_state.encode_input_text:
            st.warning("Please enter valid text.")
        else:    
            subscribe_to_imagegen_updates()

# Guest user UI 
elif not auth.is_authenticated():
    st.write("Please login and select a document!")
    st.stop()


#########################
#        SIDEBAR
#########################

# sidebar
MODEL_ID_OPTIONS=['stability.stable-diffusion-xl','']
MODEL_ID_PROVIDER=['Bedrock','Sagemaker Endpoint',]

with st.sidebar:
        st.header("Settings")
        st.subheader("Image Generation Configuration")

        model_config = st.selectbox(
                label="Select model id:",
                options=MODEL_ID_OPTIONS,
                key="model_id",
                help="Select model type to generate image for your entered text.",
            )
     
        provider = st.selectbox(
                label="Select  model provider:",
                options=MODEL_ID_PROVIDER,
                key="provider",
                help="Select model provider.",
            )       
        cfg_scale = st.number_input(
                label="cfg_scale:",
                value=10,
                min_value=0,
                max_value=90,
                key="cfg_scale",
            )
        seed = st.number_input(
                label="seed:",
                value=0,
                min_value=0,
                max_value=90,
                key="seed",
            )
        steps = st.number_input(
                label="steps:",
                value=10,
                min_value=0,
                max_value=90,
                key="steps",
            )
        
        

