import os
from aws_cdk import (
    Stack,
    CfnOutput,
    Aws,
    aws_ecr_assets as ecr_assets,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression
from .stack_constructs import (
    ServerAccessLogsBucketConstruct,
    BucketConstruct,
    CognitoConstruct,
    CloudFrontDistributionConstruct,
    DockerImageAssetConstruct,
    VPCConstruct,
    FargateNLBConstruct,
    CustomResourceConstruct
)

class BackendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the path to the frontend directory
        # need to npm run build and push the build folder to the frontend directory first
        frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend/dist")
    
        #######################
        ### BUCKET RESOURCES ##
        #######################
        
        # Create server access logs bucket
        server_access_logs_bucket = ServerAccessLogsBucketConstruct(
            self, 
            "ServerAccessLogsBucket"
        )
        
        # Create website bucket
        website_bucket = BucketConstruct(
            self, 
            "WebsiteBucket", 
            server_access_logs_bucket
        )
        
        ########################
        ### COGNITO RESOURCES ##
        ########################
        
        # Create Cognito resources
        cognito_construct = CognitoConstruct(
            self, 
            "Cognito", 
            region=Aws.REGION, 
            bucket=website_bucket
        )
        
        #######################
        ### DOCKER RESOURCES ##
        #######################
        
        # Create Docker image asset from the local Dockerfile
        docker_image_asset = DockerImageAssetConstruct(
            self,
            "WebSocketJavaImage",
            directory=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            file="Dockerfile",
            platform=ecr_assets.Platform.LINUX_ARM64
        )

        #######################
        ### FARGATE SERVICE ###
        #######################

        # Create VPC
        vpc = VPCConstruct(
            self,
            "VPC"
        )

        # Create Fargate service with NLB
        fargate_service = FargateNLBConstruct(
            self,
            "FargateService",
            container_image=docker_image_asset.image,
            vpc=vpc.vpc,
            cognito_user_pool_id=cognito_construct.user_pool.user_pool_id
        )
        
        ##########################
        ### CLOUDFRONT RESOURCES #
        ##########################
        
        # Create CloudFront distribution
        cloudfront_distribution = CloudFrontDistributionConstruct(
            self,
            "CloudFrontDistribution",
            website_bucket=website_bucket,
            load_balancer=fargate_service.load_balancer,
            ui_assets_path=frontend_path
        )

        ##########################
        ### CUSTOM RESOURCE ###
        ##########################

        custom_resource = CustomResourceConstruct(
            self,
            "CustomResource",
            cognito_construct=cognito_construct,
            cloudfront_construct=cloudfront_distribution
        )

        #####################
        ### STACK OUTPUTS ###
        #####################

        CfnOutput(
            self,
            "RegionName",
            value=self.region,
            export_name=f"{Stack.of(self).stack_name}RegionName",
        )
        
        CfnOutput(
            self,
            "UserPoolId",
            value=cognito_construct.user_pool.user_pool_id,
            description="Cognito User Pool ID",
        )
        
        CfnOutput(
            self,
            "UserPoolClientId",
            value=cognito_construct.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
        )
        
        CfnOutput(
            self,
            "WebsiteBucketName",
            value=website_bucket.bucket_name,
            description="S3 bucket hosting the static website",
        )
        
        CfnOutput(
            self,
            "CloudFrontDistributionDomainName",
            value=cloudfront_distribution.distribution.distribution_domain_name,
            description="CloudFront distribution domain name",
        )
        
        CfnOutput(
            self,
            "LoadBalancerDNS",
            value=fargate_service.load_balancer.load_balancer_dns_name,
            description="Load balancer DNS name",
        )
        
        ##########################
        ## CDK NAG SUPPRESSIONS ##
        ##########################
        
        NagSuppressions.add_stack_suppressions(
            self,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="AWS managed policies are used for demo purposes",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard permissions are used for demo purposes",
                ),
                NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason="Server access logs are not required for this demo application",
                ),
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="The Lambda runtime version is managed by CDK Bucket Deployment construct",
                ),
            ],
        )
