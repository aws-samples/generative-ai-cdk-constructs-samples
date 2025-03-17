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
import json
from constructs import Construct
from aws_cdk import (
    Aws,
    aws_appsync as appsync,
    aws_lambda as lambda_,
    aws_cognito as cognito,
    aws_iam as iam,
    CfnOutput,
    Duration,
    Stack,
    aws_secretsmanager as secretsmanager,
    RemovalPolicy
)
from aws_cdk import aws_appsync as appsync
from cdk_nag import NagSuppressions

from infra.graphql_api_construct.lambda_layers_construct import GraphQLLambdaLayers

class ApiAuthConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str,
                 agent_id: str,
                 agent_alias_id: str,
                 region: str, account: str, 
                 redirect_uri: str,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        NagSuppressions.add_stack_suppressions(
            Stack.of(self),
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Built-in CDK Lambda for log retention requires managed policy",
                    "applies_to": ["*"],
                    "resource_path": "*LogRetention*/ServiceRole/Resource"
                }
            ]
        )

        # Create Cognito User Pool
        self.user_pool = cognito.UserPool(
            self, f"{construct_id}-userpool",
            user_pool_name=f"{construct_id}-userpool",
            #self_sign_up_enabled=True,
            #sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            removal_policy=RemovalPolicy.DESTROY,
            mfa=cognito.Mfa.REQUIRED,
            mfa_second_factor={
                "sms": False,
                "otp": True
            },
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY
        )

        NagSuppressions.add_resource_suppressions(
            self.user_pool,
            [
                {
                    "id": "AwsSolutions-COG3",
                    "reason": "Using Essentials tier which does not support advanced security features"
                }
            ]
        )

        # Create Cognito Client
        self.client = self.user_pool.add_client("app-client",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(  
                user_password=True,
                user_srp=True
            ),
            supported_identity_providers=[cognito.UserPoolClientIdentityProvider.COGNITO], 
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True
                ),
                scopes=[cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE,
                    cognito.OAuthScope.COGNITO_ADMIN],
                callback_urls=[redirect_uri],
                logout_urls=[redirect_uri]
            ),
        )

        # Add domain prefix
        self.domain = self.user_pool.add_domain("domain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"{construct_id.lower()}-{Aws.ACCOUNT_ID}-login"
            )
        )

        appsync_log_role = iam.Role(
            self, 'ApiLogsRole',
            assumed_by=iam.ServicePrincipal('appsync.amazonaws.com'),
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
                                f'arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/appsync/apis/{Stack.of(self).stack_name}-*',
                                f'arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/appsync/apis/{Stack.of(self).stack_name}-*:log-stream:*'
                            ]
                        )
                    ]
                )
            }
        )

        # Add suppression for CloudWatch Logs permissions
        NagSuppressions.add_resource_suppressions(
            appsync_log_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CloudWatch Logs APIs require * permissions as they don't support resource-level permissions",
                    "appliesTo": [
                        f'Resource::arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/appsync/apis/{Stack.of(self).stack_name}-*',
                        f'Resource::arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/appsync/apis/{Stack.of(self).stack_name}-*:log-stream:*'
                    ]
                }
            ],
            True
        )


        # Create the AppSync API
        self.api = appsync.GraphqlApi(
            self, 
            f"{construct_id}-graphqlapi",
            name=f"{construct_id}-graphqlapi",
            schema=appsync.SchemaFile.from_asset(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "schema",
                    "schema.graphql")
                ),
            authorization_config=appsync.AuthorizationConfig(
                default_authorization=appsync.AuthorizationMode(
                    authorization_type=appsync.AuthorizationType.USER_POOL,
                    user_pool_config=appsync.UserPoolConfig(
                        user_pool=self.user_pool
                    )
                ),
                additional_authorization_modes=[
                    appsync.AuthorizationMode(
                        authorization_type=appsync.AuthorizationType.IAM
                    )
                ]
            ),
            log_config=appsync.LogConfig(
                field_log_level=appsync.FieldLogLevel.ALL,  
                exclude_verbose_content=False,
                role=appsync_log_role
            ),
            xray_enabled=True
        )
        
        # Output important values
        CfnOutput(self, "COGNITO_USER_POOL_ID",
            value=self.user_pool.user_pool_id, export_name=f"{construct_id}-COGNITO-USER-POOL-ID"
        )
        
        CfnOutput(self, "COGNITO_APP_CLIENT_ID",
            value=self.client.user_pool_client_id, export_name=f"{construct_id}-COGNITO-APP-CLIENT-ID"
        )
        
        CfnOutput(self, "COGNITO_DOMAIN_PREFIX",
            value=self.domain.domain_name, export_name=f"{construct_id}-COGNITO-DOMAIN-PREFIX"
        )

        CfnOutput(self, "APPSYNC_API_ENDPOINT",
                  value=self.api.graphql_url, export_name=f"{construct_id}-APPSYNC-API-ENDPOINT"
        )

        CfnOutput(self, "AWS_REGION", value=region, export_name=f"{construct_id}-AWS-REGION")

        # Create lambda layers
        self.layers = GraphQLLambdaLayers(self, construct_id)

        stream_handler_role = iam.Role(
            self,
            "StreamHandlerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "CloudWatchLogsPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[
                                f"arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/{Stack.of(self).stack_name}-*",
                                f"arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/{Stack.of(self).stack_name}-*:log-stream:*"
                            ]
                        )
                    ]
                )
            }
        )

        NagSuppressions.add_resource_suppressions(
            stream_handler_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CloudWatch Logs APIs require * permissions as they don't support resource-level permissions",
                    "appliesTo": [
                        f'Resource::arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/{Stack.of(self).stack_name}-*',
                        f'Resource::arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/{Stack.of(self).stack_name}-*:log-stream:*'
                    ]
                }
            ],
            True
        )

        self.bedrock_agent_secrets = secretsmanager.Secret(
            self, "BedrockAgentSecrets",
            secret_name="bedrock-agent-secrets",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({
                    "AGENT_ID": agent_id,
                    "AGENT_ALIAS_ID": agent_alias_id,
                    "APPSYNC_API_ID": self.api.api_id,
                    "APPSYNC_ENDPOINT": self.api.graphql_url,
                    "AWS_REGION": Stack.of(self).region
                }),
                generate_string_key="dummy"  # Required but not used
            ),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        NagSuppressions.add_resource_suppressions(
            self.bedrock_agent_secrets,
            [
                {
                    "id": "AwsSolutions-SMG4",
                    "reason": "These secrets contain static infrastructure values that don't require rotation"
                }
            ]
        )

        self.stream_handler = lambda_.Function(
            self, "StreamHandler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="stream_handler.index.lambda_handler",
            code=lambda_.Code.from_asset("assets/lambda/functions"),
            layers=[self.layers.aws_lambda_powertools_layer, self.layers.requests_auth_layer],
            environment={
                "AGENT_SECRET_NAME": self.bedrock_agent_secrets.secret_name
            },
            timeout=Duration.minutes(15),
            role=stream_handler_role,
            tracing=lambda_.Tracing.ACTIVE
        )

        self.bedrock_agent_secrets.grant_read(self.stream_handler)

        # Add permissions for AppSync
        self.stream_handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=["appsync:GraphQL"],
                resources=[
                    f"{self.api.arn}/types/Mutation/fields/publishAgentUpdate"
                ]
            )
        )

        ask_agent_handler_role = iam.Role(
            self,
            "AskAgentHandlerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "CloudWatchLogsPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[
                                f"arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/{Stack.of(self).stack_name}-*",
                                f"arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/{Stack.of(self).stack_name}-*:log-stream:*"
                            ]
                        )
                    ]
                ),
                "InvokeStreamHandlerPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["lambda:InvokeFunction"],
                            resources=[self.stream_handler.function_arn]  # Specific function ARN
                        )
                    ]
                )
            }
        )

        # Add suppressions for the log group wildcards
        NagSuppressions.add_resource_suppressions(
            ask_agent_handler_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CloudWatch Logs APIs require * permissions as they don't support resource-level permissions",
                    "appliesTo": [
                        f'Resource::arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/{Stack.of(self).stack_name}-*',
                        f'Resource::arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/{Stack.of(self).stack_name}-*:log-stream:*'
                    ]
                }
            ],
            True
        )

        self.stream_arn_secrets = secretsmanager.Secret(
            self, "StreamHandlerArnSecrets",
            secret_name="stream_arn",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({
                    "STREAM_HANDLER_ARN": self.stream_handler.function_arn,
                }),
                generate_string_key="dummy"  # Required but not used
            ),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        NagSuppressions.add_resource_suppressions(
            self.stream_arn_secrets,
            [
                {
                    "id": "AwsSolutions-SMG4",
                    "reason": "These secrets contain static infrastructure values that don't require rotation"
                }
            ]
        )

        # Create Lambda function for agent interaction
        self.ask_agent_handler = lambda_.Function(
            self, "AskAgentHandler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="agent_handler.index.lambda_handler",
            code=lambda_.Code.from_asset("assets/lambda/functions"),
            layers=[self.layers.aws_lambda_powertools_layer, self.layers.requests_auth_layer],
            environment={
                "STREAM_ARN_SECRET_NAME": self.stream_arn_secrets.secret_name
            },
            timeout=Duration.minutes(1),
            role=ask_agent_handler_role,
            tracing=lambda_.Tracing.ACTIVE
        )

        self.stream_arn_secrets.grant_read(self.ask_agent_handler)

        # Grant permissions to invoke AppSync API
        self.stream_handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=["appsync:GraphQL"],
                resources=[f"{self.api.arn}/types/Mutation/fields/publishAgentUpdate"]
            )
        )

        ask_agent_datasource_role = iam.Role(
            self,
            "AskAgentDataSourceRole",
            assumed_by=iam.ServicePrincipal("appsync.amazonaws.com"),
            inline_policies={
                "InvokeLambdaPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["lambda:InvokeFunction"],
                            resources=[self.ask_agent_handler.function_arn] 
                        )
                    ]
                )
            }
        )

        NagSuppressions.add_stack_suppressions(
            Stack.of(self),
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "AppSync needs to invoke specific Lambda function, ARN is explicitly specified",
                    "applies_to": ["*"],
                    "resource_path": "*AskAgentDataSourceRole/DefaultPolicy/Resource"
                }
            ]
        )

        # Create the datasource
        ask_agent_datasource = appsync.LambdaDataSource(
            self,
            "AskAgentDataSource",
            api=self.api,
            lambda_function=self.ask_agent_handler,
            service_role=ask_agent_datasource_role
        )

        # Create resolver for askAgent mutation
        ask_agent_datasource.create_resolver(
            id="AskAgentResolver",
            type_name="Mutation",
            field_name="askAgent",
            request_mapping_template=appsync.MappingTemplate.from_string('''
            {
                "version": "2018-05-29",
                "operation": "Invoke",
                "payload": {
                    "question": $util.toJson($context.arguments.question),
                    "sessionId": $util.toJson($context.arguments.sessionId)
                }
            }
            '''),
            response_mapping_template=appsync.MappingTemplate.from_string('''
            #if($ctx.error)
                $util.error($ctx.error.message)
            #end
            $util.toJson($ctx.result)
            ''')
        )

        # Add Bedrock permissions
        self.stream_handler.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeAgent",
                    "bedrock-agent-runtime:InvokeAgent"
                ],
                resources=[
                    f"arn:aws:bedrock:{region}:{account}:agent/{agent_id}",
                    f"arn:aws:bedrock:{region}:{account}:agent-alias/{agent_id}/{agent_alias_id}"
                ]
            )
        )

        #Add NONE data source for testing
        none_ds = self.api.add_none_data_source("PublishDS")

        # Add resolver for publishAgentUpdate
        none_ds.create_resolver(
            id="NoneDSResolver",
            type_name="Mutation",
            field_name="publishAgentUpdate",
            request_mapping_template=appsync.MappingTemplate.from_string('''
            {
                "version": "2018-05-29",
                "payload": {
                    "sessionId": $util.toJson($ctx.arguments.sessionId),
                    "content": $util.toJson($ctx.arguments.content),
                    "trace": $util.toJson($ctx.arguments.trace)
                }
            }
            '''),
            response_mapping_template=appsync.MappingTemplate.from_string('''
            #return($ctx.arguments)
            {
                "sessionId": $ctx.arguments.sessionId,
                "content": $ctx.arguments.content,
                "trace": $ctx.arguments.trace
            }
            ''')
        )