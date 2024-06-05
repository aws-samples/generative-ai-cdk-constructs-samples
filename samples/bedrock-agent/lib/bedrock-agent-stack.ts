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
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lambda_python from '@aws-cdk/aws-lambda-python-alpha';
import * as s3 from 'aws-cdk-lib/aws-s3';
import {Construct} from 'constructs';

import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';
import {NagSuppressions} from "cdk-nag";
import * as path from "path";
import { AgentActionGroup } from '@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock';

export class BedrockAgentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const accesslogBucket = new s3.Bucket(this, 'AccessLogs', {
      enforceSSL: true,
      versioned: true,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });
    NagSuppressions.addResourceSuppressions(accesslogBucket, [
      {id: 'AwsSolutions-S1', reason: 'There is no need to enable access logging for the AccessLogs bucket.'},
    ])
    const docBucket = new s3.Bucket(this, 'DocBucket', {
      enforceSSL: true,
      versioned: true,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      serverAccessLogsBucket: accesslogBucket,
      serverAccessLogsPrefix: 'inputsAssetsBucketLogs/',
    });
    const kb = new bedrock.KnowledgeBase(this, 'KB', {
      embeddingsModel: bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V1,
      instruction: 'Use this knowledge base to answer questions about books. ' +
        'It contains the full text of novels. Please quote the books to explain your answers.',
    });

    const dataSource = new bedrock.S3DataSource(this, 'DataSource', {
      bucket: docBucket,
      knowledgeBase: kb,
      dataSourceName: 'books',
      chunkingStrategy: bedrock.ChunkingStrategy.FIXED_SIZE,
      maxTokens: 500,
      overlapPercentage: 20,
    });

    const agent = new bedrock.Agent(this, 'Agent', {
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_INSTANT_V1_2,
      instruction: 'You are a helpful and friendly agent that answers questions about literature.',
      knowledgeBases: [kb],
      enableUserInput: true,
      shouldPrepareAgent:true
    });

    const actionGroupFunction = new lambda_python.PythonFunction(this, 'ActionGroupFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      entry: path.join(__dirname, '../lambda/action-group'),
      layers: [lambda.LayerVersion.fromLayerVersionArn(this, 'PowerToolsLayer', `arn:aws:lambda:${this.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:60`)],
      timeout:cdk.Duration.minutes(2)
    });

    const actionGroup = new AgentActionGroup(this,'MyActionGroup',{
      actionGroupName: 'query-library',
      description: 'Use these functions to get information about the books in the library.',
      actionGroupExecutor: {
        lambda: actionGroupFunction
      },
      actionGroupState: "ENABLED",
      apiSchema: bedrock.ApiSchema.fromAsset(path.join(__dirname, 'action-group.yaml')),
    });

    agent.addActionGroups([actionGroup])

    agent.addAlias({
      aliasName: 'my-agent-alias',
      description:'alias for my agent'
      
    })
  
    new cdk.CfnOutput(this, 'AgentId', {value: agent.agentId});
    new cdk.CfnOutput(this, 'KnowledgeBaseId', {value: kb.knowledgeBaseId});
    new cdk.CfnOutput(this, 'DataSourceId', {value: dataSource.dataSourceId});
    new cdk.CfnOutput(this, 'DocumentBucket', {value: docBucket.bucketName});

    NagSuppressions.addResourceSuppressions(
      actionGroupFunction,
      [
        {
          id: 'AwsSolutions-IAM4',
          reason: 'ActionGroup Lambda uses the AWSLambdaBasicExecutionRole AWS Managed Policy.',
        }
      ],
      true,
    );
    NagSuppressions.addResourceSuppressionsByPath(
      this,
      `/${this.node.path}/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole`,
      [
        {
          id: 'AwsSolutions-IAM4',
          reason: 'CDK CustomResource LogRetention Lambda uses the AWSLambdaBasicExecutionRole AWS Managed Policy. Managed by CDK.',
        },
        {
          id: 'AwsSolutions-IAM5',
          reason: 'CDK CustomResource LogRetention Lambda uses a wildcard to manage log streams created at runtime. Managed by CDK.',
        },
      ],
      true,
    );
  }
}
