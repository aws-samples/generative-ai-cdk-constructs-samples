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
import os
import time
import base64
# Third party imports 
import jwt
import boto3
import requests
import streamlit as st
from dotenv import load_dotenv

class CognitoHelper:
    """Handles user authentication with AWS Cognito."""

    def __init__(self):
        # Initializes class variables from environment variables.
        load_dotenv()
        self.cognito_domain = os.environ.get("COGNITO_DOMAIN")
        self.client_id = os.environ.get("CLIENT_ID")
        self.client_secret = os.environ.get("CLIENT_SECRET")
        self.app_uri = os.environ.get("APP_URI")

        self.region = os.environ.get("REGION")
        self.user_pool_id = os.environ.get("USER_POOL_ID")
        self.identity_pool_id = os.environ.get("IDENTITY_POOL_ID")
        self.authenticated_role_arn = os.environ.get("AUTHENTICATED_ROLE_ARN")
            
        # Initializes class variables from Cognito domain.
        self.token_url = f"{self.cognito_domain}/oauth2/token"
        self.login_link = f"{self.cognito_domain}/login?client_id={self.client_id}&response_type=code&scope=email+openid&redirect_uri={self.app_uri}"
        self.logout_link = f"{self.cognito_domain}/logout?client_id={self.client_id}&logout_uri={self.app_uri}"

    def decode_id_token(self, id_token = None):
        decoded = {}

        if id_token is None:
            id_token = st.session_state.get("id_token", "")

        if id_token != "":
            decoded = jwt.decode(id_token, options={"verify_signature": False})
            
        return decoded

    def get_user_tokens(self, auth_code = None):
        """Gets user access and ID tokens using auth code."""

        access_token = ""
        id_token = ""

        # if auth_code is not provided, try to get credentianls from the session state.
        if not auth_code:
            access_token = st.session_state.get("access_token", "")
            id_token = st.session_state.get("id_token", "")

            if access_token != "" and id_token != "":
                return access_token, id_token

        try:
            client_secret_string = f"{self.client_id}:{self.client_secret}"
            client_secret_encoded = base64.b64encode(client_secret_string.encode("utf-8")).decode("utf-8")
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {client_secret_encoded}",
            }
            body = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "code": auth_code,
                "redirect_uri": self.app_uri,
            }
            
            token_response = requests.post(self.token_url, headers=headers, data=body)
            access_token = token_response.json()["access_token"]
            id_token = token_response.json()["id_token"]

        except (KeyError, TypeError):
            access_token = ""
            id_token = ""
            
        return access_token, id_token

    def get_user_temporary_credentials(self, id_token = None):
        #If id_token is not provided, try to get credentianls from the session state.
        if not id_token:
            return {
                "AccessKeyId": st.session_state.get("access_key_id", ""),
                "SecretAccessKey": st.session_state.get("secret_access_key", ""),
                "SessionToken": st.session_state.get("session_token", "")
            }

        sts_client = boto3.client('sts')
        cognito_client = boto3.client('cognito-identity', region_name=self.region)

        response = cognito_client.get_id(
            IdentityPoolId=self.identity_pool_id,
            Logins={
               f'cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}': id_token
            }
        )
        identity_id = response['IdentityId']

        response = cognito_client.get_open_id_token(
            IdentityId=identity_id,
            Logins={
                f'cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}': id_token
            }
        )
        web_identity_token = response['Token']

        response = sts_client.assume_role_with_web_identity(
            RoleArn=self.authenticated_role_arn,
            RoleSessionName='authenticated-session',
            WebIdentityToken=web_identity_token
        )

        return response['Credentials']

    def set_session_state(self):
        """Sets session state variables after authentication."""
        try:
            
            auth_query_params = st.query_params.to_dict()
            if "code" not in auth_query_params or not auth_query_params["code"]:
                return

            auth_code = auth_query_params["code"]
            access_token, id_token = self.get_user_tokens(auth_code)

            if access_token != "":
                st.session_state["auth_code"] = auth_code
                st.session_state["access_token"] = access_token

            if id_token != "":
                st.session_state["id_token"] = id_token
                credentials = self.get_user_temporary_credentials(id_token)
                st.session_state["access_key_id"] = credentials["AccessKeyId"]
                st.session_state["secret_access_key"] = credentials["SecretAccessKey"]
                st.session_state["session_token"] = credentials["SessionToken"]
                st.session_state["expiration"] = credentials["Expiration"]

        except (KeyError, TypeError):
            return

    def is_authenticated(self):
        """Checks if user is authenticated."""

        access_key_id = st.session_state.get("access_key_id", "")
        secret_access_key = st.session_state.get("secret_access_key", "")
        session_token = st.session_state.get("session_token", "")
        expiration = st.session_state.get("expiration")

        is_valid_session = (access_key_id != "" and secret_access_key != "" and session_token != "")
        # +5 seconds to consider a expiry buffer. If the session is about to expire, we need to renew it.
        has_not_expired = (expiration.timestamp() > (time.time() + 5)) if expiration else True

        return is_valid_session and has_not_expired
    
    def print_login_logout_buttons(self):
        """Prints login and logout buttons."""

        html_css_login = """
        <style>
        .button-container {
            display: flex;
            justify-content: center;
        }

        .button-login {
            background-color: #28a745;
            color: #fff !important;
            padding: 0.5rem 1rem;
            border-radius: 0.25rem;
            text-decoration: none;
            font-size: 0.9rem;
        }

        .button-logout {
            background-color: #dc3545;
            color: #fff !important;
            padding: 0.5rem 1rem;
            border-radius: 0.25rem;
            text-decoration: none;
            font-size: 0.9rem;
        }

        .button-login:hover {
            background-color: #218838;
        }

        .button-logout:hover {
            background-color: #c82333; 
        }

        .button-login:active,
        .button-logout:active {
            background-color: #1e7e34;
        }
        </style>
        """

        html_button_login = (
        html_css_login
        + f"<div class='button-container'><a href='{self.login_link}' class='button-login' target='_self'>Log In</a></div>"
        )

        html_button_logout = (
        html_css_login
        + f"<div class='button-container'><a href='{self.logout_link}' class='button-logout' target='_self'>Log Out</a></div>"
        )

        if not self.is_authenticated():
            return st.sidebar.markdown(f"{html_button_login}", unsafe_allow_html=True)
        else:
            return st.sidebar.markdown(f"{html_button_logout}", unsafe_allow_html=True)