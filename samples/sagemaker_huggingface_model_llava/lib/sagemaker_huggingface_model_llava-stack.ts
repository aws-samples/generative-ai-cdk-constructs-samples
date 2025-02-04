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
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import * as genai from '@cdklabs/generative-ai-cdk-constructs';

export class SagemakerHuggingfaceModelLlavaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define some constants
    const SG_ENDPOINT_NAME = 'llavaendpoint';
    const HUGGING_FACE_MODEL_ID = 'llava-hf/llava-1.5-7b-hf';

    // Custom Sagemaker Endpoint construct
    const CustomHuggingFaceEndpoint = new genai.CustomSageMakerEndpoint(this, 'testllavaendpoint', {
      modelId: HUGGING_FACE_MODEL_ID,
      instanceType: genai.SageMakerInstanceType.ML_G5_12XLARGE,
      container: genai.DeepLearningContainerImage.HUGGINGFACE_PYTORCH_INFERENCE_2_1_0_TRANSFORMERS4_37_0_GPU_PY310_CU118_UBUNTU20_04,
      modelDataUrl: 's3://BUCKET/KEY',
      environment: {
        HF_MODEL_ID: HUGGING_FACE_MODEL_ID,
        SAGEMAKER_CONTAINER_LOG_LEVEL: "20",
        SAGEMAKER_REGION: "us-east-1",
      },
      endpointName: SG_ENDPOINT_NAME,
      startupHealthCheckTimeoutInSeconds: 900,
      modelDataDownloadTimeoutInSeconds: 900,
    });

    this.templateOptions.description = 'Description: (uksb-1tupboc43) (tag: Sagemaker Hugging Face llava Sample)'

    CustomHuggingFaceEndpoint.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          's3:GetObject',
          's3:GetObject*',
          's3:GetBucket*',
          's3:List*',
        ],
        resources: [
          'BUCKET_ARN',
          'BUCKET_ARN/*',
        ],
      }),
    );

    // Lambda request handler used to interact with the SageMaker endpoint
    const requestHandler = new lambda.Function(this, 'DemoRequestHandlerHuggingFace', {
      code: lambda.Code.fromAsset(
          path.join(__dirname, '../lambda')
        ),
      functionName: 'testllavahuggingface',
      handler: 'lambda.handler',
      description: 'Lambda request handler used to interact with the SageMaker endpoint',
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      tracing: lambda.Tracing.ACTIVE,
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      environment: {
        'ENDPOINT_NAME': SG_ENDPOINT_NAME
      }
    });

    CustomHuggingFaceEndpoint.grantInvoke(requestHandler);
  }
}
