#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SagemakerHuggingfaceModelSvdStack } from '../lib/sagemaker_huggingface_model_svd-stack';
import {AwsSolutionsChecks} from "cdk-nag";

const app = new cdk.App();


cdk.Tags.of(app).add("app", "generative-ai-cdk-constructs-samples");
cdk.Aspects.of(app).add(new AwsSolutionsChecks({verbose: true}));
new SagemakerHuggingfaceModelSvdStack(app, 'SagemakerHuggingfaceModelSvdStack', {
});