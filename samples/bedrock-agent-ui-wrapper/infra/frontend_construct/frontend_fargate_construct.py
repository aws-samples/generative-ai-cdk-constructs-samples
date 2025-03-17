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

from constructs import Construct
from datetime import datetime
from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_s3 as s3,
    aws_lambda as lambda_,
    RemovalPolicy,
    aws_secretsmanager as secretsmanager,
    aws_cloudfront,
    SecretValue,
    Stack,
    Duration,
    aws_logs as logs
)
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk.aws_cloudfront_origins import LoadBalancerV2Origin
from aws_cdk.aws_cloudfront import FunctionEventType

from cdk_nag import NagSuppressions


class FrontendFargateConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, api_auth_construct, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # **************** Create VPC **************** 
        vpc = ec2.Vpc(self, f"{construct_id}-vpc",
            max_azs=2,
            nat_gateways=1,
            enable_dns_hostnames=True,
            enable_dns_support=True
        )

        # Create a log group for VPC Flow Logs
        flow_log_group = logs.LogGroup(
            self,
            f"{construct_id}-flow-logs",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Add Flow Logs to VPC
        vpc.add_flow_log(
            id="FlowLog",
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(
                log_group=flow_log_group,
                iam_role=iam.Role(
                    self,
                    f"{construct_id}-flow-log-role",
                    assumed_by=iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"),
                    description="Role for VPC Flow Logs"
                )
            ),
            traffic_type=ec2.FlowLogTrafficType.ALL,
            max_aggregation_interval=ec2.FlowLogMaxAggregationInterval.ONE_MINUTE
        )

        #  ****************  Create security groups  **************** 
        cloudfront_prefix_lists = { # Ref: https://dev.to/kaspersfranz/limit-traffic-to-only-cloudfront-traffic-in-aws-alb-3c6
            'us-east-1': 'pl-3b927c52',
            'us-east-2': 'pl-b6a144df',
            'us-west-1': 'pl-4ea04527',
            'us-west-2': 'pl-82a045eb',
            'af-south-1': 'pl-c0aa4fa9',
            'ap-east-1': 'pl-14b2577d',
            'ap-south-1': 'pl-9aa247f3',
            'ap-northeast-2': 'pl-22a6434b',
            'ap-southeast-1': 'pl-31a34658',
            'ap-southeast-2': 'pl-b8a742d1',
            'ap-northeast-1': 'pl-58a04531',
            'ca-central-1': 'pl-38a64351',
            'eu-central-1': 'pl-a3a144ca',
            'eu-west-1': 'pl-4fa04526',
            'eu-west-2': 'pl-93a247fa',
            'eu-south-1': 'pl-1bbc5972',
            'eu-west-3': 'pl-75b1541c',
            'eu-north-1': 'pl-fab65393',
            'me-south-1': 'pl-17b2577e',
            'sa-east-1': 'pl-5da64334'
        }

        # ALB Security Group
        self.alb_security_group = ec2.SecurityGroup(
            self, 'LoadBalancerSG',
            vpc=vpc,
            allow_all_outbound=True,
            description="Allow inbound from VPC for ECS Fargate Service",
            security_group_name=f'{construct_id}-alb-sg'
        )

        # fargate service SG
        self.fargate_security_group = ec2.SecurityGroup(
            self, 'ECSFargateServiceSG',
            vpc=vpc,
            allow_all_outbound=True,
            description="Allow inbound from VPC for ECS Fargate Service",
            security_group_name=f'{construct_id}-ecs-service-sg'
        )

        region = Stack.of(self).region
        cloudfront_prefix_list_id = cloudfront_prefix_lists.get(region) # get cloudfront IP prefix using region name
        if not cloudfront_prefix_list_id:
            raise ValueError(f"No CloudFront prefix list ID found for region {region}")
        
        self.alb_security_group.add_ingress_rule(
            peer=ec2.Peer.prefix_list(cloudfront_prefix_list_id), # Add ingress rule for HTTP traffic from CloudFront ONLY
            connection=ec2.Port.tcp(80),
            description='HTTP from CloudFront'
        )

        self.alb_security_group.add_ingress_rule(
            peer=self.alb_security_group,
            connection=ec2.Port.all_traffic(),
            description="Within Security Group",
        )

        self.fargate_security_group.add_ingress_rule(
            peer=self.fargate_security_group,
            connection=ec2.Port.all_traffic(),
            description="Within Security Group",
        )

        self.fargate_security_group.add_ingress_rule(
            peer=self.alb_security_group,
            connection=ec2.Port.tcp(8501),
            description='app-server'
        )

        #  **************** Create Load Balancer  **************** 
        server_access_logs_bucket = s3.Bucket(
            self,
            f"{construct_id}-server-access-logs",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldLogs",
                    expiration=Duration.days(365),  # Delete after 1 year
                    enabled=True
            )]
        )

        alb_logs_bucket = s3.Bucket(
            self,
            f"{construct_id}-alb-logs",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=s3.ObjectOwnership.OBJECT_WRITER,
            server_access_logs_bucket=server_access_logs_bucket,
            server_access_logs_prefix=f"s3-logs/{construct_id}-alb-logs/",
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldLogs",
                    expiration=Duration.days(365),  # Delete after 1 year
                    enabled=True
            )]
        )

        alb_logs_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontLogDelivery",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("delivery.logs.amazonaws.com")],
                actions=["s3:PutObject"],
                resources=[f"{alb_logs_bucket.bucket_arn}/*"],
                conditions={
                    "StringEquals": {
                        "aws:SourceAccount": Stack.of(self).account,
                        "s3:x-amz-acl": "bucket-owner-full-control"
                    }
                }
            )
        )

        self.load_balancer = elbv2.ApplicationLoadBalancer(
            self, "LoadBalancer",
            vpc=vpc,
            internet_facing=True,
            security_group=self.alb_security_group,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        self.load_balancer.log_access_logs(
            bucket=alb_logs_bucket,
            prefix=f"alb-logs/{construct_id}"  # Optional prefix for organization
        )

        #  ****************  Create Cloudfront Distribution  **************** 
        self.custom_header_name = f"{construct_id}-cf-header"
        self.custom_header_value = f"{construct_id.lower()}"

        origin = LoadBalancerV2Origin(
            load_balancer=self.load_balancer,
            custom_headers={self.custom_header_name: self.custom_header_value},
            #origin_shield_enabled=False,
            http_port=80,
            protocol_policy=aws_cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        )

        auth_function = aws_cloudfront.Function(
            self,
            "RedirectFunction",
            code=aws_cloudfront.FunctionCode.from_inline(f"""
            function handler(event) {{
                var request = event.request;
                var uri = request.uri;

                // If this is the callback endpoint with a code, redirect to root
                if (uri.startsWith('/oauth2/idpresponse') && request.querystring.code) {{
                    return {{
                        statusCode: 302,
                        statusDescription: 'Found',
                        headers: {{
                            'location': {{ 
                                value: '/?code=' + request.querystring.code.value
                            }},
                            'cache-control': {{
                                value: 'no-cache, no-store, must-revalidate'
                            }}
                        }}
                    }};
                }}

                // If the request is to '/' and has a code, allow it to pass through
                if (uri === '/' && request.querystring.code) {{
                    return request;
                }}

                // Allow specific resource paths to pass through regardless of query parameters
                var allowed_paths = [
                    '/static/',
                    '/_stcore/',
                    '/favicon.ico',
                    '/robots.txt'
                    // Add more paths as needed
                ];

                for (var i = 0; i < allowed_paths.length; i++) {{
                    if (uri.startsWith(allowed_paths[i])) {{
                        return request;
                    }}
                }}

                // If no code, redirect to Cognito
                if (!uri.startsWith('/oauth2/')) {{
                    var cognitoUrl = 'https://{api_auth_construct.domain.domain_name}.auth.{region}.amazoncognito.com/oauth2/authorize';
                    cognitoUrl += '?client_id={api_auth_construct.client.user_pool_client_id}';
                    cognitoUrl += '&response_type=code';
                    cognitoUrl += '&scope=openid+profile+email';
                    cognitoUrl += '&redirect_uri=https://' + request.headers.host.value + '/oauth2/idpresponse';

                    return {{
                        statusCode: 302,
                        statusDescription: 'Found',
                        headers: {{
                            'location': {{ value: cognitoUrl }},
                            'cache-control': {{ value: 'no-cache, no-store, must-revalidate' }}
                        }}
                    }};
                }}

                return request;
            }}
            """)
        )


        cloudfront_distribution = aws_cloudfront.Distribution(
            self,
            f"{construct_id}-cf-dist",
            comment="Cloudfront distribution",
            default_behavior=aws_cloudfront.BehaviorOptions(
                origin=origin,
                viewer_protocol_policy=aws_cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=aws_cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=aws_cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=aws_cloudfront.OriginRequestPolicy.ALL_VIEWER,
                function_associations=[
                    aws_cloudfront.FunctionAssociation(
                        function=auth_function,
                        event_type=FunctionEventType.VIEWER_REQUEST
                    )
                ]

            ),
            enable_logging=True,
            log_bucket=alb_logs_bucket,
            log_file_prefix=f"distributions/{construct_id}-cf-dist",
            log_includes_cookies=True
        )

        NagSuppressions.add_resource_suppressions(
            cloudfront_distribution,
            suppressions=[
                {
                    "id": "AwsSolutions-CFR4",
                    "reason": "This asset doesn't require a TLS certificate to be provided, for each PoC it will be discussed with the customer how they provide a certificate."
                },
                {
                    "id": "AwsSolutions-CFR5",
                    "reason": "This asset doesn't require a TLS certificate to be provided, for each PoC it will be discussed with the customer how they provide a certificate"
                }
            ]
        )


        self.app_url = f'https://{cloudfront_distribution.domain_name}'

        #   **************** create ECS cluster   **************** 
        cluster = ecs.Cluster(
            self, 
            f"{construct_id}-cluster",
            vpc=vpc,
            container_insights=True,
            enable_fargate_capacity_providers=True,
        )

        #   **************** Create Task Definition   **************** 
        task_role_policy_doc = iam.PolicyDocument()
        task_role_policy_doc.add_statements(iam.PolicyStatement(**{
        "effect": iam.Effect.ALLOW,
        "resources": ["*"],
        "actions": [
            "ecr:GetAuthorizationToken",
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret"
        ]
        }))

        task_role = iam.Role(self, "ECSTaskRole",
        role_name=f'ECSTaskRole-{construct_id}',
        assumed_by=iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
        inline_policies={
            'ecs_task_role_policy': task_role_policy_doc
        },
        managed_policies=[
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
        ]
        )

        task_definition = ecs.FargateTaskDefinition(self, "AppServer",
        task_role=task_role,
        cpu=1 * 1024,
        memory_limit_mib=2 * 1024
        )

        appsync_secret = secretsmanager.Secret(
            self, 
            f"{construct_id}-appsync-endpoint",
            secret_string_value=SecretValue.unsafe_plain_text(api_auth_construct.api.graphql_url),
            removal_policy=RemovalPolicy.DESTROY
        )

        cognito_client_secret = secretsmanager.Secret(
            self,
            f"{construct_id}-cognito-appclient",
            secret_string_value=SecretValue.unsafe_plain_text(api_auth_construct.client.user_pool_client_id),
            removal_policy=RemovalPolicy.DESTROY
        )

        cognito_domain_secret = secretsmanager.Secret(
            self,
            f"{construct_id}-cognito-domain",
            secret_string_value=SecretValue.unsafe_plain_text(api_auth_construct.domain.domain_name),
            removal_policy=RemovalPolicy.DESTROY
        )

        region_secret = secretsmanager.Secret(
            self,
            f"{construct_id}-region",
            secret_string_value=SecretValue.unsafe_plain_text(region),
            removal_policy=RemovalPolicy.DESTROY
        )

        redirect_uri_secret = secretsmanager.Secret(
            self,
            f"{construct_id}-redirect-uri",
            secret_string_value=SecretValue.unsafe_plain_text(f"{self.app_url}/oauth2/idpresponse"),
            removal_policy=RemovalPolicy.DESTROY
        )

        logout_uri_secret = secretsmanager.Secret(
            self,
            f"{construct_id}-logout-uri",
            secret_string_value=SecretValue.unsafe_plain_text(f"{self.app_url}"),
            removal_policy=RemovalPolicy.DESTROY
        )

        NagSuppressions.add_resource_suppressions(
            [
                appsync_secret,
                cognito_client_secret,
                cognito_domain_secret,
                region_secret,
                redirect_uri_secret,
                logout_uri_secret
            ],
            [
                {
                    "id": "AwsSolutions-SMG4",
                    "reason": "These secrets contain static infrastructure values that don't require rotation"
                }
            ]
        )

        container = task_definition.add_container(
            "app",
            image=ecs.ContainerImage.from_asset(
                directory="streamlit_app",
                file="Dockerfile"
            ),
            port_mappings=[ecs.PortMapping(container_port=8501, protocol=ecs.Protocol.TCP)],
            secrets={
                "APPSYNC-API-ENDPOINT": ecs.Secret.from_secrets_manager(secret=appsync_secret),
                "COGNITO-APP-CLIENT-ID": ecs.Secret.from_secrets_manager(secret=cognito_client_secret),
                "COGNITO-DOMAIN-PREFIX": ecs.Secret.from_secrets_manager(secret=cognito_domain_secret),
                "AWS-REGION": ecs.Secret.from_secrets_manager(secret=region_secret),
                "REDIRECT_URI": ecs.Secret.from_secrets_manager(secret=redirect_uri_secret),
                "LOGOUT_URI": ecs.Secret.from_secrets_manager(secret=logout_uri_secret)
            },
            logging=ecs.LogDriver.aws_logs(
                stream_prefix=f"{construct_id}-container"
            )
        )

        #   **************** Create Fargate Service  **************** 
        fargate_service = ecs.FargateService(
            self,
            "app-alb-service",
            cluster=cluster,
            task_definition=task_definition,
            service_name=f"{construct_id}-stl-front",
            health_check_grace_period=Duration.seconds(120),  # TODO: is it necessary?
            security_groups=[self.fargate_security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )

        http_listener = self.load_balancer.add_listener(
            f"{construct_id}-http-listener",
            port=80,
            open=False,
            default_action=elbv2.ListenerAction.fixed_response(
                status_code=403,
                content_type="text/plain",
                message_body="Access denied",
            )
        )

        http_listener.add_action(
            f"{construct_id}-tg",
            conditions=[
                elbv2.ListenerCondition.http_header(
                    self.custom_header_name, [self.custom_header_value]
                )
            ],
            priority=1,
            action=elbv2.ListenerAction.forward(
                target_groups=[
                    elbv2.ApplicationTargetGroup(  # Modify this target group configuration
                        self,
                        f"{construct_id}-action-tg",
                        vpc=vpc,
                        port=8501,
                        protocol=elbv2.ApplicationProtocol.HTTP,
                        targets=[fargate_service],
                        target_group_name=f"{construct_id}-action-tg",
                        health_check={  # Add this health check configuration
                            'path': '/_stcore/health',
                            'port': '8501',
                            'protocol': elbv2.Protocol.HTTP,
                            'interval': Duration.seconds(30),
                            'timeout': Duration.seconds(5),
                            'healthy_threshold_count': 2,
                            'unhealthy_threshold_count': 5,
                        }
                    )
                ]
            )
        )
