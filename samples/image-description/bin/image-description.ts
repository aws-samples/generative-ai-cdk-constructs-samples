#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { AwsSolutionsChecks } from "cdk-nag";
import { ImageDescriptionStack } from "../lib/image-description-stack";

const app = new cdk.App();
cdk.Tags.of(app).add("app", "generative-ai-cdk-constructs-samples");
cdk.Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));

const imageDescStack = new ImageDescriptionStack(app, "ImageDescStack-New", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
