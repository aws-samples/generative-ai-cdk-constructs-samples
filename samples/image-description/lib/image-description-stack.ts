import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as emergingTech from '@cdklabs/generative-ai-cdk-constructs';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { NagSuppressions } from 'cdk-nag'
import * as appsync from 'aws-cdk-lib/aws-appsync';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';



export class ImageDescriptionStack extends cdk.Stack {
  
  public readonly cognitoPool: cognito.UserPool;
  public readonly cognitoClient: cognito.UserPoolClient;
  public readonly userPoolDomain: cognito.UserPoolDomain;
  public readonly identityPool: cognito.CfnIdentityPool;
  public readonly authenticatedRole: iam.Role;
  public readonly clientUrl = "http://localhost:8501/";


  constructor(scope: Construct, id: string,props?: cdk.StackProps) {
    super(scope, id);

     //---------------------------------------------------------------------
    // Cognito User Pool and Client
    //---------------------------------------------------------------------
    this.cognitoPool = new cognito.UserPool(this, 'CognitoPool', {
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
      }
    });

  
    const uniqueStackIdPart = cdk.Fn.select(2, cdk.Fn.split('/', `${cdk.Aws.STACK_ID}`));
     
    this.userPoolDomain = this.cognitoPool.addDomain('CognitoUserPoolDomain', {
      cognitoDomain: {
        domainPrefix: uniqueStackIdPart,
      },
    });
    
    this.cognitoClient = this.cognitoPool.addClient('CognitoClient', {
      generateSecret: true,
      oAuth: {
        callbackUrls: [this.clientUrl],
        logoutUrls: [this.clientUrl]
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
    


    new cognito.CfnIdentityPoolRoleAttachment(this, 'IdentityPoolRoleAttachment', {
      identityPoolId: this.identityPool.ref,
      roles: {
        'authenticated': this.authenticatedRole.roleArn
      }
    });

    // const graphQLApiRole = new iam.Role(this, 'graphQLApiRole', {
    //   assumedBy:new iam.ServicePrincipal('appsync.amazonaws.com')
    // });

    // const appsynccloudWatchlogsRole = new iam.Role(this, 'appsynccloudWatchlogsRole', {
    //   assumedBy: new iam.ServicePrincipal('appsync.amazonaws.com'),
    // });

    // appsynccloudWatchlogsRole.addToPolicy(
    //   new iam.PolicyStatement({
    //     effect: iam.Effect.ALLOW,
    //     actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
    //     resources: ["arn:aws:logs:"+cdk.Aws.REGION+":"+cdk.Stack.of(this).account+":*"],
    //   }),
    // );


    

    const summarization = new emergingTech.SummarizationAppsyncStepfn
    (this, 'ImageSummarization', {
      cognitoUserPool: this.cognitoPool,
      observability: true,
      stage:"test",
      isFileTransformationRequired: "true"
    });

     summarization.inputAssetBucket.grantReadWrite(this.authenticatedRole);
     summarization.processedAssetBucket.grantRead(this.authenticatedRole);
    


    new cdk.CfnOutput(this, "UserPoolId", {
      value: this.cognitoPool.userPoolId,
    });

    new cdk.CfnOutput(this, "CognitoDomain", {
      value: "https://"+this.userPoolDomain.domainName+".auth."+cdk.Aws.REGION+".amazoncognito.com",
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
      value: summarization.graphqlApiId
      ,
    });

    new cdk.CfnOutput(this, "GraphQLEndpoint", {
      value: summarization.graphqlUrl,
    });


    new cdk.CfnOutput(this, "S3InputBucket", {
      value: summarization.inputAssetBucket.bucketName 
    });

    new cdk.CfnOutput(this, "S3ProcessedBucket", {
      value: summarization.processedAssetBucket.bucketName
    });

  }

}
