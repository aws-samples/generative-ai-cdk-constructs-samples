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
    aws_s3 as s3,
    Duration,
    RemovalPolicy,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


class ServerAccessLogsBucketConstruct(s3.Bucket):
    """
    A construct that creates an S3 bucket for server access logs.

    This bucket is configured to store server access logs with specific settings
    such as versioning, automatic deletion of objects, and lifecycle rules.

    Parameters:
    - scope (Construct): The scope in which this construct is defined.
    - construct_id (str): The unique identifier for this construct.
    - **kwargs: Additional arguments passed to the S3 bucket constructor.
    """
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            versioned=True,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=True,
                block_public_policy=True,
                ignore_public_acls=True,
                restrict_public_buckets=True,
            ),
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(enabled=True, expiration=Duration.days(90)),
            ],
            cors=[s3.CorsRule(
                allowed_methods=[
                    s3.HttpMethods.GET,
                    s3.HttpMethods.HEAD,
                    s3.HttpMethods.PUT,
                    s3.HttpMethods.POST,
                    s3.HttpMethods.DELETE,
                ],
                allowed_origins=["*"],
                allowed_headers=["*"],
                exposed_headers=[
                    "x-amz-server-side-encryption",
                    "x-amz-request-id",
                    "x-amz-id-2",
                    "ETag",
                    "Content-Type",
                    "Content-Disposition",
                    "Access-Control-Allow-Origin"
                ],
                max_age=3000,
            )],
            **kwargs,
        )
        NagSuppressions.add_resource_suppressions(
            construct=self,
            suppressions=[NagPackSuppression(id="AwsSolutions-S1", reason="Server Access Logs Bucket")],
        )


class BucketConstruct(s3.Bucket):
    """
    A construct that creates an S3 bucket with server access logging enabled.

    This bucket is configured to store objects with specific settings such as
    versioning, automatic deletion of objects, and lifecycle rules. It also
    requires a server access logs bucket to log access requests.

    Parameters:
    - scope (Construct): The scope in which this construct is defined.
    - construct_id (str): The unique identifier for this construct.
    - server_access_logs_bucket (s3.Bucket): The S3 bucket used for logging access requests.
    - **kwargs: Additional arguments passed to the S3 bucket constructor.
    """
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        server_access_logs_bucket: s3.Bucket,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            versioned=True,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=True,
                block_public_policy=True,
                ignore_public_acls=True,
                restrict_public_buckets=True,
            ),
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(enabled=True, expiration=Duration.days(90)),
            ],
            server_access_logs_bucket=server_access_logs_bucket,
            server_access_logs_prefix=f"{construct_id}/",
            cors=[s3.CorsRule(
                allowed_methods=[
                    s3.HttpMethods.GET,
                    s3.HttpMethods.HEAD,
                    s3.HttpMethods.PUT,
                    s3.HttpMethods.POST,
                    s3.HttpMethods.DELETE,
                ],
                allowed_origins=["*"],
                allowed_headers=["*"],
                exposed_headers=[
                    "x-amz-server-side-encryption",
                    "x-amz-request-id",
                    "x-amz-id-2",
                    "ETag",
                    "Content-Type",
                    "Content-Disposition",
                    "Access-Control-Allow-Origin"
                ],
                max_age=3000,
            )],
            **kwargs,
        )
