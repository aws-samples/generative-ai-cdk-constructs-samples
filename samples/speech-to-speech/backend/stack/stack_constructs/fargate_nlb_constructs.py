from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
    aws_s3 as s3,
    aws_elasticloadbalancingv2 as elbv2,
    Duration,
    RemovalPolicy,
    Stack,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions
from .vpc_construct import VPCConstruct


class FargateNLBConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        container_image: ecs.ContainerImage,
        vpc: ec2.IVpc,
        cognito_user_pool_id: str,
    ):
        super().__init__(scope, construct_id)

        # Create ECS cluster
        self.cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            container_insights=True
        )

        # Create execution role for container runtime permissions
        execution_role = iam.Role(
            self,
            "ExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )

        # Create task role with required permissions
        task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "polly:SynthesizeSpeech",
                    "transcribe:StartStreamTranscription",
                    "transcribe:StartTranscriptionJob",
                    "transcribe:GetTranscriptionJob",
                    "translate:TranslateText",
                    "cloudwatch:PutMetricData",
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                resources=["*"],
            )
        )

        # Create log group
        log_group = logs.LogGroup(
            self,
            "LogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create Fargate task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            memory_limit_mib=512,
            cpu=256,
            task_role=task_role,
            execution_role=execution_role,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )

        # Add CDK Nag suppression for environment variables
        NagSuppressions.add_resource_suppressions(
            task_definition,
            suppressions=[{
                "id": "AwsSolutions-ECS2",
                "reason": "Environment variables are required for the application and are set by custom resource"
            }]
        )

        # Add container to task definition
        container = task_definition.add_container(
            "WebContainer",
            image=container_image,
            port_mappings=[ecs.PortMapping(container_port=8080)],
            logging=ecs.AwsLogDriver(
                log_group=log_group,
                stream_prefix="ecs"
            ),
            environment={
                "COGNITO_USER_POOL_ID": cognito_user_pool_id,
                "AWS_REGION": Stack.of(self).region,
            }
        )

        # Create access logs bucket for NLB with proper bucket policy
        access_logs_bucket = s3.Bucket(
            self,
            "NLBAccessLogsBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Add bucket policy for NLB access logging
        access_logs_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject"],
                principals=[iam.ServicePrincipal("delivery.logs.amazonaws.com")],
                resources=[access_logs_bucket.arn_for_objects("*")],
                conditions={
                    "StringEquals": {
                        "s3:x-amz-acl": "bucket-owner-full-control"
                    }
                }
            )
        )

        # Create security group for Fargate service
        service_security_group = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="Security group for WebSocket service"
        )

        # Allow inbound traffic on container port
        service_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(8080),
            "Allow WebSocket traffic"
        )

        # Add dependency to ensure security group exists before rules are added
        service_security_group.node.add_dependency(vpc)

        # Add CDK Nag suppressions for IAM roles
        NagSuppressions.add_resource_suppressions(
            task_role,
            suppressions=[{
                "id": "AwsSolutions-IAM5",
                "reason": "Task role needs access to various AWS services with dynamic resource names"
            }]
        )

        NagSuppressions.add_resource_suppressions(
            execution_role,
            suppressions=[{
                "id": "AwsSolutions-IAM4",
                "reason": "Using AWS managed policy for ECS task execution role which is required for ECS tasks"
            }]
        )

        # Add CDK Nag suppression for security group
        NagSuppressions.add_resource_suppressions(
            service_security_group,
            suppressions=[{
                "id": "AwsSolutions-EC23",
                "reason": "Security group needs to allow inbound access from NLB which uses dynamic IPs"
            }]
        )

        # Create Fargate service
        self.service = ecs.FargateService(
            self,
            "Service",
            cluster=self.cluster,
            task_definition=task_definition,
            security_groups=[service_security_group],
            desired_count=1,
            min_healthy_percent=100,  # Ensure at least one task is always running
            max_healthy_percent=200,  # Allow running two tasks during deployments
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        )

        # Create Network Load Balancer
        self.load_balancer = elbv2.NetworkLoadBalancer(
            self,
            "WebsocketNLB",
            vpc=vpc,
            internet_facing=True,
            cross_zone_enabled=False,  
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )

        # Enable access logging for NLB
        self.load_balancer.log_access_logs(access_logs_bucket)

        # Add CDK Nag suppression for NLB
        NagSuppressions.add_resource_suppressions(
            self.load_balancer,
            suppressions=[{
                "id": "AwsSolutions-ELB2",
                "reason": "Access logging is enabled for NLB"
            }]
        )

        # Create target group for WebSocket traffic with longer timeouts
        target_group = elbv2.NetworkTargetGroup(
            self,
            "TargetGroup",
            port=8080,  # Internal port that container listens on
            protocol=elbv2.Protocol.TCP,
            target_type=elbv2.TargetType.IP,
            vpc=vpc,
            health_check=elbv2.HealthCheck(
                enabled=True,
                port="8080",
                healthy_threshold_count=2,
                unhealthy_threshold_count=2,
                interval=Duration.seconds(10)
            ),
            deregistration_delay=Duration.seconds(60),  # Increased for graceful connection draining
            preserve_client_ip=True  # Important for WebSocket connections
        )

        # Add target group to service
        self.service.attach_to_network_target_group(target_group)

        # Create main listener with target group
        main_listener = self.load_balancer.add_listener(
            "WebsocketListener",
            port=80,  # External port that clients connect to
            protocol=elbv2.Protocol.TCP,
            default_action=elbv2.NetworkListenerAction.forward([target_group])
        )

        # Add outputs for the load balancer and log group
        CfnOutput(
            self,
            "LoadBalancerDNS",
            value=self.load_balancer.load_balancer_dns_name,
            export_name=f"{Stack.of(self).stack_name}{construct_id}LoadBalancerDNS",
        )

        CfnOutput(
            self,
            "LogGroupName",
            value=log_group.log_group_name,
            description="Log group containing container logs",
            export_name=f"{Stack.of(self).stack_name}{construct_id}LogGroupName",
        )
