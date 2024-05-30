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
# Third party imports 
import streamlit as st
# Local imports
from common.cognito_helper import CognitoHelper
from common.streamlit_utils import hide_deploy_button
from streamlit_option_menu import option_menu

from st_pages import show_pages,Section, Page, hide_pages,add_indentation


#========================================================================================
# [View] Render UI components  
#========================================================================================
# Streamlit page configuration
st.set_page_config(page_title="Generative AI CDK Constructs Samples", page_icon="🤖")
add_indentation() 

show_pages(
    [
        Section("Home", icon="🏠"),
        Page("pages/image_description.py", "Image Description", "📸",in_section=True),
        
    ]
)

#with st.sidebar:
# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper() 
auth.set_session_state()
auth.print_login_logout_buttons()

# Guest user UI 
st.write("# Welcome to Image Description Application.")
st.markdown('''

This sample application harnesses the power of generative AI to generate multi-lingual descriptions for uploaded images.
Leveraging the [Document Summarization](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-summarization-appsync-stepfn) construct,
This sophisticated solution employs the advanced capabilities of Anthropic's Claude 3 with Amazon Bedrock to generate comprehensive and accurate image descriptions across multiple languages.

For more details please refer https://github.com/aws-samples/generative-ai-cdk-constructs-samples/blob/main/samples/document_explorer/README.md            
        
Here is the architecture diagram of the sample application:
''')

st.image('assets/architecture.png', width=700)
st.markdown('<style>div[class="stApp"] > div[class="css-1es6loc e1tzin5j2"]{text-align:center;}</style>', unsafe_allow_html=True)


if auth.is_authenticated():
   
        hide_deploy_button()
      
else:
    hide_pages(["Image Description"])
    st.info("Please login!")
    st.stop()