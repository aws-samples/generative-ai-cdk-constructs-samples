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

export interface GenerateContentStackProps extends StackProps {
  natGateways: number;
  clientUrl: string;
}


export class GenerateContentStack extends cdk.Stack {
  public readonly cognitoPool: cognito.UserPool;
  public readonly cognitoClient: cognito.UserPoolClient;
  public readonly userPoolDomain: cognito.UserPoolDomain;
  public readonly identityPool: cognito.CfnIdentityPool;
  public readonly authenticatedRole: iam.Role;
  public readonly generatedAssetsBucket: s3.Bucket;
  public readonly privateSubnets: string[];

  constructor(scope: Construct, id: string, props: GenerateContentStackProps) {
    super(scope, id, props);
  
    const key=  '(uksb-1tupboc43)'
    const tag = ' Image generation stack'


    console.log(`Deploying to account ${this.account} in region ${this.region}`);

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
          natGateways: props.natGateways,
          
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
      vpc.addInterfaceEndpoint("comprehendInterfaceEndpoint",
        {service: ec2.InterfaceVpcEndpointAwsService.COMPREHEND,
          lookupSupportedAzs:true,
        subnets:{ subnetType: ec2.SubnetType.PRIVATE_ISOLATED}})
      vpc.addInterfaceEndpoint("bedrockInterfaceEndpoint",
        {service: ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME})
      // vpc.addInterfaceEndpoint("appsyncInterfaceEndpoint",
      //   {service: ec2.InterfaceVpcEndpointAwsService.APP_SYNC,
      //     privateDnsEnabled: true,
      //     subnets:{ subnetType: ec2.SubnetType.PRIVATE_ISOLATED}
          
      //   })
      vpc.addInterfaceEndpoint("rekogntionInterfaceEndpoint",
        {service: ec2.InterfaceVpcEndpointAwsService.REKOGNITION})
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
        // Private Subnets
        //---------------------------------------------------------------------
        this.privateSubnets = vpc.privateSubnets.map(subnet => subnet.subnetId);
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
    this.generatedAssetsBucket = new s3.Bucket(this, 'GeneratedAssets', {
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
   
    this.generatedAssetsBucket.grantRead(this.authenticatedRole);
    new cognito.CfnIdentityPoolRoleAttachment(this, 'IdentityPoolRoleAttachment', {
      identityPoolId: this.identityPool.ref,
      roles: {
        'authenticated': this.authenticatedRole.roleArn
      }
    });

   
    const grapdhQLApiRole = new iam.Role(this, 'grapdhQLApiRole', {
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

   



  //-----------------------------------------------------------------------------
    // GenAI IMAGE GENERATION Construct
    //-----------------------------------------------------------------------------
    // Construct
    const imageGeneration = new genai.ContentGenerationAppSyncLambda(this, 'ImageGeneration', {
      cognitoUserPool: this.cognitoPool,
      existingVpc: vpc,
      existingSecurityGroup: securityGroups[0],
      existingGeneratedAssetsBucketObj: this.generatedAssetsBucket,
      observability: true,
    });

    this.templateOptions.description = `Description: ${key}  (tag:${ tag}) `
  
   
    NagSuppressions.addResourceSuppressions(grapdhQLApiRole, [{id: 'AwsSolutions-IAM5', reason: '* used after ARN prefix'}], true)

    
    //-----------------------------------------------------------------------------
    // Suppress cdk-nag warnings for Generative AI CDK Constructs
    // Reference: https://github.com/cdklabs/cdk-nag/blob/main/RULES.md
    //-----------------------------------------------------------------------------
    NagSuppressions.addResourceSuppressions([imageGeneration,vpcFlowLogrole], [
      {id: 'AwsSolutions-IAM4', reason: 'AWS managed policies defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-IAM5', reason: 'Wildcard permissions defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-S1', reason: 'S3 access logs defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-S10', reason: 'S3 bucket policy defined in @cdklabs/generative-ai-cdk-constructs'},
      {id: 'AwsSolutions-SQS3', reason: 'SQS DLQ property defined in @cdklabs/generative-ai-cdk-constructs'},
    ], true)

    NagSuppressions.addResourceSuppressions(this.authenticatedRole, [{id: 'AwsSolutions-IAM5', reason: '* bucket ARN prefix'}], true)



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


    new cdk.CfnOutput(this, "generatedAssetsBucket", {
      value: this.generatedAssetsBucket.bucketName
    });

    new cdk.CfnOutput(this, "graphQLendpoint", {
      value: imageGeneration.graphqlApi.graphqlUrl,
    });

    new cdk.CfnOutput(this, "ClientSecret", {
      value: this.cognitoClient.userPoolClientSecret.unsafeUnwrap(),
    });
  }
}