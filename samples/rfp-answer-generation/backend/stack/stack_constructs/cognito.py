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
    aws_cognito as cognito,
    aws_iam as iam,
    CfnOutput,
    Stack,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


class CognitoConstruct(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        region: str,
    ):
        super().__init__(scope, construct_id)

        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
        )
        self.user_pool.node.default_child.user_pool_add_ons = (
            cognito.CfnUserPool.UserPoolAddOnsProperty(
                advanced_security_mode="ENFORCED",
            )
        )
        NagSuppressions.add_resource_suppressions(
            construct=self.user_pool,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-COG2",
                    reason="MFA not required for Cognito during prototype engagement",
                ),
            ],
        )
        CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            export_name=f"{Stack.of(self).stack_name}{construct_id}UserPoolId",
        )

        self.user_pool_client = cognito.UserPoolClient(
            self,
            "UserPoolClient",
            user_pool=self.user_pool,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True,
                custom=True,
            ),
        )
        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            export_name=f"{Stack.of(self).stack_name}{construct_id}UserPoolClientId",
        )

        self.identity_pool = cognito.CfnIdentityPool(
            self,
            "IdentityPool",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=self.user_pool_client.user_pool_client_id,
                    provider_name=self.user_pool.user_pool_provider_name,
                )
            ],
        )
        CfnOutput(
            self,
            "IdentityPoolId",
            value=self.identity_pool.ref,
            export_name=f"{Stack.of(self).stack_name}{construct_id}IdentityPoolId",
        )

        self.auth_user_role = iam.Role(
            self,
            "AuthenticatedUserRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.identity_pool.ref,
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated",
                    },
                },
                "sts:AssumeRoleWithWebIdentity",
            ),
        )

        self.unauth_user_role = iam.Role(
            self,
            "UnauthenticatedUserRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.identity_pool.ref,
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "unauthenticated",
                    },
                },
            ),
        )

        self.identity_pool_role_attachment = cognito.CfnIdentityPoolRoleAttachment(
            self,
            "IdentityPoolRoleAttachment",
            identity_pool_id=self.identity_pool.ref,
            roles={
                "authenticated": self.auth_user_role.role_arn,
                "unauthenticated": self.unauth_user_role.role_arn,
            },
            role_mappings={
                "mapping": cognito.CfnIdentityPoolRoleAttachment.RoleMappingProperty(
                    type="Token",
                    ambiguous_role_resolution="AuthenticatedRole",
                    identity_provider="cognito-idp.{}.amazonaws.com/{}:{}".format(
                        region,
                        self.user_pool.user_pool_id,
                        self.user_pool_client.user_pool_client_id,
                    ),
                )
            },
        )
