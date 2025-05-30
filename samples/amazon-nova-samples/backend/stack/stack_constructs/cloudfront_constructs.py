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
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_elasticloadbalancingv2 as elbv2,
    RemovalPolicy,
    aws_iam as iam,
    Duration,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


class CloudFrontDistributionConstruct(Construct):
    """
    A construct that creates a CloudFront distribution for a static website with WebSocket support.
    
    This construct sets up a CloudFront distribution that serves content from an S3 bucket
    and routes WebSocket traffic to an Application Load Balancer.
    
    Parameters:
    - scope (Construct): The scope in which this construct is defined.
    - construct_id (str): The unique identifier for this construct.
    - website_bucket (s3.IBucket): The S3 bucket containing the static website content.
    - load_balancer (elbv2.IApplicationLoadBalancer): The ALB handling WebSocket connections.
    - ui_assets_path (str): Path to the UI assets to deploy to the S3 bucket.
    """
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        website_bucket: s3.IBucket,
        load_balancer: elbv2.IApplicationLoadBalancer,
        ui_assets_path: str,
    ):
        super().__init__(scope, construct_id)
        
        # Public members for external access
        self.distribution_domain_name = None
        self.website_bucket = website_bucket
        
        # Create access logs bucket for CloudFront with ACL enabled
        access_logs_bucket = s3.Bucket(
            self,
            "AccessLogsBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_PREFERRED, 
        )

        origin_access_identity = cloudfront.OriginAccessIdentity(
            self,
            "OriginAccessIdentity"
        )
        website_bucket.grant_read(origin_access_identity)
        
        # Create CloudFront distribution
        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_identity(website_bucket),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                origin_request_policy=cloudfront.OriginRequestPolicy.CORS_S3_ORIGIN,
            ),
            additional_behaviors={
                "/interact-s2s": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        load_balancer.load_balancer_dns_name,
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                        http_port=80,
                        connection_attempts=3,
                        connection_timeout=Duration.seconds(10),
                        read_timeout=Duration.seconds(60),
                        keepalive_timeout=Duration.seconds(60)
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                    response_headers_policy=cloudfront.ResponseHeadersPolicy.CORS_ALLOW_ALL_ORIGINS_WITH_PREFLIGHT,
                ),
            },
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
            ],
            log_bucket=access_logs_bucket,
            log_file_prefix="cloudfront-logs/",
            geo_restriction=cloudfront.GeoRestriction.allowlist("US", "CA"),
            default_root_object="index.html",
        )
        
        # Set the distribution domain name after creation
        self.distribution_domain_name = self.distribution.distribution_domain_name
        
        # Deploy UI assets if path is provided
        self.deployment = s3deploy.BucketDeployment(
            self,
            "DeployWebsite",
            sources=[s3deploy.Source.asset(ui_assets_path)],
            destination_bucket=website_bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],
            memory_limit=1024,  # Increase memory limit to 1GB
            retain_on_delete=False,  # Don't retain files on delete
            prune=True,  # Remove files that don't exist in the source
        )
        self.deployment.handler_role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                "cloudfront:GetInvalidation",
                "cloudfront:CreateInvalidation",
                ],
                resources=["*"],
            )
        )
            
        # Add CDK Nag suppressions
        NagSuppressions.add_resource_suppressions(
            construct=self.distribution,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-CFR1",
                    reason="Geo restrictions are set for demo purposes",
                ),
                NagPackSuppression(
                    id="AwsSolutions-CFR2",
                    reason="WAF integration not required for this prototype",
                ),
                NagPackSuppression(
                    id="AwsSolutions-CFR4",
                    reason="CloudFront distribution has access logging enabled",
                ),
                NagPackSuppression(
                    id="AwsSolutions-CFR5",
                    reason="TLS version is set to HTTPS_ONLY for demo purposes",
                ),
                NagPackSuppression(
                    id="AwsSolutions-CFR7",
                    reason="S3 origin access control is not required for this prototype",
                ),
            ],
        )
