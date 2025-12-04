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

import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import { Stack, Aws } from 'aws-cdk-lib';
import { Role, ServicePrincipal, Policy, PolicyStatement, Effect } from 'aws-cdk-lib/aws-iam';
import { NagSuppressions } from 'cdk-nag';
import { Construct } from 'constructs';

export class PythonLambda extends PythonFunction {
  constructor(scope: Construct, id: string, props: PythonFunctionProps) {
    const role = new Role(scope, 'Role', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
    });

    super(scope, id, {
      ...props,
      role: role,
    });

    const functionName = this.functionName;

    role.attachInlinePolicy(this._lambdaBasicPolicy(scope, id, functionName));
    role.attachInlinePolicy(this._lambdaCheckpointPolicy(scope, id, functionName));
  }

  /**
   * Creates a policy that allows the lambda to create log groups and write logs to them.
   * @param scope - The scope of the construct.
   * @param constructId - The id of the construct.
   * @param functionName - The name of the function.
   * @returns A policy that allows the lambda to create log groups and write logs to them.
   */
  private _lambdaBasicPolicy(scope: Construct, constructId: string, functionName: string): Policy {
    const region = Stack.of(scope).region;
    const account = Stack.of(scope).account;

    const policy = new Policy(
      scope,
      `${constructId}LambdaBasicExecPolicy`,
      {
        statements: [
          new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
              'logs:CreateLogGroup',
              'logs:CreateLogStream',
              'logs:PutLogEvents',
            ],
            resources: [
              `arn:${Aws.PARTITION}:logs:${region}:${account}:log-group:/aws/lambda/${functionName}`,
              `arn:${Aws.PARTITION}:logs:${region}:${account}:log-group:/aws/lambda/${functionName}:*`,
            ],
          }),
        ],
      },
    );

    NagSuppressions.addResourceSuppressions(
      policy,
      [
        {
          id: 'AwsSolutions-IAM5',
          appliesTo: [{
            regex: '/^Resource::arn:<AWS::Partition>:logs:.*:log-group:/aws/lambda/.*:\\*$/',
          }],
          reason: 'Lambda requires wildcard suffix on log group ARN to create and write to log streams within its dedicated log group.',
        },
      ],
    );

    return policy;
  }

  /**
   * Creates a policy that allows the lambda to checkpoint durable executions.
   * @param scope - The scope of the construct.
   * @param constructId - The id of the construct.
   * @param functionName - The name of the function.
   * @returns A policy that allows the lambda to checkpoint durable executions.
   */
  private _lambdaCheckpointPolicy(scope: Construct, constructId: string, functionName: string): Policy {
    const region = Stack.of(scope).region;
    const account = Stack.of(scope).account;

    const policy = new Policy(
      scope,
      `${constructId}LambdaCheckpointPolicy`,
      {
        statements: [
          new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
              'lambda:CheckpointDurableExecution',
              'lambda:GetDurableExecutionState',
            ],
            resources: [
              // Qualified ARN with wildcard for durable execution paths
              // Durable execution uses qualified ARNs like: function:$LATEST/durable-execution/...
              `arn:${Aws.PARTITION}:lambda:${region}:${account}:function:${functionName}:*`,
            ],
          }),
        ],
      },
    );

    NagSuppressions.addResourceSuppressions(
      policy,
      [
        {
          id: 'AwsSolutions-IAM5',
          appliesTo: [{
            regex: '/^Resource::arn:<AWS::Partition>:lambda:.*:function:.*:\\*$/',
          }],
          reason: 'Lambda requires wildcard suffix on function ARN to checkpoint durable executions.',
        },
      ],
    );

    return policy;
  }
}
