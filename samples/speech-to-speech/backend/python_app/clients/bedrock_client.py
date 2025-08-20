#!/usr/bin/env python3
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
import json
import logging
import warnings
import os
import time
from aws_sdk_bedrock_runtime.client import (
    BedrockRuntimeClient,
    InvokeModelWithBidirectionalStreamOperationInput,
)
from aws_sdk_bedrock_runtime.models import (
    InvokeModelWithBidirectionalStreamInputChunk,
    BidirectionalInputPayloadPart,
)
from aws_sdk_bedrock_runtime.config import (
    Config,
    HTTPAuthSchemeResolver,
    SigV4AuthScheme,
)
from smithy_aws_core.credentials_resolvers.static import (
    StaticCredentialsResolver,
)
from smithy_aws_core.identity import AWSCredentialsIdentity
import boto3
# Configure logging
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings("ignore")


class BedrockInteractClient:
    """Client for interacting with AWS Bedrock Nova Sonic model"""

    def __init__(self, model_id="amazon.nova-sonic-v1:0", region="us-east-1"):
        """Initialize the Bedrock client.

        Args:
            model_id (str): Bedrock model ID to use
            region (str): AWS region
        """
        self.model_id = model_id
        self.region = region
        self.bedrock_client = None
        self.last_credential_check = 0
        self.credential_signal_file = "/tmp/credentials_refreshed"
        logger.info(
            f"Initializing BedrockInteractClient [model_id={model_id}, region={region}]"
        )

    def _check_credential_refresh(self):
        """Check if credentials have been refreshed and recreate client if needed."""
        try:
            if os.path.exists(self.credential_signal_file):
                signal_mtime = os.path.getmtime(self.credential_signal_file)
                
                if signal_mtime > self.last_credential_check:
                    # A real credential refresh from background daemon
                    logger.info("Credential refresh signal detected - recreating Bedrock client")
                    self.bedrock_client = None  # Force recreation
                    self.last_credential_check = signal_mtime
                    # Remove the signal file after processing
                    os.remove(self.credential_signal_file)
        except Exception as e:
            logger.error(f"Error checking credential refresh signal: {e}")

    def initialize_client(self):
        """Initialize the Bedrock client."""
        # Check if credentials were refreshed
        self._check_credential_refresh()
        
        if self.bedrock_client is not None:
            return True
            
        logger.info(f"Initializing Bedrock client for region {self.region}")
        try:
            # Get credentials from boto3 session (handles ECS task role properly)
            session = boto3.Session()
            credentials = session.get_credentials()
            
            # Create AWSCredentialsIdentity object
            aws_credentials = AWSCredentialsIdentity(
                access_key_id=credentials.access_key,
                secret_access_key=credentials.secret_key,
                session_token=credentials.token
            )

            config = Config(
                endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
                region=self.region,
                aws_credentials_identity_resolver=StaticCredentialsResolver(
                    credentials=aws_credentials
                ),
                http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
                http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()},
            )
            self.bedrock_client = BedrockRuntimeClient(config=config)
            logger.info(
                "Bedrock client initialized successfully with StaticCredentialsResolver"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to initialize Bedrock client: {str(e)}", exc_info=True
            )
            return False

    
    async def create_stream(self):
        """Create a bidirectional stream with Bedrock.

        Returns:
            stream: Bedrock bidirectional stream
        """
        logger.info(f"Creating bidirectional stream for model {self.model_id}")
        try:
            if not self.bedrock_client:
                if not self.initialize_client():
                    raise Exception("Failed to initialize Bedrock client")

            stream = await self.bedrock_client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
            )
            logger.info("Stream initialized successfully")
            return stream
        except Exception as e:
            if "ExpiredToken" in str(e):
                current_key = os.environ.get('AWS_ACCESS_KEY_ID', '')
                logger.warning(f"ExpiredToken error occurred with credential ending: ...{current_key[-4:] if len(current_key) >= 4 else 'NONE'}")
            raise

    async def send_event(self, stream, event_data):
        """Send an event to the Bedrock stream.

        Args:
            stream: Bedrock bidirectional stream
            event_data (dict): Event data to send

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            list(event_data.get("event", {}).keys())[
                0
            ] if "event" in event_data else "unknown"

            event_json = json.dumps(event_data)
            event = InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=event_json.encode("utf-8"))
            )
            await stream.input_stream.send(event)
            return True
        except Exception as e:
            logger.error(f"Error sending event: {str(e)}", exc_info=True)
            return False

    async def close_stream(self, stream):
        """Close the Bedrock stream.

        Args:
            stream: Bedrock bidirectional stream

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if stream:
                await stream.input_stream.close()
                logger.info("Stream closed successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Error closing stream: {str(e)}", exc_info=True)
            return False
