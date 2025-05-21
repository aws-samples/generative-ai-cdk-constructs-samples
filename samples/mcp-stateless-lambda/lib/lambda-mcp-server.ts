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
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as path from 'path';
import { Aws, Duration } from 'aws-cdk-lib';

export interface LambdaMcpServerProps {
  // Optionally allow for overrides in the future
}

export class LambdaMcpServer extends Construct {
  public readonly lambdaFunction: lambda.Function;

  constructor(scope: Construct, id: string, props?: LambdaMcpServerProps) {
    super(scope, id);

    this.lambdaFunction = new lambda.Function(this, 'McpServerLambda', {
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: 'run.sh', // Handler is required but will be overridden by the exec wrapper
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambdas/mcpserver')),
      layers: [
        lambda.LayerVersion.fromLayerVersionArn(this, 'StreamableHttpTransportLayer', `arn:aws:lambda:${Aws.REGION}:753240598075:layer:LambdaAdapterLayerX86:25`),
      ],
      memorySize: 512,
      timeout: Duration.seconds(10),
      environment: {
        AWS_LWA_PORT: '3000',
        AWS_LAMBDA_EXEC_WRAPPER: '/opt/bootstrap',
      },
    });
  }
}
