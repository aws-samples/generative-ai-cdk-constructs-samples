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

import streamlit as st
import boto3
import uuid
import json
import websockets
import asyncio
import base64
import requests
from enum import Enum
import os
from threading import Thread, Event
import logging
from queue import Queue, Empty
import time
from streamlit.runtime.scriptrunner import add_script_run_ctx
from urllib.parse import urlencode

logging.basicConfig(level=logging.INFO)  # Set to DEBUG for more details

MAX_BUTTONS_PER_ROW = 3
EXAMPLE_PROMPTS = [
    "Tell me a math joke",
    "Why was the math book sad?",
    "Why can't the bicycle stand by itself?",
    "Who is the whale closest relative on land?",
    "I'm sad, tell me something funny",
]

class StreamStatus(str, Enum):
    STARTED = "STARTED"
    STREAMING = "STREAMING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

# Cognito configuration
def get_config_value(key: str) -> str:
    """Get configuration from environment variables first, then secrets"""
    # Try environment variables first (for container deployment)
    env_value = os.environ.get(key)
    if env_value:
        return env_value
    if not st.secrets:
        st.error("No secrets found. Please configure your secrets.")
        st.stop()
    secrets_value = st.secrets.get(key)
    st.warning(f"Using secrets. {key}: {secrets_value}")
    if not secrets_value:
        st.error(f"No value found for {key}. Please configure your secrets.")
        st.stop()
    return secrets_value

COGNITO_APP_CLIENT_ID =  get_config_value('COGNITO-APP-CLIENT-ID')
COGNITO_DOMAIN_PREFIX = get_config_value('COGNITO-DOMAIN-PREFIX')
APPSYNC_API_ENDPOINT =  get_config_value('APPSYNC-API-ENDPOINT')
REGION = get_config_value('AWS-REGION')
REDIRECT_URI = get_config_value("REDIRECT_URI")
LOGOUT_URI =  get_config_value("LOGOUT_URI")

st.session_state.REDIRECT_URI = REDIRECT_URI

ASK_AGENT_MUTATION = """
        mutation AskAgent($question: String!, $sessionId: String!) {
            askAgent(question: $question, sessionId: $sessionId) {
                sessionId
                status
            }
        }
    """
SUBSCRIPTION = """subscription WatchUpdates($sessionId: String!) {
            onAgentResponse(sessionId: $sessionId) {
                sessionId
                content
                status
            }
        }
    """

