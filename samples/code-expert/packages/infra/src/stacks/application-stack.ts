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

import { CfnOutput, Duration, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import { CodeExpertWorkflow } from "../constructs/code-expert/workflow";
import { SecureBucket } from "../constructs/secure-bucket";

export class ApplicationStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const modelId: string =
      scope.node.tryGetContext("modelId") ??
      "anthropic.claude-3-5-sonnet-20240620-v1:0";

    const inputBucket = new SecureBucket(this, "InputBucket", {});
    const outputBucket = new SecureBucket(this, "OutputBucket", {});
    const configBucket = new SecureBucket(this, "ConfigBucket", {
      lifecycleRules: [],
    });

    const bedrockBatchBucket = new SecureBucket(this, "BedrockBatchBucket", {
      lifecycleRules: [
        {
          enabled: true,
          expiration: Duration.days(7),
        },
      ],
    });

    const codeExpertWorkflow = new CodeExpertWorkflow(this, "CodeExpert", {
      bedrockBatchBucket: bedrockBatchBucket,
      configBucket: configBucket,
      inputBucket: inputBucket,
      outputBucket: outputBucket,
      modelId: modelId,
    });

    new CfnOutput(this, "InputBucketName", {
      value: inputBucket.bucketName,
    });

    new CfnOutput(this, "OutputBucketName", {
      value: outputBucket.bucketName,
    });

    new CfnOutput(this, "ConfigBucketName", {
      value: configBucket.bucketName,
    });

    new CfnOutput(this, "BedrockBatchBucketName", {
      value: bedrockBatchBucket.bucketName,
    });

    new CfnOutput(this, "StateMachineArn", {
      value: codeExpertWorkflow.stateMachine.stateMachineArn,
    });
  }
}
