import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { ApiGatewayToLambda } from '@aws-solutions-constructs/aws-apigateway-lambda';
import * as genai from '@cdklabs/generative-ai-cdk-constructs';

export class BedrockDataAutomationAPIStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    
    const bda = new genai.BedrockDataAutomation(this, 'bdaap', {
      isCustomBDABlueprintRequired: true,
      isBDAProjectRequired: true,
      isBDAInvocationRequired: true,
      isStatusRequired: true,
    });
 
    new cdk.CfnOutput(this, 'inputbucketname', { value: bda.inputBucket.bucketName });
    new cdk.CfnOutput(this, 'outputbucketname', { value: bda.outputBucket.bucketName });



    // create BDA blueprint
    const bdaProjectLambdaFunction = bda.bdaProjectLambdaFunction
    
    
    new ApiGatewayToLambda(this, 'ApiGatewayToLambdaPattern', {
      existingLambdaObj:bdaProjectLambdaFunction,
      apiGatewayProps:{
        restApiName: 'createBdaProject',
      }
    });


    // create BDA blueprint
    const blueprintFunction = bda.blueprintLambdaFunction
    
    new ApiGatewayToLambda(this, 'blueprintFunction', {
      existingLambdaObj:blueprintFunction,
      apiGatewayProps:{
        restApiName: 'createBluePrint',
      }
    });

    // create BDA blueprint
    const bdainvocation = bda.bdaInvocationLambdaFunction
    
    new ApiGatewayToLambda(this, 'bdainvocation', {
      existingLambdaObj:bdainvocation,
      apiGatewayProps:{
        restApiName: 'invokeDataProcessing',
      }
    });

    // create BDA blueprint
    const bdaResult = bda.bdaResultStatuLambdaFunction
    
    new ApiGatewayToLambda(this, 'bdaResult', {
      existingLambdaObj:bdaResult,
      apiGatewayProps:{
        restApiName: 'getResultStatus',
      }
    });

  }
}