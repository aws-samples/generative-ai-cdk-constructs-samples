#!/usr/bin/env python3
import aws_cdk as cdk

from frontend_stack import FrontendStack

app = cdk.App()

APP_PREFIX = "StreamlitServerlessApp"

app_env_vars = {
    "STREAMLIT_SERVER_PORT": "8501"
}

# Create the front-end Stack
frontend_stack = FrontendStack(app, f"{APP_PREFIX}-FrontendStack")

app.synth()
