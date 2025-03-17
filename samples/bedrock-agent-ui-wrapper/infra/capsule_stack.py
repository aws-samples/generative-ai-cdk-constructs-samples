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

from typing import Any, Dict
from aws_cdk import (
    aws_route53 as route53,
    aws_route53_targets as targets,
    Stack,
    CfnOutput,
    aws_secretsmanager as secretsmanager,
    SecretValue
)
from constructs import Construct
from cdk_nag import NagSuppressions

from infra.example_bedrock_agent.example_bedrock_agent_construct import SimpleBedrockAgentConstruct
from infra.graphql_api_construct.api_auth_construct import ApiAuthConstruct
from infra.frontend_construct.frontend_fargate_construct import FrontendFargateConstruct

class CapsuleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, config: Dict[str, Any], **kwargs) -> None:
        super().__init__(scope, construct_id, description='UI for Bedrock Agent with streaming support (uksb-7wsqf2qjzq)', **kwargs)

        ## **************** Set Agent Info ****************
        if config["agent_id"]:
            self.agent_id = config["agent_id"]
            self.agent_alias_id = config["agent_alias_id"]
        else:  # if agent info is not provided, then create a testing one
            test_agent = SimpleBedrockAgentConstruct(self, f"{construct_id}-TestAgent")
            self.agent_id = test_agent.agent_id
            self.agent_alias_id = test_agent.agent_alias_id
            

        ## **************** API Layer ****************
        self.local_redirect_uri = "http://localhost:8501"  # default local hosting
        api_auth_construct = ApiAuthConstruct(self, 
                                              construct_id=f"{construct_id}-api",
                                              agent_id=self.agent_id,
                                              agent_alias_id=self.agent_alias_id,
                                              region=self.region,
                                              account=self.account,
                                              redirect_uri=self.local_redirect_uri
                                              )
        

        ## **************** Frontend Layer ****************
        if config["deploy_on_fargate"]:
            # Create frontend construct first (without Fargate service)
            frontend = FrontendFargateConstruct(
                self, 
                construct_id=f"{construct_id}-frontend",
                api_auth_construct=api_auth_construct
            )

            # Output the CloudFront URL
            CfnOutput(
                self, 
                "AppUrl",
                value=frontend.app_url,
                description="URL for the Streamlit application"
            )

            # IMPORTANT! update your cognito app client with this callbacks and wait for 2 minutes for this info to be propagated
            CfnOutput(
                self,
                "CognitoCallbackUrl",
                value=f"{frontend.app_url}/oauth2/idpresponse",
                description="Callback URL for the Cognito app client"
            )
            CfnOutput(
                self,
                "CognitoLogoutUrl",
                value=f"{frontend.app_url}",
                description="Logout URL for the Cognito app client"
            )

