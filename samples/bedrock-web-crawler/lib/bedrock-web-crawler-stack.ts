#!/usr/bin/env node
/**
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 *  with the License. A copy of the License is located at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 *  and limitations under the License.
 */
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as path from 'path';
import { WebCrawler, bedrock } from '@cdklabs/generative-ai-cdk-constructs';

export class BedrockWebCrawlerStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const crawler = new WebCrawler(this, 'WebCrawler', {
      enableLambdaCrawler: true,
    });

    const agent = new bedrock.Agent(this, 'WebAgent', {
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_SONNET_V1_0,
      instruction: `You are a helpful and friendly agent with access to the internet. 
      You can get content from web pages provided by an URL. 
      You can summarize web pages.`,
      shouldPrepareAgent:true
    });

    const actionGroup = new bedrock.AgentActionGroup(this,'WebCrawlerActionGroup',{
      actionGroupName: 'web-crawler',
      description: 'Use this function to get content from a web page by HTTP or HTTPS URL',
      actionGroupExecutor: {
        lambda: crawler.lambdaCrawler
      },
      actionGroupState: "ENABLED",
      apiSchema: bedrock.ApiSchema.fromAsset(path.join(__dirname, 'action-group.yaml')),
    });

    agent.addActionGroups([actionGroup]);
  }
}
