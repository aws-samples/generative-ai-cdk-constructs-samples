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
from st_pages import  get_nav_from_toml



# ========================================================================================
# [View] Render UI components
# ========================================================================================
# Streamlit page configuration
st.set_page_config(
    page_title="Generative AI CDK Constructs Samples", page_icon="🤖")

#sections = st.sidebar.toggle("Sections", value=True, key="use_sections")

nav = get_nav_from_toml(
    "pages/pages_sections.toml" 
)
pg = st.navigation(nav)
pg.run()


#add_page_title(pg)


# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper()
auth.set_session_state()
auth.print_login_logout_buttons()


if auth.is_authenticated():

    hide_deploy_button()

else:
    st.info("Please login!")
    
