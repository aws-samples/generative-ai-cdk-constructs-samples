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
import { NagSuppressions } from "cdk-nag";
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import * as genai from '@cdklabs/generative-ai-cdk-constructs';

export class SagemakerHuggingfaceModelSvdStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define some constants
    const SG_ENDPOINT_NAME = 'svdendpoint';
    const HUGGING_FACE_MODEL_ID = 'stabilityai/stable-video-diffusion-img2vid-xt-1-1';
    const BUCKET_PATH = 's3://BUCKET'

    // Custom Sagemaker Endpoint construct
    const CustomHuggingFaceEndpoint = new genai.CustomSageMakerEndpoint(this, 'testsvdendpoint', {
      modelId: HUGGING_FACE_MODEL_ID,
      instanceType: genai.SageMakerInstanceType.ML_G5_4XLARGE,
      container: genai.DeepLearningContainerImage.HUGGINGFACE_PYTORCH_INFERENCE_2_1_0_TRANSFORMERS4_37_0_GPU_PY310_CU118_UBUNTU20_04,
      modelDataUrl: BUCKET_PATH+'/model.tar.gz',
      environment: {
        HF_MODEL_ID: HUGGING_FACE_MODEL_ID,
        SAGEMAKER_CONTAINER_LOG_LEVEL: "20",
        SAGEMAKER_REGION: "us-east-1",
        SAGEMAKER_MODEL_SERVER_TIMEOUT: "3600",
        TS_MAX_RESPONSE_SIZE: "1000000000",
        TS_MAX_REQUEST_SIZE: "1000000000",
        MMS_MAX_RESPONSE_SIZE: "1000000000",
        MMS_MAX_REQUEST_SIZE: "1000000000",
        HF_API_TOKEN: 'XXXXX'
      },
      endpointName: SG_ENDPOINT_NAME,
      startupHealthCheckTimeoutInSeconds: 900,
      modelDataDownloadTimeoutInSeconds: 900,
      asyncInference: {
        maxConcurrentInvocationsPerInstance: 15,
        outputPath: BUCKET_PATH+'/output/',
        failurePath: BUCKET_PATH+'/failure/'
      }
    });

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

    NagSuppressions.addResourceSuppressions(
      CustomHuggingFaceEndpoint,
      [
        {
          id: 'AwsSolutions-IAM4',
          reason: 'Sample SageMaker default endpoint role uses AWS Managed Policy.',
        },
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Sample SageMaker default endpoint role uses wildcards for bucket access.',
        },
      ],
      true,
    );
  }
}
