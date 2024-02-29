#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { BaseStackStack } from '../lib/base-stack-stack';

const app = new cdk.App();
new BaseStackStack(app, 'BaseStackStack');
