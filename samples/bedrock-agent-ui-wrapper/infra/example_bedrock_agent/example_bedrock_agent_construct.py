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

from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_lambda as lambda_,
    Duration,
    aws_bedrock as bedrock,
)
from constructs import Construct
from cdk_nag import NagSuppressions
import os
from cdklabs.generative_ai_cdk_constructs import bedrock


class SimpleBedrockAgentConstruct(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        self.agent = bedrock.Agent(
            self,
            f"{id}_example_agent",
            foundation_model=bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V1_0,
            instruction="You are a demo agent for demo purposes. testAction API simply returns your message back as this is an agent used for testing",
            should_prepare_agent=True
        )

        demo_function_role = iam.Role(
            self, 'DemoFunctionRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'CloudWatchLogsPolicy': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                'logs:CreateLogGroup',
                                'logs:CreateLogStream',
                                'logs:PutLogEvents'
                            ],
                            resources=[
                                f'arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/*'
                            ]
                        )
                    ]
                )
            }
        )

        # Add suppression for CloudWatch Logs permissions
        NagSuppressions.add_resource_suppressions(
            demo_function_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CloudWatch Logs APIs require * permissions as they don't support resource-level permissions",
                    "appliesTo": [
                        f'Resource::arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/*'
                    ]
                }
            ],
            True
        )

        # Create a simple Lambda function for the agent
        demo_function = lambda_.Function(
            self, 'DemoFunction',
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler='index.lambda_handler',
            code=lambda_.Code.from_inline('''
def lambda_handler(event, context):
    print("Event Received:", event)
    api_path = event['apiPath']
    response_code = 200
    result = ''
    
    try:
        if api_path == '/testAction':
            result = {'result': _get_parameter(event, 'message')}
        else:
            response_code = 404
            result = "Unrecognized API path: {}".format(api_path)
    except Exception as e:
        response_code = 404
        result = "An error occurred: {}".format(str(e))

    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event['actionGroup'],
            'apiPath': event['apiPath'],
            'httpMethod': event['httpMethod'],
            'httpStatusCode': response_code,
            'responseBody': {'application/json': {'body': result}}
        }
    }
                                          
def _get_parameter(event, name):
    for param in event['requestBody']['content']['application/json']['properties']:
        if param['name'] == name:
            return param['value']
    return None
                                          
'''),
            timeout=Duration.seconds(30),
            role=demo_function_role
        )

        current_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(current_dir, 'agent_schema.json')

        actionGroup = bedrock.AgentActionGroup(
            name="testAction",
            description="testAction API: Use these functions as an example of test action group to answer every user question",
            executor= bedrock.ActionGroupExecutor.fromlambda_function(demo_function),
            enabled=True,
            api_schema=bedrock.ApiSchema.from_local_asset(schema_path),
            )

        self.agent.add_action_group(actionGroup)

        self.agent_alias = bedrock.AgentAlias(self, 'DevelopmentAlias',
            agent=self.agent,
            alias_name='dev_alias',
            description='development agent alias'
        )

    # Properties to access the IDs
    @property
    def agent_id(self) -> str:
        return self.agent.agent_id

    @property
    def agent_alias_id(self) -> str:
        return self.agent_alias.alias_id
