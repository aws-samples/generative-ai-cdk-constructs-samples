from aws_cdk import (
    aws_ec2 as ec2,
    aws_eks as eks,
    aws_iam as iam,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    Duration,
    RemovalPolicy,
    Stack,
    CfnOutput,
    CfnJson,
)
from aws_cdk.lambda_layer_kubectl_v30 import KubectlV30Layer
from constructs import Construct
from cdk_nag import NagSuppressions
import os


class EKSFargateConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        cognito_user_pool_id: str,
        container_image_uri: str,
    ):
        super().__init__(scope, construct_id)

        # Create EKS cluster with Fargate as the compute option
        self.cluster = eks.FargateCluster(
            self,
            "EKSCluster",
            vpc=vpc,
            version=eks.KubernetesVersion.V1_30,
            kubectl_layer=KubectlV30Layer(self, "KubectlLayer"),
            cluster_name=f"nova-sonic-eks-{Stack.of(self).stack_name}",
            default_profile=eks.FargateProfileOptions(
                selectors=[
                    eks.Selector(namespace="default"),
                    eks.Selector(namespace="kube-system"),
                ]
            ),
            core_dns_compute_type=eks.CoreDnsComputeType.FARGATE,
            endpoint_access=eks.EndpointAccess.PUBLIC_AND_PRIVATE,
            cluster_logging=[
                eks.ClusterLoggingTypes.API,
                eks.ClusterLoggingTypes.AUDIT,
                eks.ClusterLoggingTypes.AUTHENTICATOR,
                eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
                eks.ClusterLoggingTypes.SCHEDULER,
            ],
        )
        
        # Add CDK Nag suppressions for EKS cluster internal resources
        NagSuppressions.add_resource_suppressions(
            self.cluster,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "EKS cluster internal resources use AWS managed policies"
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "EKS cluster internal resources require wildcard permissions"
                },
                {
                    "id": "AwsSolutions-L1",
                    "reason": "EKS cluster Lambda functions runtime is managed by AWS"
                },
                {
                    "id": "AwsSolutions-SF1",
                    "reason": "EKS cluster Step Functions logging is managed by AWS"
                },
                {
                    "id": "AwsSolutions-SF2",
                    "reason": "EKS cluster Step Functions X-Ray is managed by AWS"
                },
            ],
            apply_to_children=True
        )

        # Add Fargate profile for the application namespace
        app_fargate_profile = eks.FargateProfile(
            self,
            "AppFargateProfile",
            cluster=self.cluster,
            selectors=[
                eks.Selector(
                    namespace="websocket-app",
                    labels={"app": "websocket-server"}
                )
            ],
            fargate_profile_name="websocket-app-profile",
        )

        # Create namespace for the application
        app_namespace = self.cluster.add_manifest(
            "AppNamespace",
            {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": "websocket-app"},
            },
        )

        # Create IAM role for the service account (IRSA)
        service_account_role = iam.Role(
            self,
            "ServiceAccountRole",
            assumed_by=iam.FederatedPrincipal(
                self.cluster.open_id_connect_provider.open_id_connect_provider_arn,
                {
                    "StringEquals": CfnJson(
                        self,
                        "ServiceAccountRoleCondition",
                        value={
                            f"{self.cluster.cluster_open_id_connect_issuer}:aud": "sts.amazonaws.com",
                            f"{self.cluster.cluster_open_id_connect_issuer}:sub": "system:serviceaccount:websocket-app:websocket-sa",
                        },
                    )
                },
                "sts:AssumeRoleWithWebIdentity",
            ),
        )

        # Add required permissions to the service account role
        service_account_role.add_to_policy(
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
                    "s3:ListBucket",
                ],
                resources=["*"],
            )
        )

        # Create Kubernetes service account with IAM role
        service_account = self.cluster.add_service_account(
            "WebSocketServiceAccount",
            name="websocket-sa",
            namespace="websocket-app",
            annotations={
                "eks.amazonaws.com/role-arn": service_account_role.role_arn,
            },
        )
        service_account.node.add_dependency(app_namespace)

        # Create ConfigMap for application configuration
        config_map = self.cluster.add_manifest(
            "AppConfigMap",
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": "websocket-config",
                    "namespace": "websocket-app",
                },
                "data": {
                    "COGNITO_USER_POOL_ID": cognito_user_pool_id,
                    "AWS_REGION": Stack.of(self).region,
                    "PORT": "8080",
                    "LOG_LEVEL": "INFO",
                    "CORS_ALLOWED_ORIGINS": "*",
                    "DEPLOYMENT_TYPE": "eks-fargate",
                },
            },
        )
        config_map.node.add_dependency(app_namespace)

        # Create Deployment for the WebSocket server
        deployment = self.cluster.add_manifest(
            "WebSocketDeployment",
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "websocket-server",
                    "namespace": "websocket-app",
                    "labels": {"app": "websocket-server"},
                },
                "spec": {
                    "replicas": 2,
                    "selector": {
                        "matchLabels": {"app": "websocket-server"}
                    },
                    "template": {
                        "metadata": {
                            "labels": {"app": "websocket-server"},
                            "annotations": {
                                "prometheus.io/scrape": "true",
                                "prometheus.io/port": "8080",
                            },
                        },
                        "spec": {
                            "serviceAccountName": "websocket-sa",
                            "containers": [
                                {
                                    "name": "websocket-container",
                                    "image": container_image_uri,
                                    "ports": [
                                        {
                                            "containerPort": 8080,
                                            "protocol": "TCP",
                                        }
                                    ],
                                    "envFrom": [
                                        {
                                            "configMapRef": {
                                                "name": "websocket-config"
                                            }
                                        }
                                    ],
                                    "resources": {
                                        "requests": {
                                            "cpu": "0.25",
                                            "memory": "512Mi",
                                        },
                                        "limits": {
                                            "cpu": "0.5",
                                            "memory": "1Gi",
                                        },
                                    },
                                    "livenessProbe": {
                                        "httpGet": {
                                            "path": "/health",
                                            "port": 8080,
                                        },
                                        "initialDelaySeconds": 30,
                                        "periodSeconds": 10,
                                    },
                                    "readinessProbe": {
                                        "httpGet": {
                                            "path": "/health",
                                            "port": 8080,
                                        },
                                        "initialDelaySeconds": 10,
                                        "periodSeconds": 5,
                                    },
                                }
                            ],
                        },
                    },
                },
            },
        )
        deployment.node.add_dependency(service_account)
        deployment.node.add_dependency(config_map)
        deployment.node.add_dependency(app_fargate_profile)

        # Create Service of type LoadBalancer (will create NLB)
        service = self.cluster.add_manifest(
            "WebSocketService",
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": "websocket-service",
                    "namespace": "websocket-app",
                    "annotations": {
                        "service.beta.kubernetes.io/aws-load-balancer-type": "nlb",
                        "service.beta.kubernetes.io/aws-load-balancer-scheme": "internet-facing",
                        "service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled": "false",
                        "service.beta.kubernetes.io/aws-load-balancer-target-type": "ip",
                        "service.beta.kubernetes.io/aws-load-balancer-healthcheck-port": "8080",
                        "service.beta.kubernetes.io/aws-load-balancer-healthcheck-path": "/health",
                    },
                },
                "spec": {
                    "type": "LoadBalancer",
                    "selector": {"app": "websocket-server"},
                    "ports": [
                        {
                            "port": 80,
                            "targetPort": 8080,
                            "protocol": "TCP",
                            "name": "websocket",
                        }
                    ],
                    "sessionAffinity": "ClientIP",
                    "sessionAffinityConfig": {
                        "clientIP": {"timeoutSeconds": 10800}
                    },
                },
            },
        )
        service.node.add_dependency(deployment)
        # IMPORTANT: Service must wait for AWS Load Balancer Controller to be ready
        # This will be added after the controller is created

        # Create HorizontalPodAutoscaler for automatic scaling
        hpa = self.cluster.add_manifest(
            "WebSocketHPA",
            {
                "apiVersion": "autoscaling/v2",
                "kind": "HorizontalPodAutoscaler",
                "metadata": {
                    "name": "websocket-hpa",
                    "namespace": "websocket-app",
                },
                "spec": {
                    "scaleTargetRef": {
                        "apiVersion": "apps/v1",
                        "kind": "Deployment",
                        "name": "websocket-server",
                    },
                    "minReplicas": 2,
                    "maxReplicas": 10,
                    "metrics": [
                        {
                            "type": "Resource",
                            "resource": {
                                "name": "cpu",
                                "target": {
                                    "type": "Utilization",
                                    "averageUtilization": 70,
                                },
                            },
                        },
                        {
                            "type": "Resource",
                            "resource": {
                                "name": "memory",
                                "target": {
                                    "type": "Utilization",
                                    "averageUtilization": 80,
                                },
                            },
                        },
                    ],
                },
            },
        )
        hpa.node.add_dependency(deployment)

        # Install AWS Load Balancer Controller using Helm
        # First, create IAM policy for the controller
        lb_controller_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeInstances",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeTags",
                        "ec2:DescribeVpcs",
                        "ec2:GetCoipPoolUsage",
                        "ec2:DescribeCoipPools",
                        "elasticloadbalancing:DescribeLoadBalancers",
                        "elasticloadbalancing:DescribeLoadBalancerAttributes",
                        "elasticloadbalancing:DescribeListeners",
                        "elasticloadbalancing:DescribeListenerCertificates",
                        "elasticloadbalancing:DescribeRules",
                        "elasticloadbalancing:DescribeTargetGroups",
                        "elasticloadbalancing:DescribeTargetGroupAttributes",
                        "elasticloadbalancing:DescribeTargetHealth",
                        "elasticloadbalancing:DescribeTags",
                        "elasticloadbalancing:CreateListener",
                        "elasticloadbalancing:CreateLoadBalancer",
                        "elasticloadbalancing:CreateRule",
                        "elasticloadbalancing:CreateTargetGroup",
                        "elasticloadbalancing:DeleteListener",
                        "elasticloadbalancing:DeleteLoadBalancer",
                        "elasticloadbalancing:DeleteRule",
                        "elasticloadbalancing:DeleteTargetGroup",
                        "elasticloadbalancing:ModifyListener",
                        "elasticloadbalancing:ModifyLoadBalancerAttributes",
                        "elasticloadbalancing:ModifyRule",
                        "elasticloadbalancing:ModifyTargetGroup",
                        "elasticloadbalancing:ModifyTargetGroupAttributes",
                        "elasticloadbalancing:RegisterTargets",
                        "elasticloadbalancing:DeregisterTargets",
                        "elasticloadbalancing:SetWebAcl",
                        "elasticloadbalancing:SetSecurityGroups",
                        "elasticloadbalancing:SetSubnets",
                        "elasticloadbalancing:SetIpAddressType",
                        "ec2:CreateSecurityGroup",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:RevokeSecurityGroupIngress",
                        "ec2:DeleteSecurityGroup",
                        "ec2:ModifySecurityGroupRules",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeInternetGateways",
                        "ec2:CreateTags",
                        "ec2:DeleteTags",
                        "cognito-idp:DescribeUserPoolClient",
                        "acm:ListCertificates",
                        "acm:DescribeCertificate",
                        "iam:ListServerCertificates",
                        "iam:GetServerCertificate",
                        "waf-regional:GetWebACL",
                        "waf-regional:GetWebACLForResource",
                        "waf-regional:AssociateWebACL",
                        "waf-regional:DisassociateWebACL",
                        "wafv2:GetWebACL",
                        "wafv2:GetWebACLForResource",
                        "wafv2:AssociateWebACL",
                        "wafv2:DisassociateWebACL",
                        "shield:GetSubscriptionState",
                        "shield:DescribeProtection",
                        "shield:CreateProtection",
                        "shield:DeleteProtection",
                    ],
                    resources=["*"],
                )
            ]
        )

        lb_controller_service_account = self.cluster.add_service_account(
            "AWSLoadBalancerControllerServiceAccount",
            name="aws-load-balancer-controller",
            namespace="kube-system",
        )

        lb_controller_service_account.role.attach_inline_policy(
            iam.Policy(
                self,
                "AWSLoadBalancerControllerPolicy",
                document=lb_controller_policy,
            )
        )

        # Install the AWS Load Balancer Controller using Helm
        lb_controller_chart = self.cluster.add_helm_chart(
            "AWSLoadBalancerController",
            chart="aws-load-balancer-controller",
            repository="https://aws.github.io/eks-charts",
            namespace="kube-system",
            values={
                "clusterName": self.cluster.cluster_name,
                "serviceAccount": {
                    "create": False,
                    "name": "aws-load-balancer-controller",
                },
                "region": Stack.of(self).region,
                "vpcId": vpc.vpc_id,
            },
        )
        lb_controller_chart.node.add_dependency(lb_controller_service_account)

        # CRITICAL FIX: Add dependency so Service waits for AWS Load Balancer Controller
        # This prevents the "no endpoints available for service" error
        service.node.add_dependency(lb_controller_chart)
        hpa.node.add_dependency(lb_controller_chart)  # HPA should also wait

        # Add Fluent Bit for CloudWatch logging as a sidecar
        fluent_bit_config = self.cluster.add_manifest(
            "FluentBitConfigMap",
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": "fluent-bit-config",
                    "namespace": "websocket-app",
                },
                "data": {
                    "fluent-bit.conf": """
[SERVICE]
    Flush         5
    Daemon        Off
    Log_Level     info

[INPUT]
    Name              tail
    Path              /var/log/containers/*.log
    Parser            docker
    Tag               kube.*
    Refresh_Interval  5
    Mem_Buf_Limit     5MB

[FILTER]
    Name                kubernetes
    Match               kube.*
    Kube_URL            https://kubernetes.default.svc:443
    Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
    Merge_Log           On
    K8S-Logging.Parser  On
    K8S-Logging.Exclude On

[OUTPUT]
    Name                cloudwatch_logs
    Match               *
    region              ${AWS_REGION}
    log_group_name      /aws/eks/${CLUSTER_NAME}/application
    log_stream_prefix   ${HOSTNAME}-
    auto_create_group   true
"""
                },
            },
        )
        fluent_bit_config.node.add_dependency(app_namespace)

        # Add CDK Nag suppressions
        NagSuppressions.add_resource_suppressions(
            service_account_role,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Service account role needs access to various AWS services with dynamic resource names",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            lb_controller_service_account.role,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "AWS Load Balancer Controller needs broad permissions to manage load balancers",
                }
            ],
        )

        # Output the cluster name and endpoint
        CfnOutput(
            self,
            "ClusterName",
            value=self.cluster.cluster_name,
            description="EKS Cluster Name",
        )

        CfnOutput(
            self,
            "ClusterEndpoint",
            value=self.cluster.cluster_endpoint,
            description="EKS Cluster Endpoint",
        )

        CfnOutput(
            self,
            "KubectlRoleArn",
            value=self.cluster.kubectl_role.role_arn,
            description="IAM role for kubectl access",
        )

        # Store cluster reference for use in other constructs
        self.load_balancer_dns = None  # Will be populated after deployment
