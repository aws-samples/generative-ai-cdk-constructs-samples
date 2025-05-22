/**
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 *  with the License. A copy of the License is located at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 *  and limitations under the License.
 */
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import path = require('path');
import { AlbToFargate } from '@aws-solutions-constructs/aws-alb-fargate';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Duration, RemovalPolicy } from 'aws-cdk-lib';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as logs from 'aws-cdk-lib/aws-logs';

export class McpStatelessEcsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const execution_role = new iam.Role(
      this,
      "ExecutionRole",
      {
        assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AmazonECSTaskExecutionRolePolicy")
        ]
      }
    )

    const task_role = new iam.Role(
      this,
      "TaskRole",
      {
        assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      }
    )

    task_role.addToPolicy(
      new iam.PolicyStatement(
        {
          actions: ["logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
          ],
          resources: ["*"],
        }
      )
    )

    const log_group = new logs.LogGroup(
      this,
      "LogGroup",
      {
        retention: logs.RetentionDays.ONE_WEEK,
        removalPolicy: RemovalPolicy.DESTROY,
      }
    )

    const task_definition = new ecs.FargateTaskDefinition(
      this,
      "TaskDefinition",
      {
        taskRole: task_role,
        executionRole: execution_role,
      }
    )

    const container_definition_props = {
      image: ecs.ContainerImage.fromAsset(
        path.join(__dirname, '../mcp_server'),
        {
          file: 'Dockerfile',
          platform: ecr_assets.Platform.LINUX_AMD64
        }
      ),
      essential: true,
      portMappings: [
          {
            containerPort: 3000,
            hostPort: 3000,
            protocol: ecs.Protocol.TCP
          }
      ],
      logging: ecs.LogDrivers.awsLogs({
        logGroup: log_group,
        streamPrefix: "ecs"
      })
    }

    task_definition.addContainer("McpServerContainer", 
      {
        image: ecs.ContainerImage.fromAsset(
          path.join(__dirname, '../mcp_server'),
          {
            file: 'Dockerfile',
            platform: ecr_assets.Platform.LINUX_AMD64
          }
        ),
        essential: true,
        portMappings: [
            {
              containerPort: 3000,
              hostPort: 3000,
              protocol: ecs.Protocol.TCP
            }
        ],
        logging: ecs.LogDrivers.awsLogs({
          logGroup: log_group,
          streamPrefix: "ecs"
        })
      }
    )

    // Define target group configuration
    const target_group_props =  {
      port: 3000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      healthCheck: {
          path: "/health",
          port: "3000",
          healthyHttpCodes: "200",
          interval: Duration.seconds(30),
          timeout: Duration.seconds(5)
      },
      targetType: elbv2.TargetType.IP
    }

  const albToFargate = new AlbToFargate(this, 'AlbToFargate', {
    publicApi: true,
    fargateTaskDefinitionProps: task_definition,
    targetGroupProps: target_group_props,
    containerDefinitionProps: container_definition_props,
    listenerProps: {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
    },
  });

  // add output for the endpoint
  new cdk.CfnOutput(this, 'McpServerEndpoint', {
    description: 'MCP Server Endpoint',
    value: `http://${albToFargate.loadBalancer.loadBalancerDnsName}/mcp`,
    exportName: `${cdk.Stack.of(this).stackName}${id}McpServerEndpoint`,
});
    
}}
