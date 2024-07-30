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
import { Aws, Stack, StackProps, Tags, aws_elasticache } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { NagSuppressions } from 'cdk-nag'

import * as path from 'path';

import * as iam from 'aws-cdk-lib/aws-iam';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as appsync from 'aws-cdk-lib/aws-appsync';
import * as opensearchservice from 'aws-cdk-lib/aws-opensearchservice';
import * as openSearchServerless from 'aws-cdk-lib/aws-opensearchserverless';

import * as emergingTech from '@cdklabs/generative-ai-cdk-constructs';

//-----------------------------------------------------------------------------
// Stack Properties
//-----------------------------------------------------------------------------
export interface ApiProps extends StackProps {
  existingOpensearchDomain?: opensearchservice.IDomain;
  existingOpensearchServerlessCollection?: openSearchServerless.CfnCollection;
  existingVpc: ec2.IVpc;
  existingSecurityGroup: ec2.SecurityGroup;
  existingInputAssetsBucketObj: s3.IBucket;
  existingProcessedAssetsBucketObj: s3.IBucket;
  openSearchIndexName: string;
  cacheNodeType: string;
  engine: string;
  numCacheNodes: number;
  removalPolicy: cdk.RemovalPolicy;
  clientUrl: string;
}

export class ApiStack extends Stack {
  public readonly cognitoPool: cognito.UserPool;
  public readonly cognitoClient: cognito.UserPoolClient;
  public readonly userPoolDomain: cognito.UserPoolDomain;
  public readonly mergedApi: appsync.CfnGraphQLApi;
  public readonly identityPool: cognito.CfnIdentityPool;
  public readonly authenticatedRole: iam.Role;

  constructor(scope: Construct, id: string, props: ApiProps) {
    super(scope, id, props);

    //---------------------------------------------------------------------
    // Cognito User Pool and Client
    //---------------------------------------------------------------------
    this.cognitoPool = new cognito.UserPool(this, 'CognitoPool', {
      selfSignUpEnabled: true,
      autoVerify: { email: true },
      signInAliases: { email: true },
      removalPolicy: props.removalPolicy,
      advancedSecurityMode: cognito.AdvancedSecurityMode.ENFORCED,
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
        tempPasswordValidity: cdk.Duration.days(3),
      }
    });
    NagSuppressions.addResourceSuppressions(this.cognitoPool, [
      {id: 'AwsSolutions-COG2', reason: 'An MFA is not required to create a sample UserPool.'},
    ])


      const uniqueStackIdPart = cdk.Fn.select(2, cdk.Fn.split('/', `${cdk.Aws.STACK_ID}`));
      this.userPoolDomain = this.cognitoPool.addDomain('CognitoUserPoolDomain', {
      cognitoDomain: {
        domainPrefix: uniqueStackIdPart,
      },
    });
    
    this.cognitoClient = this.cognitoPool.addClient('CognitoClient', {
      generateSecret: true,
      oAuth: {
        callbackUrls: [props.clientUrl],
        logoutUrls: [props.clientUrl]
      },
    });

    this.identityPool = new cognito.CfnIdentityPool(this, 'IdentityPool', {
      allowUnauthenticatedIdentities: false,
      cognitoIdentityProviders: [{
        clientId: this.cognitoClient.userPoolClientId,
        providerName: this.cognitoPool.userPoolProviderName,
      }]
    });

    //---------------------------------------------------------------------
    // IAM Roles
    //---------------------------------------------------------------------
    this.authenticatedRole = new iam.Role(this, 'CognitoAuthenticatedRole', {
      assumedBy: new iam.FederatedPrincipal(
        'cognito-identity.amazonaws.com',
        {
          StringEquals: { 'cognito-identity.amazonaws.com:aud': this.identityPool.ref },
          'ForAnyValue:StringLike': { 'cognito-identity.amazonaws.com:amr': 'authenticated' },
        },
        'sts:AssumeRoleWithWebIdentity',
      ),
    });
    props.existingInputAssetsBucketObj.grantReadWrite(this.authenticatedRole);
    props.existingProcessedAssetsBucketObj.grantRead(this.authenticatedRole);
    new cognito.CfnIdentityPoolRoleAttachment(this, 'IdentityPoolRoleAttachment', {
      identityPoolId: this.identityPool.ref,
      roles: {
        'authenticated': this.authenticatedRole.roleArn
      }
    });
    NagSuppressions.addResourceSuppressions(this.authenticatedRole, [{id: 'AwsSolutions-IAM5', reason: '* bucket ARN prefix'}], true)

    const mergedApiRole = new iam.Role(this, 'mergedApiRole', {
      assumedBy:new iam.ServicePrincipal('appsync.amazonaws.com')
    });

    const appsynccloudWatchlogsRole = new iam.Role(this, 'appsynccloudWatchlogsRole', {
      assumedBy: new iam.ServicePrincipal('appsync.amazonaws.com'),
    });

    appsynccloudWatchlogsRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
        resources: ["arn:aws:logs:"+Aws.REGION+":"+cdk.Stack.of(this).account+":*"],
      }),
    );
    NagSuppressions.addResourceSuppressions(appsynccloudWatchlogsRole, [{id: 'AwsSolutions-IAM5', reason: '* used after region:account prefix'}], true)

    //---------------------------------------------------------------------
    // AppSync Merged API
    //---------------------------------------------------------------------
    this.mergedApi = new appsync.CfnGraphQLApi(this, 'mergedApi', {
      apiType:'MERGED',
      name:'mergedApi',
      authenticationType:'AMAZON_COGNITO_USER_POOLS',
      userPoolConfig: {
        awsRegion: Aws.REGION,
        userPoolId: this.cognitoPool.userPoolId,
        defaultAction: 'ALLOW'
      },
      additionalAuthenticationProviders:[{
        authenticationType:'AWS_IAM'
      }],
      logConfig: {
        cloudWatchLogsRoleArn: appsynccloudWatchlogsRole.roleArn,
        fieldLogLevel: 'ALL',
        excludeVerboseContent: false,
      },
      xrayEnabled: true,
      mergedApiExecutionRoleArn:mergedApiRole.roleArn,
    });

    //-----------------------------------------------------------------------------
    // GenAI RAG Construct
    //-----------------------------------------------------------------------------
    // Construct
    const rag = new emergingTech.RagAppsyncStepfnOpensearch(this, 'JoyrideRag', {
      cognitoUserPool: this.cognitoPool,
      existingVpc: props.existingVpc,
      existingMergedApi: this.mergedApi,
      existingSecurityGroup: props.existingSecurityGroup,
      existingInputAssetsBucketObj: props.existingInputAssetsBucketObj,
      existingProcessedAssetsBucketObj: props.existingProcessedAssetsBucketObj,
      existingOpensearchDomain: props.existingOpensearchDomain,
      existingOpensearchServerlessCollection: props.existingOpensearchServerlessCollection,
      openSearchIndexName: props.openSearchIndexName,
      observability: true,
    });
    // Update Merged API Policy
    mergedApiRole.addToPrincipalPolicy(new iam.PolicyStatement({
      effect:iam.Effect.ALLOW,
      actions:['appsync:SourceGraphQL', 'appsync:StartSchemaMerge'],
      resources:[
        `${rag.graphqlApi.arn}/*`,
        `${rag.graphqlApi.arn}/sourceApiAssociations/*`,
        `${this.mergedApi.attrArn}/*`,
        `${this.mergedApi.attrArn}/sourceApiAssociations/*`,
      ]
    }));
    NagSuppressions.addResourceSuppressions(mergedApiRole, [{id: 'AwsSolutions-IAM5', reason: '* used after ARN prefix'}], true)

    // Add Source API
    const cfn_source_api_association_rag = new appsync.CfnSourceApiAssociation(this, "RagApiAssociation", {
      mergedApiIdentifier: this.mergedApi.attrApiId,
      sourceApiAssociationConfig: {mergeType:'AUTO_MERGE'},
      sourceApiIdentifier: rag.graphqlApi.apiId
    });
    // Add dependency
    cfn_source_api_association_rag.node.addDependency(this.mergedApi);
    cfn_source_api_association_rag.node.addDependency(rag.graphqlApi);

    //-----------------------------------------------------------------------------
    // GenAI Summarization Construct
    //-----------------------------------------------------------------------------
    // Construct
    const cfnCacheClusterProps: aws_elasticache.CfnCacheClusterProps = {
      cacheNodeType: props.cacheNodeType,
      engine: props.engine,
      numCacheNodes: props.numCacheNodes,
    };
    const summarization = new emergingTech.SummarizationAppsyncStepfn(this, 'JoyrideSummarization', {
      cognitoUserPool: this.cognitoPool,
      existingVpc: props.existingVpc,
      existingMergedApi: this.mergedApi,
      existingSecurityGroup: props.existingSecurityGroup,
      existingInputAssetsBucketObj: props.existingInputAssetsBucketObj,
      existingProcessedAssetsBucketObj: props.existingProcessedAssetsBucketObj,
      observability: true,
      isFileTransformationRequired: props.openSearchIndexName,
    });
    // Update Merged API Policy
    mergedApiRole.addToPrincipalPolicy(new iam.PolicyStatement({
      effect:iam.Effect.ALLOW,
      actions:['appsync:SourceGraphQL', 'appsync:StartSchemaMerge'],
      resources:[
        `${summarization.graphqlApi.arn}/*`,
        `${summarization.graphqlApi.arn}/sourceApiAssociations/*`,
        `${this.mergedApi.attrArn}/*`,
        `${this.mergedApi.attrArn}/sourceApiAssociations/*`,
      ]
    }));
    NagSuppressions.addResourceSuppressions(mergedApiRole, [{id: 'AwsSolutions-IAM5', reason: '* used after ARN prefix'}], true)

    // Add Source API
    const cfn_source_api_association_summarization = new appsync.CfnSourceApiAssociation(this, "SummarizationApiAssociation", {
      mergedApiIdentifier: this.mergedApi.attrApiId,
      sourceApiAssociationConfig: {mergeType:'AUTO_MERGE'},
      sourceApiIdentifier: summarization.graphqlApi.apiId
    });
    // Add dependency
    cfn_source_api_association_summarization.node.addDependency(this.mergedApi);
    cfn_source_api_association_summarization.node.addDependency(summarization.graphqlApi);

    //-----------------------------------------------------------------------------
    // GenAI Q&A Construct
    //-----------------------------------------------------------------------------
    // Construct
    const qa = new emergingTech.QaAppsyncOpensearch(this, 'JoyrideQa', {
      cognitoUserPool: this.cognitoPool,
      existingVpc: props.existingVpc,
      existingMergedApi: this.mergedApi,
      existingSecurityGroup: props.existingSecurityGroup,
      existingInputAssetsBucketObj: props.existingProcessedAssetsBucketObj,
      existingOpensearchDomain: props.existingOpensearchDomain,
      existingOpensearchServerlessCollection: props.existingOpensearchServerlessCollection,
      openSearchIndexName: props.openSearchIndexName,
      observability: true,
      customDockerLambdaProps: {
        code: lambda.DockerImageCode.fromImageAsset(path.join(
          __dirname,
          'lambda',
          'aws-qa-appsync-opensearch-custom',
          'question_answering',
          'src'
        ))
      }
    });
    // Update Merged API Policy
    mergedApiRole.addToPrincipalPolicy(new iam.PolicyStatement({
      effect:iam.Effect.ALLOW,
      actions:['appsync:SourceGraphQL', 'appsync:StartSchemaMerge'],
      resources:[
        `${qa.graphqlApi.arn}/*`,
        `${qa.graphqlApi.arn}/sourceApiAssociations/*`,
        `${this.mergedApi.attrArn}/*`,
        `${this.mergedApi.attrArn}/sourceApiAssociations/*`,
      ]
    }));
    NagSuppressions.addResourceSuppressions(mergedApiRole, [{id: 'AwsSolutions-IAM5', reason: '* used after ARN prefix'}], true)

    // Add Source API
    const cfn_source_api_association_qa = new appsync.CfnSourceApiAssociation(this, "QaApiAssociation", {
      mergedApiIdentifier: this.mergedApi.attrApiId,
      sourceApiAssociationConfig: {mergeType:'AUTO_MERGE'},
      sourceApiIdentifier: qa.graphqlApi.apiId
    });
    // Add dependency
    cfn_source_api_association_qa.node.addDependency(this.mergedApi);
    cfn_source_api_association_qa.node.addDependency(qa.graphqlApi);


     //-----------------------------------------------------------------------------
    // Suppress cdk-nag warnings for Generative AI CDK Constructs
    // Reference: https://github.com/cdklabs/cdk-nag/blob/main/RULES.md
    //-----------------------------------------------------------------------------
    NagSuppressions.addResourceSuppressions([rag, summarization, qa], [
      {id: 'AwsSolutions-IAM4', reason: 'AWS managed policies defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-IAM5', reason: 'Wildcard permissions defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-S1', reason: 'S3 access logs defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-S10', reason: 'S3 bucket policy defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-SQS3', reason: 'SQS DLQ property defined in @cdklabs/generative-ai-cdk-constructs'},
    ], true)


    //---------------------------------------------------------------------
    // Export values
    //---------------------------------------------------------------------
    new cdk.CfnOutput(this, 'Region', {
      value: Aws.REGION
    });

    new cdk.CfnOutput(this, "UserPoolId", {
      value: this.cognitoPool.userPoolId,
    });

    new cdk.CfnOutput(this, "CognitoDomain", {
      value: "https://"+this.userPoolDomain.domainName+".auth."+Aws.REGION+".amazoncognito.com",
    });

    new cdk.CfnOutput(this, "ClientId", {
      value: this.cognitoClient.userPoolClientId, 
    });

    new cdk.CfnOutput(this, "AppUri", {
      value: props.clientUrl,
    });

    new cdk.CfnOutput(this, "IdentityPoolId", {
      value: this.identityPool.ref, 
    });

    new cdk.CfnOutput(this, "AuthenticatedRoleArn", {
      value: this.authenticatedRole.roleArn, 
    });
    
    new cdk.CfnOutput(this, "MergedApiId", {
      value: this.mergedApi.attrApiId,
    });

    new cdk.CfnOutput(this, "GraphQLEndpoint", {
      value: this.mergedApi.attrGraphQlUrl,
    });

  
  }
}
