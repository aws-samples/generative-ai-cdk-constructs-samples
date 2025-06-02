from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    RemovalPolicy,
    Stack,
)
from cdk_nag import NagSuppressions
from constructs import Construct


class VPCConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
    ):
        super().__init__(scope, construct_id)

        # Create VPC Flow Logs role with custom policy
        flow_log_role = iam.Role(
            self,
            "FlowLogRole",
            assumed_by=iam.ServicePrincipal("vpc-flow-logs.amazonaws.com")
        )

        # Add custom policy for VPC Flow Logs
        flow_log_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams"
                ],
                resources=["*"]
            )
        )

        # Create Lambda role for security group management
        sg_manager_role = iam.Role(
            self,
            "SecurityGroupManagerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        # Add permissions for security group management
        sg_manager_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:RevokeSecurityGroupIngress",
                    "ec2:DescribeSecurityGroups"
                ],
                resources=["*"]
            )
        )

        # Add CloudWatch Logs permissions for Lambda
        sg_manager_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=["*"]
            )
        )

        # Add CDK Nag suppression for security group manager role
        NagSuppressions.add_resource_suppressions(
            sg_manager_role,
            suppressions=[{
                "id": "AwsSolutions-IAM5",
                "reason": "Security group manager role needs access to manage security groups and CloudWatch logs"
            }]
        )

        # Add CDK Nag suppression for Flow Logs role
        NagSuppressions.add_resource_suppressions(
            flow_log_role,
            suppressions=[{
                "id": "AwsSolutions-IAM5",
                "reason": "VPC Flow Logs role needs access to create and manage log groups/streams"
            }]
        )

        # Create VPC with NAT Gateway
        self.vpc = ec2.Vpc(
            self, 
            "VPC",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # Add Flow Logs
        self.vpc.add_flow_log(
            "FlowLog",
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(
                log_group=logs.LogGroup(
                    self,
                    "VPCFlowLogsGroup",
                    retention=logs.RetentionDays.ONE_WEEK,
                    removal_policy=RemovalPolicy.DESTROY
                ),
                iam_role=flow_log_role
            ),
            traffic_type=ec2.FlowLogTrafficType.ALL
        )
