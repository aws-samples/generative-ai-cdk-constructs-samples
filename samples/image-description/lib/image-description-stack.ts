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

import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as emergingTech from "@cdklabs/generative-ai-cdk-constructs";
import * as cognito from "aws-cdk-lib/aws-cognito";
import { NagSuppressions } from "cdk-nag";
import * as iam from "aws-cdk-lib/aws-iam";

export class ImageDescriptionStack extends cdk.Stack {
  /**
   * Cognito pool of image description stack
   */
  public readonly cognitoPool: cognito.UserPool;
  /**
   * Cognito client of image description stack
   */
  public readonly cognitoClient: cognito.UserPoolClient;
  /**
   * User pool domain of image description stack
   */
  public readonly userPoolDomain: cognito.UserPoolDomain;
  /**
   * Identity pool of image description stack
   */
  public readonly identityPool: cognito.CfnIdentityPool;
  /**
   * Authenticated role of image description stack
   */
  public readonly authenticatedRole: iam.Role;
  /**
   * Client url of image description stack
   */
  public readonly clientUrl = "http://localhost:8501/";

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id);

    //---------------------------------------------------------------------
    // Cognito User Pool and Client
    //---------------------------------------------------------------------
    this.cognitoPool = new cognito.UserPool(this, "CognitoPool", {
      selfSignUpEnabled: true,
      autoVerify: { email: true },
      signInAliases: { email: true },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      advancedSecurityMode: cognito.AdvancedSecurityMode.ENFORCED,
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
        tempPasswordValidity: cdk.Duration.days(3),
      },
    });

    // Add unique value to for each account / environment.
    const stage = "-DEV";

    const uniqueStackIdPart = cdk.Fn.select(
      2,
      cdk.Fn.split("/", `${cdk.Aws.STACK_ID}`)
    );

    this.userPoolDomain = this.cognitoPool.addDomain("CognitoUserPoolDomain", {
      cognitoDomain: {
        domainPrefix: uniqueStackIdPart,
      },
    });

    this.cognitoClient = this.cognitoPool.addClient("CognitoClient", {
      generateSecret: true,
      oAuth: {
        callbackUrls: [this.clientUrl],
        logoutUrls: [this.clientUrl],
      },
    });

    this.identityPool = new cognito.CfnIdentityPool(this, "IdentityPool", {
      allowUnauthenticatedIdentities: false,
      cognitoIdentityProviders: [
        {
          clientId: this.cognitoClient.userPoolClientId,
          providerName: this.cognitoPool.userPoolProviderName,
        },
      ],
    });

    //---------------------------------------------------------------------
    // IAM Roles
    //---------------------------------------------------------------------
    const authenticatedRole = new iam.Role(this, "CognitoAuthenticatedRole", {
      assumedBy: new iam.FederatedPrincipal(
        "cognito-identity.amazonaws.com",
        {
          StringEquals: {
            "cognito-identity.amazonaws.com:aud": this.identityPool.ref,
          },
          "ForAnyValue:StringLike": {
            "cognito-identity.amazonaws.com:amr": "authenticated",
          },
        },
        "sts:AssumeRoleWithWebIdentity"
      ),
    });
    this.authenticatedRole = authenticatedRole;

    new cognito.CfnIdentityPoolRoleAttachment(
      this,
      "IdentityPoolRoleAttachment",
      {
        identityPoolId: this.identityPool.ref,
        roles: {
          authenticated: this.authenticatedRole.roleArn,
        },
      }
    );

    const summarization = new emergingTech.SummarizationAppsyncStepfn(
      this,
      "ImageSummarization",
      {
        cognitoUserPool: this.cognitoPool,
        observability: true,
        stage: stage,
        isFileTransformationRequired: "true",
      }
    );

    this.templateOptions.description =  "Description: (uksb-1tupboc43) (tag: Image Description sample)",

    summarization.inputAssetBucket.grantReadWrite(this.authenticatedRole);
    summarization.processedAssetBucket.grantRead(this.authenticatedRole);

    // print cdk outpout
    new cdk.CfnOutput(this, "UserPoolId", {
      value: this.cognitoPool.userPoolId,
    });

    new cdk.CfnOutput(this, "CognitoDomain", {
      value:
        "https://" +
        this.userPoolDomain.domainName +
        ".auth." +
        cdk.Aws.REGION +
        ".amazoncognito.com",
    });

    new cdk.CfnOutput(this, "ClientId", {
      value: this.cognitoClient.userPoolClientId,
    });

    new cdk.CfnOutput(this, "AppUri", {
      value: this.clientUrl,
    });

    new cdk.CfnOutput(this, "IdentityPoolId", {
      value: this.identityPool.ref,
    });

    new cdk.CfnOutput(this, "AuthenticatedRoleArn", {
      value: this.authenticatedRole.roleArn,
    });

    new cdk.CfnOutput(this, "GraphQLApiId", {
      value: summarization.graphqlApiId,
    });

    new cdk.CfnOutput(this, "GraphQLEndpoint", {
      value: summarization.graphqlUrl,
    });

    new cdk.CfnOutput(this, "S3InputBucket", {
      value: summarization.inputAssetBucket.bucketName,
    });

    new cdk.CfnOutput(this, "S3ProcessedBucket", {
      value: summarization.processedAssetBucket.bucketName,
    });
    
    new cdk.CfnOutput(this, "ClientSecret", {
      value: this.cognitoClient.userPoolClientSecret.unsafeUnwrap(),
    });

    // CDK- NAG suppressions
    NagSuppressions.addResourceSuppressions(
      this,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "ESLogGroupPolicy managed by aws-cdk.",
          appliesTo: [
            "Resource::*",
            "Resource::<ImageSummarizationprocessedAssetsSummaryBucketDEVAA9F30E3.Arn>/*",
            "Resource::<ImageSummarizationinputAssetsSummaryBucketDEV184F81EF.Arn>/*",
            "Resource::<ImageSummarizationsummarygeneratordevimagedesstackimagesummarizationb66b14bb0F1908FB.Arn>:*",
            "Resource::<ImageSummarizationinputValidatorLambdaDEV5B95C05A.Arn>:*",
            "Resource::<ImageSummarizationdocumentReaderLambdaDEV8B4FAE2D.Arn>:*",
          ],
        },
        {
          id: "AwsSolutions-IAM5",
          reason: "s3 action managed by generative-ai-cdk-constructs.",
          appliesTo: [
            "Action::s3:*",
            "Action::s3:Abort*",
            "Action::s3:DeleteObject*",
            "Action::s3:GetBucket*",
            "Action::s3:GetObject*",
            "Action::s3:List*",
          ],
        },
        {
          id: "AwsSolutions-IAM4",
          reason: "ServiceRole managed by aws-cdk.",
          appliesTo: [
            "Policy::arn:<AWS::Partition>:iam::aws:policy/Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSAppSyncPushToCloudWatchLogs-role/AWSLambdaBasicExecutionRole",
            "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSAppSyncPushToCloudWatchLogs",
            "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
          ],
        },
        {
          id: "AwsSolutions-L1",
          reason: "Runtime managed by aws-cdk.",
        },
        {
          id: "AwsSolutions-SQS3",
          reason: "Queue managed by genertive ai cdk constructs.",
        },
      ],
      true
    );
  }
}
