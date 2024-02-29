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

from st_pages import show_pages,Section, Page, hide_pages,add_page_title


#========================================================================================
# [View] Render UI components  
#========================================================================================
# Streamlit page configuration
#pages = ["1_📁_Select_Document", "2_🏷️_Summary", "3_💬_Q&A","4_:camera:_Image_Generation"]
#add_page_title()

show_pages(
    [
        #Section("Document Explorer", icon="📃"),
        Page("pages/1_Select_Document.py", "Select Document", "📁",in_section=True),
        Page("pages/2_Summary.py", "Summary", "🏷️",in_section=True),
        Page("pages/3_Q&A.py", "Q&A", "💬",in_section=True),
        #Section(name="Content Generation", icon="🎨"),
        Page("pages/4_Image_Generation.py", "Image Generation", "📸",in_section=True),
        Page("pages/5_Image_Search.py", "Image Search", "🔎",in_section=True),

    ]
)

selected = option_menu(
        menu_title="AWS-GENERATIVE-AI-CDK-CONSTRUCTS SAMPLE APPS",
        options=["Document Explorer", 'Content Generation'], 
        icons=['💬', '📸'],
        menu_icon="cast", 
        #default_index=0,
        orientation='horizontal'
        )


# Define a function to hide selected pages
# def hide_pages(pages_to_hide):
#     for page in pages_to_hide:
#         st.sidebar.markdown(f"## {page}")
#         st.sidebar.markdown("This page is hidden.")

#with st.sidebar:
# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper() 
auth.set_session_state()
auth.print_login_logout_buttons()

if auth.is_authenticated():
    if selected == "Document Explorer":
        st.title="You have selected document explorer "
        hide_pages(["Image Generation","Image Search"])
        hide_deploy_button()

        # Guest user UI 
        st.write("# Welcome to Document Explorer!")
        st.markdown('''
        The Sample Generative AI Application demonstrates how to build end-to-end solutions leveraging AWS services and the [Generative AI Constructs library](https://github.com/awslabs/generative-ai-cdk-constructs).

        It includes examples of key components needed in generative AI applications:

        - [Data Ingestion Pipeline](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-rag-appsync-stepfn-opensearch): Ingests documents, converts them to text, and stores them in a knowledge base for retrieval. This enables long context window approaches.

        - [Document Summarization](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-summarization-appsync-stepfn): Summarizes PDF documents leveraging Large Language Models like Anthropic Claude V2 via Amazon Bedrock. 

        - [Question Answering](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-qa-appsync-opensearch): Answers natural language questions by retrieving relevant documents from the knowledge base and leveraging Large Language Models.

        By providing reusable constructs following AWS best practices, this app enables quickly building custom generative AI apps on AWS. The constructs abstract complexity of orchestrating AWS services like Lambda, OpenSearch, Step Functions, Bedrock, etc.

        Here is the architecture diagram of the sample application:
        ''')
        st.image('assets/doc_explorer_diagram.png', width=700)
        st.markdown('<style>div[class="stApp"] > div[class="css-1es6loc e1tzin5j2"]{text-align:center;}</style>', unsafe_allow_html=True)


        
    if selected == "Content Generation":
        hide_pages(["Q&A","Select Document","Summary"])

    else:
        hide_pages(["Q&A","Select Document","Summary","Image Generation","Image Search"])

else:
    hide_pages(["Q&A","Select Document","Summary","Image Generation","Image Search"])
    st.write("Please login!")
    st.stop()