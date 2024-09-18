import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as emergingTech from "@cdklabs/generative-ai-cdk-constructs";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as rds from "aws-cdk-lib/aws-rds";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { NagSuppressions } from "cdk-nag";

import {
  Effect,
  PolicyStatement,
  Role,
  ServicePrincipal,
} from "aws-cdk-lib/aws-iam";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as path from "path";
import { Aws } from "aws-cdk-lib";

export class TextToSqlStack extends cdk.Stack {
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
    super(scope, id, props);

    const stage = "-QA";
    const uniqueStackIdPart = cdk.Fn.select(
      2,
      cdk.Fn.split("/", `${cdk.Aws.STACK_ID}`)
    );

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

    const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(
      this,
      "CognitoAuthorizer",
      {
        cognitoUserPools: [this.cognitoPool],
        authorizerName: "CognitoAuthorizer",
      }
    );

    const secret = this.createSecret(stage, "texttosqlacdbsecret");
    const secretCompleteArn = secret.secretFullArn;
    secret.addRotationSchedule("RotationSchedule", 
      {  hostedRotation: secretsmanager.HostedRotation.mysqlSingleUser(),
      });
    

    //---------------------------------------------------------------------
    // TEXT TO SQL construct
    //---------------------------------------------------------------------

    const textToSql = new emergingTech.TextToSql(this, "TextToSql1", {
      databaseSecretARN: secretCompleteArn ? secretCompleteArn : "",
      dbName: emergingTech.DbName.MYSQL,
      metadataSource: emergingTech.MetatdataSource.CONFIG_FILE,
      stage: stage,
    });

    this.createAuroraCluster(
      emergingTech.DbName.MYSQL,
      3306,
      textToSql.dbSecurityGroup,
      secret,
      textToSql.vpc,
      "Chinook"
    );

    const eventBus = textToSql.eventBus;

    textToSql.configAssetBucket.grantReadWrite(this.authenticatedRole);
    textToSql.configAssetBucket.grantRead(this.authenticatedRole);

    // Create IAM Policies & Roles
    const apiGwServiceRole = new Role(this, "ApiGWRole", {
      assumedBy: new ServicePrincipal("apigateway.amazonaws.com"),
    });

    apiGwServiceRole.addToPolicy(
      new PolicyStatement({
        effect: Effect.ALLOW,
        actions: ["events:PutEvents"],
        resources: [eventBus!.eventBusArn],
      })
    );

    //---------------------------------------------------------------------
    // REST API Gateway
    //---------------------------------------------------------------------
    const restApi = new apigateway.RestApi(this, "texttosqlconstructapi");

    const eventBridgeRestApiIntegration = new apigateway.AwsIntegration({
      action: "PutEvents",
      service: "events",
      options: {
        integrationResponses: [
          {
            statusCode: "200",
            responseTemplates: {
              "application/json": `
                #set($inputRoot = $input.path('$'))
                {
                  $util.escapeJavaScript($input.body)
                }
              `,
            },
          },
        ],
        credentialsRole: apiGwServiceRole,
        passthroughBehavior: apigateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
        requestTemplates: {
          "application/json": `
            #set($context.requestOverride.header.X-Amz-Target = "AWSEvents.PutEvents")
            #set($context.requestOverride.header.Content-Type = "application/x-amz-json-1.1")
            #set($inputRoot = $input.path('$'))
            {
              "Entries": [
                {
                  "Detail": "$util.escapeJavaScript($input.body)",
                  "DetailType": "POST-Request",
                  "EventBusArn": "${eventBus!.eventBusArn}",
                  "EventBusName": "${eventBus!.eventBusName}",
                  "Source": "webclient"
                }
              ]
            }
          `,
        },
      },
    });

    const apiResource = restApi.root.addResource("getsqlfromtext");

    apiResource.addMethod("POST", eventBridgeRestApiIntegration, {
      requestParameters: {
        "method.request.header.X-Amz-Target": false,
        "method.request.header.Content-Type": false,
      },
      methodResponses: [{ statusCode: "200" }],
      authorizationType: apigateway.AuthorizationType.COGNITO,
      authorizer: cognitoAuthorizer,
    });

    // Create an IAM role with permissions to publish messages to Step Functions
    const userFeedbackFunctionRole = new iam.Role(
      this,
      "userFeedbackFunctionRole",
      {
        assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
        inlinePolicies: {
          LambdaFunctionServiceRolePolicy: new iam.PolicyDocument({
            statements: [
              new iam.PolicyStatement({
                actions: [
                  "logs:CreateLogGroup",
                  "logs:CreateLogStream",
                  "logs:PutLogEvents",
                  "ec2:CreateNetworkInterface",
                  "ec2:DeleteNetworkInterface",
                  "ec2:AssignPrivateIpAddresses",
                  "ec2:UnassignPrivateIpAddresses",
                  "ec2:DescribeNetworkInterfaces",
                  "states:SendTaskSuccess",
                ],
                resources: [
                  `arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:/aws/lambda/*`,
                  textToSql.stepFunction!.stateMachineArn,
                  "*",
                ],
              }),
            ],
          }),
        },
      }
    );

