#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ImageDescriptionStack } from '../lib/image-description-stack';
const app = new cdk.App();
new ImageDescriptionStack(app, 'ImageDescStack', {
 
   env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION },

  });