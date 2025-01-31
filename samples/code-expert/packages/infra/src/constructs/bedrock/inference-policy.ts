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

import { aws_iam as iam, aws_s3 as s3, Stack } from "aws-cdk-lib";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

export interface BedrockBatchRoleProps {
  readonly bedrockBatchBucket: s3.IBucket;
}

/**
 * This class creates a singleton managed policy that enables the use of any
 * Bedrock foundation model and inference profile.
 */
export class BedrockInferencePolicy {
  public static getBedrockInferencePolicy(
    scope: Construct,
    constructId: string = "BedrockInferencePolicy",
  ): iam.ManagedPolicy {
    if (!BedrockInferencePolicy.policy) {
      BedrockInferencePolicy.policy = new iam.ManagedPolicy(
        scope,
        constructId,
        {},
      );
      BedrockInferencePolicy.policy.addStatements(
        new iam.PolicyStatement({
          sid: "Inference",
          actions: ["bedrock:InvokeModel", "bedrock:CreateModelInvocationJob"],
          resources: [
            `arn:aws:bedrock:${Stack.of(scope).region}::foundation-model/*`,
          ],
        }),

        new iam.PolicyStatement({
          sid: "CrossRegionInference",
          actions: ["bedrock:InvokeModel", "bedrock:CreateModelInvocationJob"],
          resources: [
            Stack.of(scope).formatArn({
              service: "bedrock",
              resource: "inference-profile",
              resourceName: "*",
            }),
            ...inferenceProfileRegionMap(Stack.of(scope).region).map(
              (region) => `arn:aws:bedrock:${region}::foundation-model/*`,
            ),
          ],
        }),
      );
    }

    NagSuppressions.addResourceSuppressions(
      BedrockInferencePolicy.policy,
      [
        {
          id: "AwsSolutions-IAM5",
          reason:
            "This policy has wildcards to enable any bedrock foundation model.",
        },
      ],
      true,
    );
    return BedrockInferencePolicy.policy;
  }

  private static policy: iam.ManagedPolicy;

  private constructor() {} // Prevent direct instantiation
}

function inferenceProfileRegionMap(region: string): string[] {
  if (region.startsWith("us-")) {
    return ["us-east-1", "us-east-2", "us-west-2"];
  }
  if (region.startsWith("eu-")) {
    return ["eu-central-1", "eu-west-1", "eu-west-3"];
  }
  if (region.startsWith("ap-")) {
    return ["ap-northeast-1", "ap-southeast-1", "ap-southeast-2"];
  }
  throw new Error(`Region ${region} not supported`);
}
