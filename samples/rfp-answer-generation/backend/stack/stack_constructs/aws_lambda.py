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
    aws_iam as iam,
    aws_lambda_python_alpha as lambda_python,
    Stack,
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

        role.attach_inline_policy(
            _lambda_basic_policy(scope, construct_id, self.function_name)
        )


def _lambda_basic_policy(
    scope: Construct,
    construct_id: str,
    function_name: str,
):
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
                    f"arn:aws:logs:{Stack.of(scope).region}:{Stack.of(scope).account}:log-group:/aws/lambda/{function_name}",
                    f"arn:aws:logs:{Stack.of(scope).region}:{Stack.of(scope).account}:log-group:/aws/lambda/{function_name}:*",
                ],
            ),
        ],
    )
    NagSuppressions.add_resource_suppressions(
        construct=policy,
        suppressions=[
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason="AWSLambdaBasicExecutionRole CloudWatch log groups",
            )
        ],
    )
    return policy
