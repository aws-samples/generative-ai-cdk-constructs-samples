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

import * as path from 'path';
import * as bedrock from '@aws-cdk/aws-bedrock-alpha';
import { Stack, StackProps, Duration, Fn, CfnOutput } from 'aws-cdk-lib';
import { Runtime, CfnFunction } from 'aws-cdk-lib/aws-lambda';
import { NagSuppressions } from 'cdk-nag';
import { Construct } from 'constructs';
// Internal constructs
import { PythonLambda } from '../constructs/python-lambda';

export class AppOneStack extends Stack {
  constructor(scope: Construct, id: string, props: StackProps = {}) {
    super(scope, id, props);

    const bedrockModel = bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_SONNET_4_5_V1_0;

    const cris = bedrock.CrossRegionInferenceProfile.fromConfig({
      geoRegion: bedrock.CrossRegionInferenceProfileRegion.GLOBAL,
      model: bedrockModel,
    });

    const pythonLambda = new PythonLambda(this, 'PythonLambda', {
      entry: path.join(__dirname, '..', '..', 'lambda', 'demo-one'),
      index: 'agent_handler.py',
      handler: 'handler',
      runtime: Runtime.PYTHON_3_14,
      timeout: Duration.minutes(5),
      description: 'Strands weather agent on lambda with durable execution - Demo 1',
      environment: {
        MODEL_ID: cris.inferenceProfileId,
      },
    });

    // Use escape hatch to add DurableConfig (not yet exposed in CDK)
    // Get the CloudFormation resource (L1 construct)
    const cfnFunction = pythonLambda.node.defaultChild as CfnFunction;
    // Add DurableConfig properties using escape hatch
    // Use individual property overrides for nested structure
    cfnFunction.addPropertyOverride('DurableConfig.ExecutionTimeout', 900);
    cfnFunction.addPropertyOverride('DurableConfig.RetentionPeriodInDays', 1);

    // Grant invoke permissions to the bedrock model
    cris.grantInvoke(pythonLambda);
    bedrockModel.grantInvokeAllRegions(pythonLambda);

    // Add Nag suppressions for Bedrock permissions on the DefaultPolicy
    // The DefaultPolicy is created automatically when grantInvoke adds permissions
    // Use the same path as the aspect
    NagSuppressions.addResourceSuppressionsByPath(
      this,
      `${pythonLambda.role!.node.path}/DefaultPolicy/Resource`,
      [
        {
          id: 'AwsSolutions-IAM5',
          appliesTo: [{
            regex: '/^Action::bedrock:InvokeModel\\*$/',
          }],
          reason: 'Bedrock Cross-Region Inference Profile requires wildcard action to invoke the model across regions.',
        },
        {
          id: 'AwsSolutions-IAM5',
          appliesTo: [{
            regex: '/^Resource::arn:<AWS::Partition>:bedrock:\\*::foundation-model/.*$/',
          }],
          reason: 'Bedrock Cross-Region Inference Profile requires wildcard resource pattern to support cross-region model invocation.',
        },
      ],
    );

    new CfnOutput(this, 'PythonLambdaName', {
      value: pythonLambda.functionName,
      description: 'The name of the Python Lambda function',
    });
  }
}
