#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { GenerateContentStack } from '../lib/content-generation-stack';
import { NagSuppressions, AwsSolutionsChecks } from 'cdk-nag';


const env = {
  region: process.env.CDK_DEFAULT_REGION,
  account: process.env.CDK_DEFAULT_ACCOUNT,
  natGateways: 1,
  clientUrl: process.env.STREAMLIT_CLIENTURL? process.env.STREAMLIT_CLIENTURL : "http://localhost:8501/"
}


const app = new cdk.App();

new GenerateContentStack(app, 'GenerateContentStack', {
  natGateways: 1,
  clientUrl:env.clientUrl,
  //description: '(uksb-1tupboc43) (tag: Image generation stack)',
env: { account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION },
  /* If you don't specify 'env', this stack will be environment-agnostic.
   * Account/Region-dependent features and context lookups will not work,
   * but a single synthesized template can be deployed anywhere. */

  /* Uncomment the next line to specialize this stack for the AWS Account
   * and Region that are implied by the current CLI configuration. */
   

  /* Uncomment the next line if you know exactly what Account and Region you
   * want to deploy the stack to. */
  // env: { account: '123456789012', region: 'us-east-1' },

  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
});
