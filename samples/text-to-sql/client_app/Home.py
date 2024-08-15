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
from st_pages import show_pages, Section, Page, hide_pages, add_indentation


# ========================================================================================
# [View] Render UI components
# ========================================================================================
# Streamlit page configuration
st.set_page_config(
    page_title="Generative AI CDK Constructs Samples", page_icon="🤖")
add_indentation()

show_pages(
    [
        Section("Home", icon="🏠"),
        Page("pages/1_🤖_text_to_sql_client.py",
             "Insight to Data", "🤖", in_section=True),
        Page("pages/2_📈_text_to_sql_metrics.py",
             "Metrics ", "🤖", in_section=True),

    ]
)

# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper()
auth.set_session_state()
auth.print_login_logout_buttons()

# Guest user UI
st.write("# Welcome to Text to SQL Application.")
st.markdown('''

This sample application harnesses the power of generative AI to generate SQL from natural language.

        
Here is the architecture diagram of the sample application:
''')

st.image('assets/architecture.png', width=700)
st.markdown(
    '<style>div[class="stApp"] > div[class="css-1es6loc e1tzin5j2"]{text-align:center;}</style>', unsafe_allow_html=True)


if auth.is_authenticated():

    hide_deploy_button()

else:
    hide_pages(["Text To SQL Sample App"])
    st.info("Please login!")
    st.stop()
