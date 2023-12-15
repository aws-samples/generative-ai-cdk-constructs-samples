# Third party imports 
import streamlit as st
# Local imports
from common.cognito_helper import CognitoHelper
from common.streamlit_utils import hide_deploy_button

#========================================================================================
# [View] Render UI components  
#========================================================================================
# Streamlit page configuration
st.set_page_config(page_title="Generative AI CDK Constructs Samples", page_icon="🤖")
hide_deploy_button()

# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper() 
auth.set_session_state()
auth.print_login_logout_buttons()

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