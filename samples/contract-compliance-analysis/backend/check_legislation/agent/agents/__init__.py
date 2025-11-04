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

import os
import boto3
from abc import ABC, abstractmethod
from strands.models import BedrockModel
from botocore.config import Config

from schema import CheckLegislationRequest
from model import Clause, LegislationCheck
from util import AppPropertiesManager

APP_TASK_NAME = 'LegislationCheck'
DEFAULT_MODEL_ID = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
 
class AgentArchitecture(ABC):
    """Abstract base class for agent architectures"""

    def __init__(self) -> None:
        # Get model ID from SSM Parameter Store
        properties = AppPropertiesManager()
        model_id = properties.get_parameter(
            "LanguageModelId", task_name=APP_TASK_NAME, default=DEFAULT_MODEL_ID
        )
        print(f"Using model ID: {model_id}")
        
        # Assume cross-account role if specified
        bedrock_xacct_role = os.getenv('BEDROCK_XACCT_ROLE')
        if bedrock_xacct_role:
            sts_client = boto3.client('sts')
            assumed_role = sts_client.assume_role(
                RoleArn=bedrock_xacct_role,
                RoleSessionName='bedrock-agent-session'
            )
            credentials = assumed_role['Credentials']

            boto_session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
        else:
            boto_session = None

        self.bedrock_model = BedrockModel(
            model_id=model_id,
            temperature=0.0,
            boto_session=boto_session,            
            max_tokens=8000,
            boto_client_config=Config(
                connect_timeout=300,
                read_timeout=600,
                retries={
                    "max_attempts": 50,
                    "mode": "adaptive",
                },
            )
        )

    @abstractmethod
    def analyze_clause(self, request: CheckLegislationRequest, clause: Clause) -> LegislationCheck:
        """Analyze clause against legislation"""
        pass
