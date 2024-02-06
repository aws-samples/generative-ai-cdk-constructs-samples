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
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import * as genai from '@cdklabs/generative-ai-cdk-constructs';

export class SagemakerHuggingfaceModelStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define some constants
    const SG_ENDPOINT_NAME = 'mistralendpoint';
    const HUGGING_FACE_MODEL_ID = 'mistralai/Mistral-7B-Instruct-v0.1';

    // Sagemaker construct model from Hugging Face
    const HuggingFaceEndpoint = new genai.HuggingFaceSageMakerEndpoint(this, 'testmistralendpoint', {
      modelId: HUGGING_FACE_MODEL_ID,
      instanceType: genai.SageMakerInstanceType.ML_G5_2XLARGE,
      container: genai.DeepLearningContainerImage.HUGGINGFACE_PYTORCH_TGI_INFERENCE_2_0_1_TGI1_1_0_GPU_PY39_CU118_UBUNTU20_04,
      environment: {
          SM_NUM_GPUS: '1',
          MAX_INPUT_LENGTH: '2048',
          MAX_TOTAL_TOKENS: '4096',
      },
      endpointName: SG_ENDPOINT_NAME
    });

    // Lambda request handler used to interact with the SageMaker endpoint
    const requestHandler = new lambda.Function(this, 'DemoRequestHandlerHuggingFace', {
      code: lambda.Code.fromAsset(
          path.join(__dirname, '../lambda')
        ),
      functionName: 'testmistralhuggingface',
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

    HuggingFaceEndpoint.grantInvoke(requestHandler);
  }
}
