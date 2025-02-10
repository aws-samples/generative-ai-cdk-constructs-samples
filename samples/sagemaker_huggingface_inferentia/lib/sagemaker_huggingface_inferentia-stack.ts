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

export class SagemakerHuggingfaceInferentiaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define some constants
    const SG_ENDPOINT_NAME = 'zephyr7bneuron';
    const HUGGING_FACE_MODEL_ID = 'aws-neuron/zephyr-7b-seqlen-2048-bs-4-cores-2';

    // Sagemaker construct model from Hugging Face
    const HuggingFaceEndpointInferentia = new genai.HuggingFaceSageMakerEndpoint(this, 'testzephyr7bendpoint', {
      modelId: HUGGING_FACE_MODEL_ID,
      instanceType: genai.SageMakerInstanceType.ML_INF2_8XLARGE,
      container: genai.DeepLearningContainerImage.fromDeepLearningContainerImage('huggingface-pytorch-tgi-inference','1.13.1-optimum0.0.17-neuronx-py310-ubuntu22.04-v1.0'),
      environment: {
        HF_MODEL_ID: HUGGING_FACE_MODEL_ID,
        MAX_CONCURRENT_REQUESTS: '4',
        MAX_INPUT_LENGTH: '1512',
        MAX_TOTAL_TOKENS: '2048',
        MAX_BATCH_PREFILL_TOKENS: '4096',
        MAX_BATCH_TOTAL_TOKENS: '8192',
      },
      startupHealthCheckTimeoutInSeconds: 900,
      endpointName: SG_ENDPOINT_NAME
    });

    this.templateOptions.description= 'Description: (uksb-1tupboc43) (tag: Sagemaker hugging face infrentia Stack)'

    // Lambda request handler used to interact with the SageMaker endpoint
    const requestHandler = new lambda.Function(this, 'DemoRequestHandlerHuggingFaceInferentia', {
      code: lambda.Code.fromAsset(
          path.join(__dirname, '../lambda')
        ),
      functionName: 'testzephyrhuggingfaceinferentia',
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

    HuggingFaceEndpointInferentia.grantInvoke(requestHandler);
  }
}
