import * as cdk from 'aws-cdk-lib';
import { Aws, Stack, StackProps, Tags, aws_elasticache } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as genai from '@cdklabs/generative-ai-cdk-constructs';
import { NagSuppressions, AwsSolutionsChecks } from 'cdk-nag';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as appsync from 'aws-cdk-lib/aws-appsync';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as logs from 'aws-cdk-lib/aws-logs';

// import * as sqs from 'aws-cdk-lib/aws-sqs';

export class GenerateContentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

 const env = {
      region: process.env.CDK_DEFAULT_REGION,
      account: process.env.CDK_DEFAULT_ACCOUNT,
      natGateways: 1,
      clientUrl: process.env.STREAMLIT_CLIENTURL? process.env.STREAMLIT_CLIENTURL : "http://localhost:8501/"
  }
  
  
  const app = new cdk.App();
  cdk.Tags.of(app).add("app", "generative-ai-cdk-constructs-samples");
  cdk.Aspects.of(app).add(new AwsSolutionsChecks({verbose:true}));
  
  //---------------------------------------------------------------------
        // VPC
  //---------------------------------------------------------------------
        const vpc = new ec2.Vpc(this, 'VPC', {
          subnetConfiguration: [
          {
              name: 'public',
              subnetType: ec2.SubnetType.PUBLIC,
              cidrMask: 24,
              mapPublicIpOnLaunch: false,
          },
          {
              name: 'private',
              subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
              cidrMask: 24
          },
          {
              name: 'isolated',
              subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
              cidrMask: 24,
          },
          ],
          ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
          natGateways: env.natGateways,
      });

      //---------------------------------------------------------------------
      // VPC Flow Logs
      //---------------------------------------------------------------------
      const logGroup = new logs.LogGroup(this, 'VPCFlowLogsLogGroup');
      const vpcFlowLogrole = new iam.Role(this, 'VPCFlowLogsRole', {
      assumedBy: new iam.ServicePrincipal('vpc-flow-logs.amazonaws.com'),
      });
      new ec2.FlowLog(this, 'FlowLog', {
          resourceType: ec2.FlowLogResourceType.fromVpc(vpc),
          destination: ec2.FlowLogDestination.toCloudWatchLogs(logGroup, vpcFlowLogrole),
      });

      //---------------------------------------------------------------------
      // Gateway VPC endpoint for S3
      //---------------------------------------------------------------------
      vpc.addGatewayEndpoint("S3GatewayEndpoint", {service: ec2.GatewayVpcEndpointAwsService.S3});

      //---------------------------------------------------------------------
        // Security Group
        //---------------------------------------------------------------------
        const securityGroups = [
          new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
          vpc: vpc,
          allowAllOutbound: true,
          description: 'security group for lambda',
          securityGroupName: 'lambdaSecurityGroup',
          }),
      ];
      securityGroups[0].addIngressRule(securityGroups[0], ec2.Port.tcp(443), 'allow https within sg');


  //---------------------------------------------------------------------
    // S3 - Input Generated Logs
    //---------------------------------------------------------------------
    const accessLogsBucket = new s3.Bucket(this, 'AccessLogs', {
      enforceSSL: true,
      versioned: true,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY 
    });
    NagSuppressions.addResourceSuppressions(accessLogsBucket, [
      {id: 'AwsSolutions-S1', reason: 'There is no need to enable access logging for the AccessLogs bucket.'},
    ]);

      //---------------------------------------------------------------------
    // S3 - Generated Assets
    //---------------------------------------------------------------------
    const generatedAssetsBucket = new s3.Bucket(this, 'GeneratedAssets', {
      enforceSSL: true,
      versioned: true,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY ,
      serverAccessLogsBucket: accessLogsBucket,
      serverAccessLogsPrefix: 'generatedAssetsBucketLogs/',
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
          allowedOrigins: [
            'http://localhost:5173'
          ],
          allowedHeaders: ['*'],
          exposedHeaders: ['Access-Control-Allow-Origin'],
        }
      ]
    });
  //---------------------------------------------------------------------
    // Cognito User Pool and Client
    //---------------------------------------------------------------------
    const cognitoPool = new cognito.UserPool(this, 'CognitoPool', {
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
    NagSuppressions.addResourceSuppressions(cognitoPool, [
      {id: 'AwsSolutions-COG2', reason: 'An MFA is not required to create a sample UserPool.'},
    ])


      const uniqueStackIdPart = cdk.Fn.select(2, cdk.Fn.split('/', `${cdk.Aws.STACK_ID}`));
      const userPoolDomain = cognitoPool.addDomain('CognitoUserPoolDomain', {
      cognitoDomain: {
        domainPrefix: uniqueStackIdPart,
      },
    });
    
    const cognitoClient = cognitoPool.addClient('CognitoClient', {
      generateSecret: true,
      oAuth: {
        callbackUrls: [env.clientUrl],
        logoutUrls: [env.clientUrl]
      },
    });

    const identityPool = new cognito.CfnIdentityPool(this, 'IdentityPool', {
      allowUnauthenticatedIdentities: false,
      cognitoIdentityProviders: [{
        clientId: cognitoClient.userPoolClientId,
        providerName: cognitoPool.userPoolProviderName,
      }]
    });

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

    //---------------------------------------------------------------------
    // AppSync Merged API
    //---------------------------------------------------------------------
    const mergedApi = new appsync.CfnGraphQLApi(this, 'mergedApi', {
      apiType:'MERGED',
      name:'mergedApi',
      authenticationType:'AMAZON_COGNITO_USER_POOLS',
      userPoolConfig: {
        awsRegion: Aws.REGION,
        userPoolId: cognitoPool.userPoolId,
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
    // GenAI IMAGE GENERATION Construct
    //-----------------------------------------------------------------------------
    // Construct
    const imageGeneration = new genai.ContentGenerationAppsyncLambda(this, 'JoyrideImageGeneration', {
      cognitoUserPool: cognitoPool,
      existingVpc: vpc,
      existingMergedApi: mergedApi,
      existingSecurityGroup: securityGroups[0],
      existingGeneratedAssetsBucketObj: generatedAssetsBucket,
      observability: true,
    });
    // Update Merged API Policy
    mergedApiRole.addToPrincipalPolicy(new iam.PolicyStatement({
      effect:iam.Effect.ALLOW,
      actions:['appsync:SourceGraphQL', 'appsync:StartSchemaMerge'],
      resources:[
        `${imageGeneration.graphqlApi.arn}/*`,
        `${imageGeneration.graphqlApi.arn}/sourceApiAssociations/*`,
        `${mergedApi.attrArn}/*`,
        `${mergedApi.attrArn}/sourceApiAssociations/*`,
      ]
    }));
    NagSuppressions.addResourceSuppressions(mergedApiRole, [{id: 'AwsSolutions-IAM5', reason: '* used after ARN prefix'}], true)

    // Add Source API
    const cfn_source_api_association_imagegen = new appsync.CfnSourceApiAssociation(this, "ImgGenApiAssociation", {
      mergedApiIdentifier: mergedApi.attrApiId,
      sourceApiAssociationConfig: {mergeType:'AUTO_MERGE'},
      sourceApiIdentifier: imageGeneration.graphqlApi.apiId
    });
    // Add dependency
    cfn_source_api_association_imagegen.node.addDependency(mergedApi);
    cfn_source_api_association_imagegen.node.addDependency(imageGeneration.graphqlApi);
    
     //-----------------------------------------------------------------------------
    // Suppress cdk-nag warnings for Generative AI CDK Constructs
    // Reference: https://github.com/cdklabs/cdk-nag/blob/main/RULES.md
    //-----------------------------------------------------------------------------
    NagSuppressions.addResourceSuppressions([imageGeneration], [
      {id: 'AwsSolutions-IAM4', reason: 'AWS managed policies defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-IAM5', reason: 'Wildcard permissions defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-S1', reason: 'S3 access logs defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-S10', reason: 'S3 bucket policy defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-SQS3', reason: 'SQS DLQ property defined in @cdklabs/generative-ai-cdk-constructs'},
    ], true)


    // The code that defines your stack goes here

    // example resource
    // const queue = new sqs.Queue(this, 'GenerateContentQueue', {
    //   visibilityTimeout: cdk.Duration.seconds(300)
    // });
  }
}
