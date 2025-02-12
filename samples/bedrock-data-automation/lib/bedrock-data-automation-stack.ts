import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as events from 'aws-cdk-lib/aws-events';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { EventbridgeToLambda } from '@aws-solutions-constructs/aws-eventbridge-lambda';
import * as genai from '@cdklabs/generative-ai-cdk-constructs';

export class BedrockDataAutomationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    
    const bda = new genai.BedrockDataAutomation(this, 'cb', {
      isCustomBDABlueprintRequired: true,
      isBDAProjectRequired: true,
      isBDAInvocationRequired: true,
      isStatusRequired: true,
    });
 
    new cdk.CfnOutput(this, 'inputbucketname', { value: bda.inputBucket.bucketName });
    new cdk.CfnOutput(this, 'outputbucketname', { value: bda.outputBucket.bucketName });


    const bdaProjectFunctio = bda.bdaProjectLambdaFunction

    // create BDA blueprint
    const bluePrintFunction = bda.blueprintLambdaFunction
    const blueprintEventbridge = new EventbridgeToLambda(this, 'CreateBlueprintEventRule', {
      existingLambdaObj: bluePrintFunction,
      eventRuleProps: {
        eventPattern: {
          source: ['custom.bedrock.blueprint'],
          detailType: ['Bedrock Blueprint Request'],
        }
      },
    });

  

//  Invoke Data processing
const invokeFunction = bda.bdaInvocationLambdaFunction

const invokeEventbridge = new EventbridgeToLambda(this, 'InvokeEventRule', {
  existingLambdaObj: invokeFunction, // Your existing Lambda function
  eventRuleProps: {
    eventPattern: {
      source: ['custom.bedrock.blueprint'],
      detailType: ['Bedrock Invoke Request'],
      
    }
  },

});

const bdaProjectFunction = bda.bdaProjectLambdaFunction

const bdaProjectEvent =  new EventbridgeToLambda(this, 'bdaProjectRule', {
  existingLambdaObj: bdaProjectFunction, 
  eventRuleProps: {
    eventPattern: {
      source: ['custom.bedrock.blueprint'],
      detailType: ['Bedrock Project Request'],
      
    }
  },

  

}); 


const bdaResultStatusFunction = bda.bdaResultStatuLambdaFunction

const bdaResultEvent =  new EventbridgeToLambda(this, 'bdaResultRule', {
  existingLambdaObj: bdaResultStatusFunction, 
  eventRuleProps: {
    eventPattern: {
      source: ['custom.bedrock.blueprint'],
      detailType: ['Bedrock Result Status'],
      
    }
  },
  

}); 

  }
}


// Example event structure
// const event = {
//   detail: {
//     input_file_name: "your-input-file.txt"
//   },
//   detail-type: "FileProcessingEvent",
//   source: "custom.fileprocessing"
// }
