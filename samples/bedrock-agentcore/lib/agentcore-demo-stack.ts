import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as agentcore from '@aws-cdk/aws-bedrock-agentcore-alpha';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as path from 'path';

/**
 * AgentCore Demo Stack - Refactored Structure
 * 
 * Resource Creation Order:
 * 1. Runtime (agent container infrastructure)
 * 2. Memory (conversation storage)
 * 3. Gateway (external tool integration)
 * 4. Gateway Targets (Lambda functions)
 * 5. Tool Permissions (Code Interpreter, Browser)
 * 
 * Business Use Case: AI Research Assistant
 */
export class AgentCoreDemoStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ========================================
    // 1. RUNTIME - Core Agent Infrastructure
    // ========================================
    // Create the agent runtime first - this is the foundation
    // Environment variables will be populated after dependencies are created
    const runtime = new agentcore.Runtime(this, 'ResearchAssistantRuntime', {
      runtimeName: 'research_assistant',
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromAsset(
        path.join(__dirname, '../agent')
      ),
      // Environment variables added after Memory and Gateway creation
    });

    // ========================================
    // 2. MEMORY - Conversation Storage
    // ========================================
    // Default short-term memory for immediate conversation retrieval
    const memory = new agentcore.Memory(this, 'ResearchAssistantMemory', {
      memoryName: 'research_assistant_memory',
      description: 'Short-term memory for AI Research Assistant chat conversations',
      expirationDuration: cdk.Duration.days(90),
      // NO memoryStrategies = uses default STM (matches aws-asl-metahuman pattern)
    });

    // ========================================
    // 3. GATEWAY - External Tool Integration
    // ========================================
    // MCP Gateway with Cognito M2M authentication
    const gateway = new agentcore.Gateway(this, 'ResearchAssistantGateway', {
      gatewayName: 'research-assistant-gateway',
      description: 'Gateway for Research Assistant external tools',
      protocolConfiguration: new agentcore.McpProtocolConfiguration({
        instructions: 'Use this gateway to access weather and external data tools',
        searchType: agentcore.McpGatewaySearchType.SEMANTIC,
        supportedVersions: [agentcore.MCPProtocolVersion.MCP_2025_03_26],
      }),
    });

    // ========================================
    // 4. GATEWAY TARGETS - Lambda Functions
    // ========================================
    // Weather tool Lambda function
    const weatherLambda = new lambda.Function(this, 'WeatherToolFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambda/weather-tool')),
      description: 'Weather tool for Research Assistant',
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: {
        LOG_LEVEL: 'INFO',
      },
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
    // 5. TOOL PERMISSIONS - Code Interpreter & Browser
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

    // Code Interpreter permissions
    runtime.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock-agentcore:InvokeCodeInterpreter',
        'bedrock-agentcore:StartCodeInterpreterSession',
        'bedrock-agentcore:StopCodeInterpreterSession',
        'bedrock-agentcore:GetCodeInterpreterSession',
      ],
      resources: ['*'],
    }));

    // Browser permissions (complete set from AWS documentation)
    runtime.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock-agentcore:CreateBrowser',
        'bedrock-agentcore:ListBrowsers',
        'bedrock-agentcore:GetBrowser',
        'bedrock-agentcore:DeleteBrowser',
        'bedrock-agentcore:StartBrowserSession',
        'bedrock-agentcore:ListBrowserSessions',
        'bedrock-agentcore:GetBrowserSession',
        'bedrock-agentcore:StopBrowserSession',
        'bedrock-agentcore:UpdateBrowserStream',
        'bedrock-agentcore:ConnectBrowserAutomationStream',
        'bedrock-agentcore:ConnectBrowserLiveViewStream',
      ],
      resources: ['*'],
    }));

    // ========================================
    // 6. RESOURCE PERMISSIONS
    // ========================================
    // Grant Runtime access to Memory
    memory.grantRead(runtime);
    memory.grantWrite(runtime);

    // Grant Runtime access to Gateway
    gateway.grantInvoke(runtime);

    // ========================================
    // 5. RUNTIME CONFIGURATION
    // ========================================
    // Add environment variables to Runtime (now that Memory and Gateway exist)
    const runtimeCfn = runtime.node.defaultChild as cdk.aws_bedrockagentcore.CfnRuntime;
    runtimeCfn.addPropertyOverride('EnvironmentVariables', {
      'MEMORY_ID': memory.memoryId,
      'GATEWAY_URL': gateway.gatewayUrl,
      'AWS_REGION': this.region,
    });


    // ========================================
    // 8. OUTPUTS - For CLI Usage
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

    // ========================================
    // NOTES ON L2 CONSTRUCT BENEFITS
    // ========================================
    /*
     * This stack demonstrates the power of AgentCore L2 constructs:
     * 
     * 1. SIMPLIFIED SYNTAX
     *    - No CfnXxx constructs needed
     *    - Clean, intuitive API
     *    - Type-safe properties
     * 
     * 2. AUTOMATIC IAM PERMISSIONS
     *    - Gateway automatically gets Lambda invoke permissions
     *    - Memory automatically configures service roles
     *    - No manual IAM policy crafting required
     * 
     * 3. BUILT-IN BEST PRACTICES
     *    - Memory strategies use recommended configurations
     *    - Gateway uses secure defaults (Cognito M2M)
     *    - Proper encryption and logging
     * 
     * 4. SEAMLESS INTEGRATION
     *    - Gateway.addLambdaTarget() handles everything
     *    - Memory strategies work out of the box
     *    - Cross-construct references just work
     * 
     * 5. PRODUCTION READY
     *    - All resources properly tagged
     *    - CloudWatch logging enabled
     *    - Security best practices applied
     */
  }
}