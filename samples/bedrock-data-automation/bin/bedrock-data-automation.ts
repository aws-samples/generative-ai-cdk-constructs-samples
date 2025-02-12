#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { BedrockDataAutomationStack } from '../lib/bedrock-data-automation-stack';
import { BedrockDataAutomationAPIStack } from '../lib/bedrock-data-automation-stack-apigw'; 

const app = new cdk.App();
new BedrockDataAutomationStack(app, 'BDAStack', {
  env: {
    region: 'us-west-2', 
    account: process.env.CDK_DEFAULT_ACCOUNT,
  },

  // Add custom synthesizer configuration, this is for custom cdkbootstrap with cdktoolkit-staging bucket
  // this is just for us-west-2, bootstrap again with deafult cdk bucket
  synthesizer: new cdk.DefaultStackSynthesizer({
    fileAssetsBucketName: 'cdktoolkit-staging', // Replace with your actual bucket name prefix
  }),
  /* If you don't specify 'env', this stack will be environment-agnostic.
   * Account/Region-dependent features and context lookups will not work,
   * but a single synthesized template can be deployed anywhere. */

  /* Uncomment the next line to specialize this stack for the AWS Account
   * and Region that are implied by the current CLI configuration. */
  // env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION },

  /* Uncomment the next line if you know exactly what Account and Region you
   * want to deploy the stack to. */
  // env: { account: '123456789012', region: 'us-east-1' },

  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
});

new BedrockDataAutomationAPIStack(app, 'BDAAPIStack', {
  env: {
    region: 'us-west-2', 
    account: process.env.CDK_DEFAULT_ACCOUNT,
  },

  synthesizer: new cdk.DefaultStackSynthesizer({
    fileAssetsBucketName: 'cdktoolkit-staging', // Replace with your actual bucket name prefix
  }),
  });