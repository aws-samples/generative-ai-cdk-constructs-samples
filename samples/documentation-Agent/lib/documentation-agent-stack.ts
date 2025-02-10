import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as fs from 'fs';
import * as path from 'path';
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';


export class DocumentationAgentStack extends cdk.Stack {
  
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

     const key=  '(uksb-1tupboc43)'
     const tag = ' Document Agent'
     
     // Read instruction from file
     const instructionPath = path.join(__dirname, '..', 'instructions', 'readme-instructions.txt');
     const instruction = fs.readFileSync(instructionPath, 'utf-8');
 

     // print instruction
     new cdk.CfnOutput(this, 'Instruction', {
      value: instruction,
      description: 'Instruction for the agent'
    });
    
    const agent = new bedrock.Agent(this, 'documentationAgent', {
      foundationModel: bedrock.BedrockFoundationModel.AMAZON_NOVA_MICRO_V1,
      instruction: instruction,
      enableUserInput: true,
      shouldPrepareAgent:true
    });
    
     this.templateOptions.description = `Description: ${key}  (tag:${ tag}) `
  }
}
