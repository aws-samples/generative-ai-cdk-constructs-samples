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
import { Duration } from 'aws-cdk-lib';

export interface LambdaMcpAuthorizerProps {
  // Optionally allow for overrides in the future
}

export class LambdaMcpAuthorizer extends Construct {
  public readonly lambdaFunction: lambda.Function;

  constructor(scope: Construct, id: string, props?: LambdaMcpAuthorizerProps) {
    super(scope, id);

    this.lambdaFunction = new lambda.Function(this, 'McpAuthorizerLambda', {
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambdas/authorizer')),
      memorySize: 256,
      timeout: Duration.seconds(10),
    });
  }
}
