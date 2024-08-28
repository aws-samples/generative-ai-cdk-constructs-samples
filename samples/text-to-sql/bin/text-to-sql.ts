#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { TextToSqlStack } from '../lib/text-to-sql-stack';
import { AwsSolutionsChecks } from "cdk-nag";

const app = new cdk.App();
cdk.Tags.of(app).add("app", "generative-ai-cdk-constructs-samples");
cdk.Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));

new TextToSqlStack(app, 'TextToSqlStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  description: "(uksb-1tupboc43) GenAI Text to SQL Stack",
 
});