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
import { Construct } from 'constructs';
import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { LambdaMcpServer } from './lambda-mcp-server';
import { LambdaMcpAuthorizer } from './lambda-mcp-authorizer';

export interface ApiGatewayMcpProps {
  readonly lambdaMcpServer: LambdaMcpServer;
  readonly lambdaMcpAuthorizer: LambdaMcpAuthorizer;
}

export class ApiGatewayMcp extends Construct {
  public readonly apiGateway: apigateway.RestApi;

  constructor(scope: Construct, id: string, props: ApiGatewayMcpProps) {
    super(scope, id);

    const logGroup = new cdk.aws_logs.LogGroup(this, 'LogGroup');

    this.apiGateway = new apigateway.RestApi(this, 'ApiGateway', {
      restApiName: 'McpStatelessLambdaApi',
      deploy: true,
      cloudWatchRole: true,
      deployOptions: {
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: false,
        tracingEnabled: true,
        accessLogDestination: new apigateway.LogGroupLogDestination(logGroup),
        accessLogFormat: apigateway.AccessLogFormat.clf(),
        stageName: 'dev',
      },
    });

    // add resource to the api gateway
    const resource = this.apiGateway.root.addResource('mcp');

    // add authorizer to the api gateway
    const auth = new apigateway.TokenAuthorizer(this, 'mcpAuthorizer', {
        handler: props.lambdaMcpAuthorizer.lambdaFunction,
        identitySource: 'method.request.header.Authorization',
        resultsCacheTtl: cdk.Duration.minutes(0), // disable caching
      });

    // add integration to the api gateway
    const integration = new apigateway.LambdaIntegration(props.lambdaMcpServer.lambdaFunction)

    // add method to the api gateway
    resource.addMethod('ANY', integration, {
        authorizationType: apigateway.AuthorizationType.CUSTOM,
        authorizer: auth
    });

    // Ensure no double slash in endpoint URL
    const mcpEndpoint = this.apiGateway.url.replace(/\/$/, '') + resource.path;

    // add output for the api gateway endpoint
    new cdk.CfnOutput(this, 'McpServerEndpoint', {
        description: 'MCP Server Endpoint',
        value: mcpEndpoint,
        exportName: `${cdk.Stack.of(this).stackName}${id}McpServerEndpoint`,
    });
  }

}