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

import * as path from "node:path";
import * as lambda_python from "@aws-cdk/aws-lambda-python-alpha";
import { aws_lambda as lambda, aws_s3 as s3, Duration } from "aws-cdk-lib";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

export interface ProcessFindingsFunctionProps {
  readonly outputBucket: s3.IBucket;
  readonly bedrockBatchBucket: s3.IBucket;
  readonly modelId: string;
}

export class ProcessFindingsFunction extends lambda_python.PythonFunction {
  constructor(
    scope: Construct,
    id: string,
    props: ProcessFindingsFunctionProps,
  ) {
    super(scope, id, {
      entry: path.resolve(
        __dirname,
        "..",
        "..",
        "..",
        "..",
        "code-expert",
        "code-expert",
      ),
      bundling: {
        assetExcludes: ["tests/", "test_data/", ".*", "dist/", "pytest.ini"],
      },
      index: "amzn_code_expert_code_expert/lambda_handlers/process_findings.py",
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      memorySize: 2048,
      timeout: Duration.minutes(5),
      environment: {
        OUTPUT_BUCKET: props.outputBucket.bucketName,
        BATCH_BUCKET: props.bedrockBatchBucket.bucketName,
        MODEL_ID: props.modelId,
      },
    });

    props.bedrockBatchBucket.grantRead(this);
    props.outputBucket.grantWrite(this);

    NagSuppressions.addResourceSuppressions(
      this,
      [
        {
          id: "AwsSolutions-IAM4",
          reason: `Allow the use of AWS Managed Policies for Lambda execution.`,
          appliesTo: [
            "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
          ],
        },
        {
          id: "AwsSolutions-IAM5",
          reason: `Wildcards allow access to any objects in specific buckets.`,
        },
      ],
      true,
    );
  }
}
