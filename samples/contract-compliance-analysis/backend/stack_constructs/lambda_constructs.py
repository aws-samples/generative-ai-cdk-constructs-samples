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
    aws_lambda_python_alpha as lambda_python,
    aws_lambda as lambda_,
    aws_iam as iam,
    Stack
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


class PythonFunctionConstruct(lambda_python.PythonFunction):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            **kwargs,
    ):
        role = iam.Role(
            scope,
            f"{construct_id}ServiceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        super().__init__(
            scope,
            construct_id,
            role=role,
            **kwargs,
        )

        # Get the actual function name after initialization
        function_name = self.function_name

        role.attach_inline_policy(_lambda_basic_policy(scope, construct_id, function_name))


class DockerImageFunctionConstruct(lambda_.DockerImageFunction):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            **kwargs,
    ):
        role = iam.Role(
            scope,
            f"{construct_id}ServiceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        super().__init__(
            scope,
            construct_id,
            role=role,
            **kwargs,
        )

        # Get the actual function name after initialization
        function_name = self.function_name

        role.attach_inline_policy(_lambda_basic_policy(scope, construct_id, function_name))


def _lambda_basic_policy(
        scope: Construct,
        construct_id: str,
        function_name: str
):
    region = Stack.of(scope).region
    account = Stack.of(scope).account

    policy = iam.Policy(
        scope,
        f"{construct_id}LambdaBasicExecPolicy",
        statements=[
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:aws:logs:{region}:{account}:log-group:/aws/lambda/{function_name}",
                    f"arn:aws:logs:{region}:{account}:log-group:/aws/lambda/{function_name}:*"
                ],
            ),
        ],
    )
    NagSuppressions.add_resource_suppressions(
        construct=policy,
        suppressions=[
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                applies_to=[{
                    "regex": "/^Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:log-group:/aws/lambda/.*:\\*$/"
                }],
                reason="Lambda requires wildcard suffix on log group ARN to create and write to log streams within its dedicated log group."
            )
        ],
    )
    return policy


def add_bedrock_marketplace_permissions(role: iam.Role):
    """
    Add AWS Marketplace permissions for Claude models to enable auto-subscription on first invocation.
    
    All Anthropic Claude models are sold through AWS Marketplace and require marketplace subscription.
    This policy allows Lambda to automatically subscribe to Claude models when first invoked,
    restricted to only Claude product IDs and only when called by Bedrock.
    
    Reference: https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-product-ids.html
    """
    role.add_to_policy(iam.PolicyStatement(
        actions=[
            "aws-marketplace:ViewSubscriptions",
            "aws-marketplace:Subscribe",
        ],
        resources=["*"],
        conditions={
            "ForAllValues:StringEquals": {
                # Product IDs from: https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-product-ids.html
                "aws-marketplace:ProductId": [
                    "c468b48a-84df-43a4-8c46-8870630108a7",  # Anthropic Claude
                    "b0eb9475-3a2c-43d1-94d3-56756fd43737",  # Anthropic Claude Instant
                    "prod-6dw3qvchef7zy",  # Anthropic Claude 3 Sonnet
                    "prod-m5ilt4siql27k",  # Anthropic Claude 3.5 Sonnet
                    "prod-cx7ovbu5wex7g",  # Anthropic Claude 3.5 Sonnet v2
                    "prod-4dlfvry4v5hbi",  # Anthropic Claude 3.7 Sonnet
                    "prod-mxcfnwvpd6kb4",  # Anthropic Claude Sonnet 4.5
                    "prod-4pmewlybdftbs",  # Anthropic Claude Sonnet 4
                    "prod-ozonys2hmmpeu",  # Anthropic Claude 3 Haiku
                    "prod-5oba7y7jpji56",  # Anthropic Claude 3.5 Haiku
                    "prod-xdkflymybwmvi",  # Anthropic Claude Haiku 4.5
                    "prod-fm3feywmwerog",  # Anthropic Claude 3 Opus
                    "prod-azycxvnd5mhqi",  # Anthropic Claude Opus 4
                    "prod-w3q2d6rfge4tw",  # Anthropic Claude Opus 4.1
                ]
            },
            "StringEquals": {
                "aws:CalledViaLast": "bedrock.amazonaws.com"
            }
        }
    ))
    
    # Suppress cdk-nag warning for wildcard resource (required by AWS Marketplace API)
    # Must target the DefaultPolicy/Resource that gets auto-created
    from aws_cdk import Stack
    stack = Stack.of(role)
    NagSuppressions.add_resource_suppressions_by_path(
        stack,
        f"{role.node.path}/DefaultPolicy/Resource",
        [
            {
                "id": "AwsSolutions-IAM5",
                "appliesTo": ["Resource::*"],
                "reason": "AWS Marketplace Subscribe/ViewSubscriptions actions do not support resource-level permissions. Access is restricted by ProductId condition to 14 Anthropic Claude models and CalledViaLast condition to Bedrock service only."
            }
        ]
    )

