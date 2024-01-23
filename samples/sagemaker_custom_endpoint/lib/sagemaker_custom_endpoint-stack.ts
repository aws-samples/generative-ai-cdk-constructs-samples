import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import * as genai from '@cdklabs/generative-ai-cdk-constructs';

export class SagemakerCustomEndpointStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define some constants
    const SG_ENDPOINT_NAME = 'testbgebase';

    // Lambda request handler used to interact with the SageMaker endpoint
    const customEndpoint = new genai.CustomSageMakerEndpoint(this, 'test3', {
      modelId: 'bgeinf2',
      instanceType: genai.SageMakerInstanceType.ML_INF2_XLARGE,
      container: genai.DeepLearningContainerImage.fromDeepLearningContainerImage('huggingface-pytorch-inference-neuronx', '1.13.1-transformers4.34.1-neuronx-py310-sdk2.15.0-ubuntu20.04'),
      modelDataUrl: 's3://BUCKET/KEY',
      environment: {
        SAGEMAKER_CONTAINER_LOG_LEVEL: "20",
        SAGEMAKER_MODEL_SERVER_WORKERS: "2",
        SAGEMAKER_REGION: "us-east-2",
      },
      endpointName: SG_ENDPOINT_NAME,
      instanceCount: 1,
      volumeSizeInGb: 100
    });

    customEndpoint.addToRolePolicy(
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

    const requestHandlercustombge = new lambda.Function(this, 'DemoRequestHandlerCustom', {
      code: lambda.Code.fromAsset(
          path.join(__dirname, "../lambda")
        ),
      functionName: "testbgecustom",
      handler: "lambda.handler",
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      tracing: lambda.Tracing.ACTIVE,
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      environment: {
        'ENDPOINT_NAME': SG_ENDPOINT_NAME
      }
    });

    customEndpoint.grantInvoke(requestHandlercustombge);
  }
}
