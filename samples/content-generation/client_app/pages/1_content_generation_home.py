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


#========================================================================================
# [View] Render UI components  
#========================================================================================
# Streamlit page configuration
# Check if user is authenticated and display login/logout buttons
auth = CognitoHelper() 
auth.set_session_state()
auth.print_login_logout_buttons()

if auth.is_authenticated():
       
        hide_deploy_button()

        # Guest user UI 
        st.write("# Welcome to Content Generation!")
        st.markdown('''
        
The Sample Generative AI Application demonstrates how to leverage AWS services and the Generative AI Constructs library to generate content like images.


Using the Content Generation constructs, you can generate images from text prompts by connecting to generative AI models like Amazon TITAN or Stability AI's Stable Diffusion. The constructs provide a serverless backend to call these models from your app. 

By wrapping the complexity of orchestrating services like AWS Lambda, Amazon AppSync, and Amazon Bedrock, the Generative AI Constructs library enables you to quickly build custom generative AI applications following AWS best practices. 

Please refer here for more information on the construct:             
- [Content Generation](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-contentgen-appsync-lambda): Generate images from text using Amazon titan-image-generator-v1 or stability.stable-diffusion-xl model.

With just a few lines of configuration, you can connect your app to a generative model endpoint to start creating images. The constructs handle provisioning and connecting the underlying AWS services.

This accelerated development, along with the reliability and scalability of AWS, makes it easy to build sophisticated generative AI apps. 
                    
Here is the architecture diagram of the sample application:
        ''')
        st.image('assets/image_generation.png', width=700)
        st.markdown('<style>div[class="stApp"] > div[class="css-1es6loc e1tzin5j2"]{text-align:center;}</style>', unsafe_allow_html=True)


else:
    st.write("Please login!")
    st.stop()