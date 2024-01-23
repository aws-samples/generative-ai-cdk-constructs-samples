import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import * as genai from '@cdklabs/generative-ai-cdk-constructs';

export class SagemakerJumpstartModelStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define some constants
    const SG_ENDPOINT_NAME = 'testllamatwo';

    // Deploy Llama 2 7B version 2.0.2 from SageMaker Jumpstart to a real-time SageMaker endpoint
    const JmpStrtTestConstruct = new genai.JumpStartSageMakerEndpoint(this, 'testllamatwosevenb', {
      model: genai.JumpStartModel.META_TEXTGENERATION_LLAMA_2_7B_F_2_0_2,
      instanceType: genai.SageMakerInstanceType.ML_G5_2XLARGE,
      endpointName: SG_ENDPOINT_NAME
    });

    // Lambda request handler used to interact with the SageMaker endpoint
    const requestHandler = new lambda.Function(this, 'DemoRequestHandlerJumpstart', {
      code: lambda.Code.fromAsset(
          path.join(__dirname, '../lambda')
        ),
      functionName: 'lambdallama2',
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

    JmpStrtTestConstruct.grantInvoke(requestHandler);
  }
}