def handle_callback():
    if 'code' in st.query_params and not st.session_state.is_authenticated:
        try:
            token_endpoint = f"https://{COGNITO_DOMAIN_PREFIX}.auth.{REGION}.amazoncognito.com/oauth2/token"

            # Prepare the token request
            token_data = {
                'grant_type': 'authorization_code',
                'client_id': COGNITO_APP_CLIENT_ID,
                'code': st.query_params['code'],
                'redirect_uri': REDIRECT_URI
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            # Make the token request
            response = requests.post(
                token_endpoint,
                data=token_data,
                timeout=(3.05, 27),
                headers=headers
            )
            response.raise_for_status() 
            tokens = response.json()
            logging.info(f"Token response status: {response.status_code}")
            if response.status_code == 200:
                st.session_state.auth_token = tokens['id_token']
                st.session_state.refresh_token = tokens['refresh_token']
                st.session_state.is_authenticated = True
            else:
                logging.error(f"Token exchange failed: {response.text}")
                st.error("Authentication failed")
        except requests.exceptions.HTTPError as e:
            st.error(f"HTTP error occurred while fetching token: {e}")
        except requests.exceptions.Timeout as e:
            st.error(f"Timeout error occurred while fetching token: {e}")
        except requests.exceptions.RequestException as e:
            st.error(f"Error occurred while fetching token: {e}")
        except json.JSONDecodeError as e:
            st.error(f"Error decoding token response: {e}")
        except Exception as e:
            st.error(f"Authentication failed: {e}")


def get_login_url():
    params = {
        'client_id': COGNITO_APP_CLIENT_ID,
        'response_type': 'code',
        'scope': 'email openid profile',
        'redirect_uri': st.session_state.REDIRECT_URI
    }
    
    domain_url = f"https://{COGNITO_DOMAIN_PREFIX}.auth.{REGION}.amazoncognito.com"
    return f"{domain_url}/oauth2/authorize?{urlencode(params)}"


def logout():
    # Store the current token before clearing session
    refresh_token = st.session_state.refresh_token if 'refresh_token' in st.session_state else None
    COGNITO_DOMAIN = f"{COGNITO_DOMAIN_PREFIX}.auth.{REGION}.amazoncognito.com"
    if refresh_token:
        try:
            response = requests.post(
                f"https://{COGNITO_DOMAIN}/oauth2/revoke",
                data={
                    "token": refresh_token,
                    "client_id": COGNITO_APP_CLIENT_ID,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=(3.05, 27),
            )
            if response.status_code != 200:
                logging.error(f"Failed to revoke token: {response.text}")
        except Exception as e:
            logging.error(f"Exception during token revocation: {str(e)}")

    
    # Clear session state
    st.session_state.is_authenticated = False
    st.session_state.auth_token = None
    
    # Clear query parameters
    st.query_params.clear()
    
    # Construct the Cognito logout URL
    COGNITO_LOGOUT_URL = f"https://{COGNITO_DOMAIN}/logout?client_id={COGNITO_APP_CLIENT_ID}&logout_uri={LOGOUT_URI}"
    logging.debug(f"Redirecting to Cognito Logout URL: {COGNITO_LOGOUT_URL}")
    # Redirect the user to the Cognito logout page
    st.markdown(f'<meta http-equiv="refresh" content="0; url={COGNITO_LOGOUT_URL}" />', unsafe_allow_html=True)

    
def custom_css():
    st.markdown(
        f"""
        <style>
        [data-testid="stHeader"] {{
            display: none;  /* Hide default Streamlit header */
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    if "auth_token" not in st.session_state:
        st.session_state.auth_token = None
    if "response_queue" not in st.session_state:
        st.session_state.response_queue = Queue()
    if "error_queue" not in st.session_state:
        st.session_state.error_queue = Queue()
    if "streaming" not in st.session_state:
        st.session_state.streaming = False
    if "current_prompt" not in st.session_state:
        st.session_state.current_prompt = None

def send_mutation(question: str, auth_token: str) -> str:
    if "session_id" not in st.session_state: 
        logging.info("Session ID not found, creating a new one.")
        st.session_state.session_id = str(uuid.uuid4())
        logging.info(f"New session ID created: {st.session_state.session_id}")
    else:
        logging.info(f"Using existing session ID: {st.session_state.session_id}") 

    headers = {
        'Content-Type': 'application/json',
        'Authorization': auth_token
    }
    
    payload = {
        'query': ASK_AGENT_MUTATION,
        'variables': {
            'question': question,
            'sessionId': st.session_state.session_id
        }
    }
    try:
        response = requests.post(
            APPSYNC_API_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=(3.05, 27)  # (connect timeout, read timeout)
        )
        response.raise_for_status()
        
        result = response.json()
        logging.info(f"Mutation sent. Response: {response.text}")
        return result['data']['askAgent']['sessionId']

    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error occurred: {e}")
        logging.error(f"Response content: {e.response.content}")
    except requests.exceptions.Timeout as e:
        logging.error(f"Request timed out: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
    except (KeyError, json.JSONDecodeError) as e:
        logging.error(f"Error parsing response: {e}")
        logging.error(f"Response content: {response.content}")

def get_ws_url(auth_token: str) -> str:
    """Prepare WebSocket URL with authentication"""
    api_host = APPSYNC_API_ENDPOINT.replace('https://', '').replace('/graphql', '')
    ws_url = f"wss://{api_host.replace('appsync-api', 'appsync-realtime-api')}/graphql"
    
    header = {
        'host': api_host,
        'Authorization': auth_token
    }
    
    payload = {}

    base64_header = base64.b64encode(json.dumps(header).encode()).decode()
    base64_payload = base64.b64encode(json.dumps(payload).encode()).decode()

    return f"{ws_url}?header={base64_header}&payload={base64_payload}"

def start_subscription_thread(ws_url: str, session_id: str, auth_token: str):
    """Run subscription in a separate thread"""
    completion_event = Event()

    async def run_subscription():
        async with websockets.connect(
            ws_url,
            subprotocols=['graphql-ws']
        ) as websocket:
            await websocket.send(json.dumps({
                "type": "connection_init",
                "payload": {}
            }))
            
            ack = await websocket.recv()
            logging.info(f"Received ack: {ack}")
            subscription_id = str(uuid.uuid4())
            subscription_message = {
                "type": "start",
                "id": subscription_id,
                "payload": {
                    "data": json.dumps({
                        "query": SUBSCRIPTION,
                        "variables": {
                            "sessionId": session_id
                        }
                    }),
                    "extensions": {
                        "authorization": {
                            "host": APPSYNC_API_ENDPOINT.replace('https://', '').replace('/graphql', ''),
                            "Authorization": auth_token
                        }
                    }
                }
            }
            
            await websocket.send(json.dumps(subscription_message))
            logging.info(f"Subscription started")
            try:
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    logging.info(f"Received message: {data}")
                    if data.get("type") == "data" and "payload" in data:
                        result = data["payload"].get("data", {})
                        if "onAgentResponse" in result:
                            response = result["onAgentResponse"]
                            #callback(response, placeholder)
                            st.session_state.response_queue.put(response)
                            
                            if response.get("status") in ["COMPLETED", "ERROR"]:
                                stop_message = {
                                    "type": "stop",
                                    "id": subscription_id
                                }
                                await websocket.send(json.dumps(stop_message))
                                logging.info("Stopping subscription")
                                completion_event.set()
                                break
                                
                    elif data.get("type") == "ka":
                        continue
                    
            except Exception as e:
                st.error(f"Error in websocket loop: {e}")
                st.session_state.error_queue.put(str(e))
                completion_event.set()
            finally:
                completion_event.set()

    def run_async_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_subscription())

    thread = Thread(target=run_async_loop, daemon=True)
    add_script_run_ctx(thread)
    thread.start()
    return completion_event

def chat_interface():
    flexible_col, fixed_col1, fixed_col2 = st.columns([0.01, 1, 0.01])

    with flexible_col:
        st.empty()

    with fixed_col1:
        logout_button = st.button(
            "↪️", 
            type="secondary", 
            key="logout",
            help="Logout"
        )
    with fixed_col2:
        clear_button = st.button(
            "🗑️", 
            type="secondary", 
            key="clear_chat",
            help="Clear chat history"
        )

    # Handle button clicks
    if clear_button:
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.streaming = False
        st.rerun()

    if logout_button:
        logout()

    # Create main content container with margin at bottom
    def welcome_message():
        st.markdown(
                    """
                    <div style="text-align: center; padding: 50px 0;">
                        <h2>👋 Welcome to Amazon Bedrock Agent!</h2>
                        <p>Type your question below or pick one of these examples:</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
    
    message_container = st.container()
    if not st.session_state.messages and not st.session_state.streaming:
        with st.empty():
            welcome_message()
        for i in range(0, len(EXAMPLE_PROMPTS), MAX_BUTTONS_PER_ROW):
            with st.empty():
                row_prompts = EXAMPLE_PROMPTS[i:i + MAX_BUTTONS_PER_ROW]
                cols = st.columns(MAX_BUTTONS_PER_ROW)
                
                # Add buttons to the columns
                for j, prompt in enumerate(row_prompts):
                    with cols[j]:
                        if st.button(
                            prompt,
                            key=f"example_{prompt}",
                            use_container_width=True,
                            type="secondary"
                        ):
                            st.session_state.streaming = True
                            st.session_state.current_prompt = prompt
                            st.session_state.messages.append({"role": "user", "content": prompt})
                            st.rerun()
    else:
        with message_container:
            # Display chat messages
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    if "\n\n" in message["content"]:
                        format_messages(message["content"].split("\n\n"))
                    else:
                        st.markdown(message["content"])
                    if message.get("final_answer"):
                            st.markdown(
                                f"""
                                <div style="padding: 20px; 
                                border-radius: 5px; border: 1px solid #008296; border-left: 4px solid #008296; 
                                margin-top: 20px;">
                                {message["final_answer"]}
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )


    # Create fixed input container at the bottom
    st.markdown('<div class="fixed-input">', unsafe_allow_html=True)
    prompt = st.chat_input(
        "Waiting for response..." if st.session_state.streaming else "What would you like to know?",
        disabled=st.session_state.streaming,
        #key=f"chat_input_{st.session_state.input_key}"
        key="chat_input"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Handle the chat input logic
    if prompt and not st.session_state.streaming:
        st.session_state.streaming = True
        st.session_state.current_prompt = prompt  # Save prompt to session state
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()  # Force refresh to show disabled state
        
    if st.session_state.get("current_prompt") and st.session_state.streaming:
        prompt = st.session_state.current_prompt
        del st.session_state.current_prompt  # Clear saved prompt

        # Add assistant response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            current_response = []
            
            try:
                # Send initial mutation
                session_id = send_mutation(prompt, st.session_state.auth_token)
                logging.info(f"Subscription started for session {session_id}")
                # Start subscription
                ws_url = get_ws_url(st.session_state.auth_token)
                completion_event = start_subscription_thread(
                    ws_url, 
                    session_id,
                    st.session_state.auth_token
                )
                
                # Process responses from queue
                while not completion_event.is_set() or not st.session_state.response_queue.empty():
                    try:
                        if not st.session_state.error_queue.empty():
                            error_msg = st.session_state.error_queue.get_nowait()
                            st.error(f"Error: {error_msg}")
                            break

                        response = st.session_state.response_queue.get_nowait()
                        logging.info(f"Received response with status {response.get("status")}")
                        if response.get("status") == "STREAMING":
                            new_content = response.get('content', '')
                            if new_content not in current_response:
                                current_response.append(new_content)
                            with response_placeholder.container():
                                st.info("Processing...")
                                format_messages(current_response)
                        elif response.get("status") == "COMPLETED":
                            final_answer = json.loads(response.get('content', "")).get("Result", "")
                            final_content = '\n\n'.join(current_response)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": final_content,
                                "final_answer": final_answer
                                })
                            st.session_state.streaming = False
                            st.rerun()
                            break
                        elif response.get("status") == "ERROR":
                            st.error("Error occurred during processing.")
                            st.session_state.streaming = False
                            st.rerun()
                            break
                    except Empty:
                        time.sleep(0.1) # to add pause between queue polling
                        continue
                    
            except Exception as e:
                logging.error(f"Error in chat interface: {e}")
                st.error(f"Error: {e}")
                st.session_state.streaming = False
            finally:
                if st.session_state.streaming:
                    st.session_state.streaming = False

def format_messages(current_response: list[str]):
    for message in current_response:
        content_dict = json.loads(message)
        if "finalResponse" in content_dict.get("Observation", {}):  # final response is displayed separately
                continue
        else:
            st.markdown(message)  # ADD YOUR FORMATTING FOR TRACE MESSAGES HERE



def main():
    st.set_page_config(
        page_title="Amazon Bedrock Agent Chat",
        page_icon="🤖",
        layout="wide"
    )
    
    custom_css()
    initialize_session_state()

    handle_callback()
    if not st.session_state.is_authenticated:
        st.markdown(
            f'<h2>👋 Welcome to Amazon Bedrock Agent!</h2>',
            unsafe_allow_html=True
        )
        
        if st.button("Sign In"):
            login_url = get_login_url()
            st.markdown(f'<meta http-equiv="refresh" content="0;url={login_url}">', unsafe_allow_html=True)
    else:
        chat_interface()

if __name__ == "__main__":
    main()
