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
import datetime
import os
from constructs import Construct
from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    custom_resources as custom_resources,
    Aws,
    CustomResource,
)
from . import (
    CognitoConstruct,
    CloudFrontDistributionConstruct,
)

class CustomResourceConstruct(Construct):
    """A CDK construct that manages custom resources for updating frontend configuration.

    This construct creates a Lambda function and custom resource that updates the frontend's
    config.js file with necessary AWS resource information. It handles the following:
    - Creates a Lambda function to update the config.js file in the S3 bucket
    - Sets up a custom resource provider to trigger the Lambda function
    - Configures the Lambda with necessary permissions to access the S3 bucket
    - Updates the config.js file with Cognito and CloudFront configuration

    Args:
        scope (Construct): The scope in which this construct is defined
        construct_id (str): The scoped construct ID
        cognito_construct (CognitoConstruct): The Cognito construct containing user pool and client information
        cloudfront_construct (CloudFrontDistributionConstruct): The CloudFront construct containing distribution and bucket information
        **kwargs: Additional keyword arguments to pass to the parent Construct class

    Dependencies:
        - Requires CognitoConstruct for user pool and client IDs
        - Requires CloudFrontDistributionConstruct for distribution domain and S3 bucket
    """
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cognito_construct: CognitoConstruct,
        cloudfront_construct: CloudFrontDistributionConstruct,

        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        update_config_js_function = lambda_.Function(
            self,
            "UpdateConfigJsFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), "../lambdas", "update_config_js_fn")),
            description="Update the config.js file in the S3 bucket",
            timeout=Duration.minutes(3),
            memory_size=256,
        )

        cloudfront_construct.website_bucket.grant_read_write(update_config_js_function)

        provider = custom_resources.Provider(
            self,
            "UpdateConfigJsProvider",
            on_event_handler=update_config_js_function,
        )

        update_config_js = CustomResource(
            self,
            "UpdateConfigJs",
            service_token=provider.service_token,
            properties={
                "REGION_NAME": Aws.REGION,
                "COGNITO_USER_POOL_ID": cognito_construct.user_pool.user_pool_id,
                "COGNITO_USER_POOL_CLIENT_ID": cognito_construct.user_pool_client.user_pool_client_id,
                "COGNITO_IDENTITY_POOL_ID": cognito_construct.identity_pool.ref,
                "LOAD_BALANCER_DNS": cloudfront_construct.distribution.domain_name,
                "S3_BUCKET_NAME": cloudfront_construct.website_bucket.bucket_name,
                "CHANGE_DETECT": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

        update_config_js.node.add_dependency(cognito_construct)
        update_config_js.node.add_dependency(cloudfront_construct)