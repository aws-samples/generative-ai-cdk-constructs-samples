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

import { App, Aspects } from 'aws-cdk-lib';
import { AwsSolutionsChecks } from 'cdk-nag';
import { AppOneStack } from './stacks/app-one';

const devEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const app = new App();

Aspects.of(app).add(new AwsSolutionsChecks());

const demo = app.node.tryGetContext('demo') ?? 'demo-one';

switch (demo) {
  case 'demo-one':
    new AppOneStack(app, 'cdk-lambda-strands-durable-demo-app-one', {
      env: devEnv,
      description: 'Strands weather agent on lambda with durable execution - Demo 1',
    });
    break;
  default:
    throw new Error(`Demo ${demo} not found`);
}

app.synth();
