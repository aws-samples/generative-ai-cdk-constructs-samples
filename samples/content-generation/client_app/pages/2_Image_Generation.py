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
IMAGE_OUTPUT_BUCKET = os.environ.get("S3_GENERATED_BUCKET") 



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
            "imageInput":{
                    "model_config": {
                        "modelId": params['model_id'],
                        "provider": params['provider'],
                        "model_kwargs":"{\n \"cfg_scale\":"+str(params['cfg_scale'])+",\"seed\":"+str(params['seed'])+",\"steps\":"+str(params['steps'])+",\"style_preset\":\""+params['style_preset']+"\",\"clip_guidance_preset\":\""+params['clip_guidance_preset']+"\",\"sampler\":\""+params['sampler']+"\"}"
            
            },
            "jobid": job_id,
            "filename": '',            
            "input_text": params['input_text'],
            "negative_prompts":params['negative_prompts']
        }
        }
       

        print(f'calling img gen mutation :: {variables}')
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
        "negative_prompts":st.session_state.encode_negative_prompts,
        "cfg_scale":st.session_state["cfg_scale"],
        "seed":st.session_state["seed"],
        "steps":st.session_state["steps"],
        "style_preset":st.session_state["style_preset"],
        "clip_guidance_preset":st.session_state["clip_guidance_preset"],
        "sampler":st.session_state["sampler"],
        "width":st.session_state["width"],
        "height":st.session_state["height"]
    }
    generate_image_based_on_text(params)

def clear_text():
        st.session_state["input_text"] = ""   
        st.session_state.encode_input_text = ""
        st.session_state["negative_prompts"] = ""   
        st.session_state.encode_negative_prompts = ""

def on_message_update(message, subscription_client):
    """Callback when image generation job status update is received."""
    response_obj = message.get("updateGenerateImageStatus")
    print(f'response received or not :: {response_obj}')
    if not response_obj:
        return

    status = response_obj.get("status")
    image_generated=response_obj.get("filename")
    message = response_obj.get("message")

    print(f'response received  :: {status}')

    if status == "Completed":
       # display image
        print(f"display image {image_generated} from {IMAGE_OUTPUT_BUCKET}")
        s3 = boto3.client('s3')
        try:
            response = s3.get_object(Bucket=IMAGE_OUTPUT_BUCKET, Key=image_generated)
            file_stream = BytesIO(response['Body'].read())
            st.image(file_stream,width=400)
        except Exception as e:
            print(f'error in displaying image :: {e}')
        subscription_client.unsubscribe()
    if status == "Blocked":
         st.warning(message)
         subscription_client.unsubscribe()
    else:
        print(' No image to display')
        subscription_client.unsubscribe()
                   

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
        print(f'job id :: {job_id}')
        variables = {"jobid": job_id}

        print(f'start subscription :: ')
        subscription_client.subscribe(
            Subscriptions.UPDATE_GENERATE_IMAGE_JOB_STATUS,
            "UpdateGenerateImageStatus",
            variables,
            on_message_callback=on_message_update,
            on_subscription_registered_callback=on_subscription_registered
        )

#========================================================================================
# [View] Render UI components  
#========================================================================================
# Streamlit page configuration

st.set_page_config(page_title="Image Generation", page_icon=":camera:",
                    layout="wide",initial_sidebar_state="expanded")
add_indentation() 
st.session_state['selected_nav_index']=1

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
    st.markdown("Please select model configuration from side bar. " )

    
    input_text = st.text_area('Image Prompt',
    placeholder='Please enter text to Generate Image!',
    max_chars=100,key="input_text")
    st.write(f'You wrote {len(input_text)} characters.')

    negative_prompts = st.text_area('Negative Prompts',
    placeholder='Please specify what you do not want in the generated Image!',
    max_chars=100,key="negative_prompts")

    encode_input_text= base64.b64encode(input_text.encode("utf-8")).decode("utf-8") 
    st.session_state.encode_input_text=encode_input_text

    encode_negative_prompts= base64.b64encode(negative_prompts.encode("utf-8")).decode("utf-8") 
    st.session_state.encode_negative_prompts=encode_negative_prompts

    col1, col2,col3 = st.columns([3, 1, 5])

    with col1:
        if st.button("Generate",type='primary'):
            if not st.session_state.encode_input_text:
                st.warning("Please enter valid text.")
            else:    
                subscribe_to_imagegen_updates()
    with col2:
         st.button("Clear",type='primary',on_click=clear_text)
            
    
# Add Clear button
    

# Guest user UI 
elif not auth.is_authenticated():
    st.write("Please login")
    st.stop()


#########################
#        SIDEBAR
#########################

# sidebar
MODEL_ID_OPTIONS=['stability.stable-diffusion-xl','amazon.titan-image-generator-v1']
MODEL_ID_PROVIDER=['Bedrock','Sagemaker Endpoint',]
STYLE_PRESET_OPTIONS=['photographic', 'digital-art', 'cinematic']
CLIP_GUIDANCE_PRESET_OPTIONS=['FAST_BLUE', 'FAST_GREEN', 'NONE', 'SIMPLE SLOW', 'SLOWER SLOWEST']
SAMPLER_OPTIONS=['DDIM', 'DDPM', 'K_DPMPP_SDE', 'K_DPMPP_2M', 'K_DPMPP_2S_ANCESTRAL', 'K_DPM_2', 'K_DPM_2_ANCESTRAL', 'K_EULER', 'K_EULER_ANCESTRAL', 'K_HEUN, K_LMS']


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
          
        clip_guidance_preset = st.selectbox(
                label="Clip guidance preset",
                options=CLIP_GUIDANCE_PRESET_OPTIONS,
                key="clip_guidance_preset",
                help="(e.g. FAST_BLUE FAST_GREEN NONE SIMPLE SLOW SLOWER SLOWEST)",
            )  
        style_preset = st.selectbox(
                label="Style preset",
                options=STYLE_PRESET_OPTIONS,
                key="style_preset",
                help="(e.g. photographic, digital-art, cinematic, ...)",
            )  
        sampler = st.selectbox(
                label="sampler",
                options=SAMPLER_OPTIONS,
                key="sampler",
                help="(e.g. DDIM, DDPM, K_DPMPP_SDE, K_DPMPP_2M, K_DPMPP_2S_ANCESTRAL, K_DPM_2, K_DPM_2_ANCESTRAL, K_EULER, K_EULER_ANCESTRAL, K_HEUN, K_LMS)",
            )  
        
        width = st.number_input(
                label="width:",
                value=512,
                min_value=0,
                max_value=1024,
                key="width",
            )
        
        height = st.number_input(
                label="height:",
                value=512,
                min_value=0,
                max_value=1024,
                key="height",
            )
        
        cfg_scale = st.number_input(
                label="cfg_scale:",
                value=5,
                min_value=0,
                max_value=30,
                key="cfg_scale",
            )
        seed = st.number_input(
                label="seed",
                value=452345,
                min_value=0,
                max_value=4523455,
                key="seed",
            )
        steps = st.number_input(
                label="steps:",
                value=10,
                min_value=0,
                max_value=90,
                key="steps",
            )
        
        
        

