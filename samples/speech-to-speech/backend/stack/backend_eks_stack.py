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
    CustomResourceConstruct,
    get_backend_language,
    BackendLanguage
)
from .stack_constructs.eks_fargate_constructs import EKSFargateConstruct


class BackendEKSStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the path to the frontend directory
        # need to npm run build and push the build folder to the frontend directory first
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
            "frontend/dist"
        )
    
        # Get backend language from context
        backend_language = get_backend_language(self.node.root)
    
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
        # Set image name and dockerfile based on backend language
        if backend_language == BackendLanguage.PYTHON:
            docker_image_asset = DockerImageAssetConstruct(
                self,
                "WebSocketPythonImage",
                directory=os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/python_app",
                file="Dockerfile",
                platform=ecr_assets.Platform.LINUX_ARM64
            )
        else:
            docker_image_asset = DockerImageAssetConstruct(
                self,
                "WebSocketJavaImage",
                directory=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                file="Dockerfile",
                platform=ecr_assets.Platform.LINUX_ARM64
            )
        
        #######################
        ### VPC RESOURCES #####
        #######################

        # Create VPC
        vpc = VPCConstruct(
            self,
            "VPC"
        )

        #########################
        ### EKS FARGATE SERVICE #
        #########################

        # Create EKS Fargate cluster and deploy the application
        eks_fargate_service = EKSFargateConstruct(
            self,
            "EKSFargateService",
            vpc=vpc.vpc,
            cognito_user_pool_id=cognito_construct.user_pool.user_pool_id,
            container_image_uri=docker_image_asset.asset.image_uri,
        )
        
        # Add suppressions for EKS internal resources
        NagSuppressions.add_resource_suppressions(
            eks_fargate_service,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="EKS managed resources use AWS managed policies"
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5", 
                    reason="EKS managed resources require wildcard permissions"
                ),
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="EKS managed Lambda functions runtime is controlled by AWS"
                ),
                NagPackSuppression(
                    id="AwsSolutions-SF1",
                    reason="EKS managed Step Functions logging is controlled by AWS"
                ),
                NagPackSuppression(
                    id="AwsSolutions-SF2",
                    reason="EKS managed Step Functions X-Ray tracing is controlled by AWS"
                ),
            ],
            apply_to_children=True
        )
        
        ##########################
        ### CLOUDFRONT RESOURCES #
        ##########################
        
        # Note: For EKS, we need to wait for the LoadBalancer to be created
        # and then update CloudFront. For now, we'll create a placeholder.
        # In production, you would need to either:
        # 1. Use a custom resource to get the NLB DNS after deployment
        # 2. Deploy in two phases
        # 3. Use an Ingress controller with a known domain
        
        # For this implementation, we'll output instructions for manual configuration
        
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
            "EKSClusterName",
            value=eks_fargate_service.cluster.cluster_name,
            description="EKS Cluster Name",
        )
        
        CfnOutput(
            self,
            "EKSClusterEndpoint",
            value=eks_fargate_service.cluster.cluster_endpoint,
            description="EKS Cluster Endpoint",
        )
        
        CfnOutput(
            self,
            "KubectlCommand",
            value=f"aws eks update-kubeconfig --name {eks_fargate_service.cluster.cluster_name} --region {self.region}",
            description="Command to configure kubectl",
        )
        
        CfnOutput(
            self,
            "GetLoadBalancerCommand",
            value=f"kubectl get service websocket-service -n websocket-app -o jsonpath='{{.status.loadBalancer.ingress[0].hostname}}'",
            description="Command to get the NLB DNS name after deployment",
        )
        
        CfnOutput(
            self,
            "DeploymentInstructions",
            value=(
                "After deployment completes:\n"
                "1. Configure kubectl using the KubectlCommand output\n"
                "2. Wait for the LoadBalancer to be provisioned (3-5 minutes)\n"
                "3. Get the NLB DNS using the GetLoadBalancerCommand output\n"
                "4. The WebSocket endpoint will be available at: ws://<NLB_DNS>/"
            ),
            description="Post-deployment instructions",
        )
        
        ##########################
        ## CDK NAG SUPPRESSIONS ##
        ##########################
        
        # Stack-level suppressions that will apply to all resources including EKS internal ones
        NagSuppressions.add_stack_suppressions(
            self,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="AWS managed policies are used for demo purposes and EKS internal resources",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard permissions are used for demo purposes and required by EKS internal resources",
                ),
                NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason="Server access logs are not required for this demo application",
                ),
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Lambda runtime versions are managed by CDK for internal resources",
                ),
                NagPackSuppression(
                    id="AwsSolutions-EKS1",
                    reason="EKS cluster endpoint is public for demo purposes",
                ),
                NagPackSuppression(
                    id="AwsSolutions-EKS2",
                    reason="EKS cluster logging is enabled for all log types",
                ),
                NagPackSuppression(
                    id="AwsSolutions-SF1",
                    reason="Step Functions logging is managed by CDK for EKS cluster provisioning",
                ),
                NagPackSuppression(
                    id="AwsSolutions-SF2",
                    reason="Step Functions X-Ray tracing is managed by CDK for EKS cluster provisioning",
                ),
            ],
        )
