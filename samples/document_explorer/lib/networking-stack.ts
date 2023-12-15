import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';

export class NetworkingStack extends Stack {
    public readonly vpc: ec2.Vpc;
    public readonly securityGroups: ec2.SecurityGroup[];
    public readonly privateSubnets: string[];

    constructor(scope: Construct, id: string, props?: StackProps) {
        super(scope, id, props);

        //---------------------------------------------------------------------
        // VPC
        //---------------------------------------------------------------------
        this.vpc = new ec2.Vpc(this, 'VPC', {
            subnetConfiguration: [
            {
                name: 'public',
                subnetType: ec2.SubnetType.PUBLIC,
                cidrMask: 24,
                mapPublicIpOnLaunch: false,
            },
            {
                name: 'private',
                subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
                cidrMask: 24
            },
            {
                name: 'isolated',
                subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
                cidrMask: 24,
            },
            ],
            ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16')
        });

        //VPC Flow Logs
        const logGroup = new logs.LogGroup(this, 'VPCFlowLogsLogGroup');
        const vpcFlowLogrole = new iam.Role(this, 'VPCFlowLogsRole', {
        assumedBy: new iam.ServicePrincipal('vpc-flow-logs.amazonaws.com'),
        });
        new ec2.FlowLog(this, 'FlowLog', {
            resourceType: ec2.FlowLogResourceType.fromVpc(this.vpc),
            destination: ec2.FlowLogDestination.toCloudWatchLogs(logGroup, vpcFlowLogrole),
        });
    
        //---------------------------------------------------------------------
        // Security Group
        //---------------------------------------------------------------------
        this.securityGroups = [
            new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
            vpc: this.vpc,
            allowAllOutbound: true,
            description: 'security group for lambda',
            securityGroupName: 'lambdaSecurityGroup',
            }),
        ];
        this.securityGroups[0].addIngressRule(this.securityGroups[0], ec2.Port.tcp(443), 'allow https within sg');

        //---------------------------------------------------------------------
        // Private Subnets
        //---------------------------------------------------------------------
        this.privateSubnets = this.vpc.privateSubnets.map(subnet => subnet.subnetId);
    }
}