    // Feed back lambda function
    const userFeedbackFunctionProps = {
      code: lambda.Code.fromAsset(path.join(__dirname, "../lambda")),
      handler: "send_feedback.handler",
      runtime: lambda.Runtime.PYTHON_3_9,
      vpc: textToSql.vpc,
      name: "userFeedbackFunction" + "_stage" + "_" + uniqueStackIdPart,
      timeout: cdk.Duration.seconds(30),
      memorySize: 1024,
      role: userFeedbackFunctionRole,
    };

    // Define the Python Lambda function
    const userFeedbackFunction = new lambda.Function(
      this,
      "PythonLambda",
      userFeedbackFunctionProps
    );

    // Add a new POST method to the existing feedbackAPIResource with Cognito authorization
    const feedbackAPIResource = restApi.root.addResource("getfeedback");
    feedbackAPIResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(userFeedbackFunction),
      {
        authorizationType: apigateway.AuthorizationType.COGNITO,
        authorizer: cognitoAuthorizer,
      }
    );

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

    new cdk.CfnOutput(this, "API_ENDPOINT", {
      value: restApi.url + "/getsqlfromtext",
    });
    new cdk.CfnOutput(this, "FEEDBACK_QUEUE", {
      value: textToSql.feedbackQueue.queueUrl,
    });
    new cdk.CfnOutput(this, "RESULT_QUEUE", {
      value: textToSql.outputQueue.queueUrl,
    });
    new cdk.CfnOutput(this, "FEEDBACK_ENDPOINT", {
      value: restApi.url + "/getfeedback",
    });
    new cdk.CfnOutput(this, "CONFIG_BUCKET", {
      value: textToSql.configAssetBucket.bucketName,
    });

    new cdk.CfnOutput(this, "SECURITY_GROUP", {
      value: textToSql.lambdaSecurityGroup.uniqueId,
    });

    new cdk.CfnOutput(this, "PUBLIC_SUBNET_ID", {
      value: textToSql.vpc.publicSubnets.at(0)?.subnetId || "",
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
              "Resource::<TextToSql1configassetQA2A0581E5.Arn>/*",
              "Resource::<TextToSql1queryExecutorFunctionNameQA74D84D0B.Arn>:*",
              "Resource::<TextToSql1queryGeneratorFunctionQA550773FE.Arn>:*",
              "Resource::<TextToSql1reformulateQuestionFunctionQA1B72EAFF.Arn>:*",
              "Resource::arn:<AWS::Partition>:bedrock:<AWS::Region>::foundation-model/*",
              "Resource::arn:<AWS::Partition>:logs:<AWS::Region>:<AWS::AccountId>:log-group:/aws/lambda/*",
              "Resource::arn:<AWS::Partition>:s3:::<TextToSql1configassetQA2A0581E5>/*",
              "Resource::<TextToSql1autocorrectQueryFunctionQA80F3055B.Arn>:*",
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
          {
            id: 'AwsSolutions-RDS6',
            reason: 'Using password authentication for sample db.',
          },
          {
            id: 'AwsSolutions-RDS10',
            reason: 'Using sample db which needs to be deleted.',
          },
          {
            id: 'AwsSolutions-RDS11',
            reason: 'Using sample db which needs to be deleted.',
          },
          {
            id: 'AwsSolutions-RDS14',
            reason: 'Using sample db which needs to be deleted.',
          },
          {
            id: 'AwsSolutions-APIG1',
            reason: 'Using sample api for the sample app.',
          },
          {
            id: 'AwsSolutions-APIG2',
            reason: 'Using sample api for the sample app.',
          },
          {
            id: 'AwsSolutions-APIG6',
            reason: 'Using sample api for the sample app.',
          },
        ],
        true
      );
  }

  //---------------------------------------------------------------------
  // Create Database secret
  //---------------------------------------------------------------------

  private createSecret(
    stage: string,
    secretName: string
  ): secretsmanager.Secret {
    return new secretsmanager.Secret(this, "dbsecret" + stage, {
      secretName: secretName,
      generateSecretString: {
        excludePunctuation: true,
        passwordLength: 16,
        secretStringTemplate: JSON.stringify({
          username: "admin",
        }),
        generateStringKey: "password",
      },
    });
  }

  //---------------------------------------------------------------------
  // Create Database
  //---------------------------------------------------------------------

  private createAuroraCluster(
    dbName: string,
    dbPort: number,
    dbSecurityGroup: ec2.SecurityGroup,
    secret: secretsmanager.Secret,
    vpc: ec2.IVpc,
    databaseName: string
  ): rds.DatabaseCluster {
    return new rds.DatabaseCluster(this, "AuroraCluster", {
      engine: rds.DatabaseClusterEngine.auroraMysql({
        version: rds.AuroraMysqlEngineVersion.VER_3_07_0,
      }),
      storageEncrypted:true,
      port: dbPort,
      credentials: rds.Credentials.fromSecret(secret),
      instanceProps: {
        vpc: vpc,
        vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        securityGroups: [dbSecurityGroup],
        instanceType: ec2.InstanceType.of(
          ec2.InstanceClass.BURSTABLE3,
          ec2.InstanceSize.MEDIUM
        ),
      },
      instances: 1,
      defaultDatabaseName: databaseName,
    });
  }

  
}
