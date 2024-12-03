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
from st_pages import show_pages, Page, Section

from common.streamlit_utils import hide_deploy_button
#from streamlit_option_menu import option_menu

#========================================================================================
# [View] Render UI components  
#========================================================================================
# Streamlit page configuration
st.set_page_config(
    page_title="Generative AI CDK Constructs Samples", page_icon="🤖")

show_pages([
    Section("Document Explorer", icon="📁"),
    Page("pages/1_doc_explorer_home.py", "Home", "🏠", in_section=True),
    Page("pages/2_Select_Document.py", "Select Document", "📃", in_section=True), 
    Page("pages/3_Q&A.py", "Q&A", "💬", in_section=True),
    Page("pages/4_Summary.py", "Summary", "🏷️", in_section=True),
    Page("pages/5_Visual_Q&A.py", "Visual Q&A", "👁️‍🗨️", in_section=True)
])

auth = CognitoHelper() 
auth.set_session_state()
auth.print_login_logout_buttons()

if auth.is_authenticated():
        hide_deploy_button()
else:
    st.info("Please login!")
    st.stop()