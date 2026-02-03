import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as agentcore from '@aws-cdk/aws-bedrock-agentcore-alpha';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as path from 'path';

export class AgentCoreDemoStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ========================================
    // 1. MEMORY - Conversation Storage
    // ========================================
    const memory = new agentcore.Memory(this, 'ResearchAssistantMemory', {
      memoryName: 'research_assistant_memory',
      description: 'Short-term memory for AI Research Assistant chat conversations',
      // NO memoryStrategies = uses default STM 
    });

    // ========================================
    // 2. GATEWAY - External Tool Integration
    // ========================================
    const gateway = new agentcore.Gateway(this, 'ResearchAssistantGateway', {
      gatewayName: 'research-assistant-gateway',
      description: 'Gateway for Research Assistant external tools',
    });

    // ========================================
    // 3. GATEWAY TARGETS - Lambda Functions
    // ========================================
    // Weather tool Lambda function
    const weatherLambda = new lambda.Function(this, 'WeatherToolFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambda/weather-tool')),
      description: 'Weather tool for Research Assistant',
    });

    // Add Lambda as Gateway target
    const weatherTarget = gateway.addLambdaTarget('WeatherTarget', {
      gatewayTargetName: 'weather-tool',
      description: 'Weather information tool',
      lambdaFunction: weatherLambda,
      toolSchema: agentcore.ToolSchema.fromInline([
        {
          name: 'get_weather',
          description: 'Get current weather information for a specific location',
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              location: {
                type: agentcore.SchemaDefinitionType.STRING,
                description: 'The city and state, e.g., San Francisco, CA',
              },
              unit: {
                type: agentcore.SchemaDefinitionType.STRING,
                description: 'Temperature unit (celsius or fahrenheit)',
              },
            },
            required: ['location'],
          },
        },
      ]),
    });

    // Ensure Gateway Target waits for IAM permissions
    weatherTarget.node.addDependency(gateway.role);

    // ========================================
    // 4. CODE INTERPRETER - Python Code Execution
    // ========================================
    const codeInterpreter = new agentcore.CodeInterpreterCustom(this, 'CodeInterpreter', {
      codeInterpreterCustomName: 'research_assistant_interpreter',
      description: 'Code interpreter for Research Assistant',
    });

    // ========================================
    // 5. BROWSER - Web Browsing Capability with Recording
    // ========================================
    // S3 bucket for browser session recordings
    const recordingBucket = new s3.Bucket(this, 'BrowserRecordings', {
      bucketName: `agent-browser-recordings-${this.account}`,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    const browser = new agentcore.BrowserCustom(this, 'Browser', {
      browserCustomName: 'research_assistant_browser',
      description: 'Browser for Research Assistant with session recording',
      recordingConfig: {
        enabled: true,
        s3Location: {
          bucketName: recordingBucket.bucketName,
          objectKey: 'browser-sessions/',
        },
      },
    });

    // ========================================
    // 6. RUNTIME - Core Agent Infrastructure
    // ========================================
    const runtime = new agentcore.Runtime(this, 'ResearchAssistantRuntime', {
      runtimeName: 'research_assistant',
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromAsset(
        path.join(__dirname, '../agent')
      ),
      environmentVariables: {
        'MEMORY_ID': memory.memoryId!,
        'GATEWAY_URL': gateway.gatewayUrl!,
        'AWS_REGION': this.region,
        'CODE_INTERPRETER_ID': codeInterpreter.codeInterpreterId!,
        'BROWSER_ID': browser.browserId!,
      },
    });

    // ========================================
    // 7. BEDROCK MODEL PERMISSIONS
    // ========================================
    // Grant Runtime permissions to invoke Bedrock models
    runtime.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
      ],
      resources: ['*'],
    }));

    // ========================================
    // 8. RESOURCE PERMISSIONS
    // ========================================
    // Grant Runtime access to Memory
    memory.grantRead(runtime);
    memory.grantWrite(runtime);

    // Grant Runtime access to Gateway
    gateway.grantInvoke(runtime);

    // Grant Runtime access to Code Interpreter (automatic IAM permissions for custom instance)
    codeInterpreter.grantUse(runtime);

    // Grant Runtime access to Browser (automatic IAM permissions for custom instance)
    browser.grantUse(runtime);

    runtime.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock-agentcore:StartBrowserSession',
        'bedrock-agentcore:GetBrowserSession',
        'bedrock-agentcore:StopBrowserSession',
        'bedrock-agentcore:UpdateBrowserStream',
        'bedrock-agentcore:ConnectBrowserAutomationStream',
        'bedrock-agentcore:ConnectBrowserLiveViewStream',
      ],
      resources: ['*'],
      sid: 'AllowDefaultBrowserForStrands',
    }));

    // ========================================
    // 9. OUTPUTS - For CLI Usage
    // ========================================
    // Export important values for deployment and testing
    
    new cdk.CfnOutput(this, 'MemoryId', {
      value: memory.memoryId || 'Not available',
      description: 'Memory ID for agent configuration',
      exportName: 'ResearchAssistantMemoryId',
    });

    new cdk.CfnOutput(this, 'RuntimeId', {
      value: runtime.agentRuntimeId || 'Not available',
      description: 'Runtime ID for agent invocation',
      exportName: 'ResearchAssistantRuntimeId',
    });

    new cdk.CfnOutput(this, 'RuntimeArn', {
      value: runtime.agentRuntimeArn || 'Not available',
      description: 'Runtime ARN',
      exportName: 'ResearchAssistantRuntimeArn',
    });

    new cdk.CfnOutput(this, 'GatewayId', {
      value: gateway.gatewayId || 'Not available',
      description: 'Gateway ID for agent configuration',
      exportName: 'ResearchAssistantGatewayId',
    });

    new cdk.CfnOutput(this, 'GatewayUrl', {
      value: gateway.gatewayUrl || 'Not available',
      description: 'Gateway URL for agent invocation',
      exportName: 'ResearchAssistantGatewayUrl',
    });

    new cdk.CfnOutput(this, 'WeatherLambdaArn', {
      value: weatherLambda.functionArn,
      description: 'Weather Lambda function ARN',
      exportName: 'WeatherToolLambdaArn',
    });

    // Output Cognito details for authentication
    if (gateway.userPool) {
      new cdk.CfnOutput(this, 'CognitoUserPoolId', {
        value: gateway.userPool.userPoolId,
        description: 'Cognito User Pool ID for gateway authentication',
        exportName: 'GatewayCognitoUserPoolId',
      });
    }

    if (gateway.userPoolClient) {
      new cdk.CfnOutput(this, 'CognitoClientId', {
        value: gateway.userPoolClient.userPoolClientId,
        description: 'Cognito User Pool Client ID',
        exportName: 'GatewayCognitoClientId',
      });
    }

    if (gateway.tokenEndpointUrl) {
      new cdk.CfnOutput(this, 'TokenEndpointUrl', {
        value: gateway.tokenEndpointUrl,
        description: 'OAuth token endpoint URL for authentication',
        exportName: 'GatewayTokenEndpointUrl',
      });
    }

    // Output Code Interpreter and Browser IDs
    new cdk.CfnOutput(this, 'CodeInterpreterCustomId', {
      value: codeInterpreter.codeInterpreterId || 'Not available',
      description: 'Code Interpreter Custom ID',
      exportName: 'ResearchAssistantCodeInterpreterCustomId',
    });

    new cdk.CfnOutput(this, 'BrowserCustomId', {
      value: browser.browserId || 'Not available',
      description: 'Browser Custom ID',
      exportName: 'ResearchAssistantBrowserCustomId',
    });

  }
}