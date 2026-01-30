#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AgentCoreDemoStack } from '../lib/agentcore-demo-stack';

const app = new cdk.App();

new AgentCoreDemoStack(app, 'AgentCoreDemoStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ,
  },
  description: 'Amazon Bedrock AgentCore Demo - Research Assistant showcasing L2 Constructs',
});

