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
import tempfile
import pandas as pd

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

METRIC_BUCKET = os.environ.get("CONFIG_BUCKET")


# ========================================================================================
# [Response]: Long Polling
# ========================================================================================
def display_config_files():
    # Download the selected file from S3
    key = "metric/"+"texttosql_metrics.csv"
    print(f"get file: {key} from  {METRIC_BUCKET}") 
   
    try:
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False) as temp_file:
                s3.download_fileobj(METRIC_BUCKET, key, temp_file)
                temp_file.seek(0)
                print(f"temp file: {temp_file.name}")
    except Exception as e:
        st.error(f"Error downloading file from S3: {e}")
    print("read csv in pd")
    df = pd.read_csv(temp_file.name)  
    print(df) 
    st.write(df)
    
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
    st.title("Metrics") 

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
    
    print("display_config_files")
    display_config_files()
    
   
    

    
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
    st.subheader("Metrics")

   