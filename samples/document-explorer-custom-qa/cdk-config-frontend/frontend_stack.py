"""Frontend stack for hosting Streamlit with ECS and Fargate"""
import platform
from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_ecs_patterns as ecs_patterns,
    aws_ecs as ecs,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_elasticloadbalancingv2 as elbv2
)

from aws_cdk.aws_ecr_assets import DockerImageAsset

class FrontendStack(Stack):
    """Frontend stack for hosting Streamlit with ECS and Fargate"""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        platform_mapping = {
            "x86_64": ecs.CpuArchitecture.X86_64,
            "arm64": ecs.CpuArchitecture.ARM64
        }
        # Get architecture from platform (depending the machine that runs CDK)
        architecture = platform_mapping[platform.machine()] 

        # The code that defines your stack goes here
        # Build Docker image
        imageAsset = DockerImageAsset(self, "FrontendStreamlitImage",
            directory=("../client_app/")
        )

        # create app execute role
        app_execute_role = iam.Role(self, "AppExecuteRole",
                                    assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")                     
        )
        app_execute_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=["*"]
            )  
        )
        # create VPC to host the Ecs app
        vpc = ec2.Vpc(self, "StreamlitECSVpc", 
                      ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
                      subnet_configuration=[
                          ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC),
                          ec2.SubnetConfiguration(name="private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                          ec2.SubnetConfiguration(name="isolated", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                      ]
        )
        ecs_cluster = ecs.Cluster(self, 'StreamlitAppCluster', 
                                  vpc=vpc)
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, "StreamlitAppService",
                        cluster=ecs_cluster,
                        runtime_platform = ecs.RuntimePlatform(
                            operating_system_family=ecs.OperatingSystemFamily.LINUX,
                            cpu_architecture=architecture),
                        task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                            image=ecs.ContainerImage.from_docker_image_asset(imageAsset),
                            container_port=8501,
                            task_role=app_execute_role,
                        ), 
                        task_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                        public_load_balancer=True,
                )

        # Configure health check for ALB
        fargate_service.target_group.configure_health_check(
            path="/healthz"
        )
        cdk.CfnOutput(
            self,
            'StreamlitLoadbalancer',
            value=fargate_service.load_balancer.load_balancer_dns_name)    
        
        # Custom header object
        custom_header_name = "X-Verify-Origin"
        custom_header_value = '-'.join((self.stack_name,"StreamLitCloudFrontDistribution"))
        
        # Create a CloudFront distribution
        cloudfront_distribution = cloudfront.Distribution(self, "StreamLitCloudFrontDistribution",
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.SSL_V3,
            comment="CloudFront distribution for Streamlit frontend application",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.LoadBalancerV2Origin(fargate_service.load_balancer, 
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY, 
                    http_port=80, 
                    origin_path="/", 
                    custom_headers = { custom_header_name : custom_header_value } ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_AND_CLOUDFRONT_2022,
                response_headers_policy=cloudfront.ResponseHeadersPolicy.CORS_ALLOW_ALL_ORIGINS,
                compress=False
            ),
        )

        # Output the CloudFront distribution URL
        cdk.CfnOutput(self, "StreamlitURL", value=f"https://{cloudfront_distribution.domain_name}")
        
        # Create deny rule for ALB
        # Add a rule to deny traffic if custom header is absent
        elbv2.ApplicationListenerRule(self, "MyApplicationListenerRule",
            listener=fargate_service.listener,
            priority=1,
            conditions=[ elbv2.ListenerCondition.http_header( custom_header_name, [ custom_header_value ]) ],
            action = elbv2.ListenerAction.forward([fargate_service.target_group])
        )
        
        
        elbv2.ApplicationListenerRule(self, "RedirectApplicationListenerRule",
            listener=fargate_service.listener,
            priority=5,
            conditions=[ elbv2.ListenerCondition.path_patterns(["*"]) ],
            action = elbv2.ListenerAction.redirect(host=cloudfront_distribution.domain_name, permanent=True,protocol="HTTPS",port="443")
        )
        
