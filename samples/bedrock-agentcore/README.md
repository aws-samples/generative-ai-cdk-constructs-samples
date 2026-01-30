# AI Travel Planning Agent - Amazon Bedrock AgentCore Demo

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Serverless Architecture Advantages](#serverless-architecture-advantages)
- [AWS CDK AgentCore L2 Constructs](#aws-cdk-agentcore-l2-constructs)
- [Prerequisites](#prerequisites)
- [Deployment](#deployment)
- [Testing the Sample](#testing-the-sample)
- [Monitoring and Operations](#monitoring-and-operations)
- [Clean Up](#clean-up)
- [Project Structure](#project-structure)
- [Technical Implementation Details](#technical-implementation-details)
- [Additional Resources](#additional-resources)
- [Contributing](#contributing)
- [Content Security Legal Disclaimer](#content-security-legal-disclaimer)
- [License](#license)

## Overview

This sample demonstrates how to build and deploy a sophisticated AI travel planning assistant using Amazon Bedrock AgentCore. The solution leverages serverless architecture to eliminate infrastructure management while providing automatic scaling and high availability. It uses AWS CDK AgentCore L2 constructs as infrastructure as code (IaC).

### Key Agent core modules

- **Amazon Bedrock AgentCore Runtime** - Serverless agent hosting with automatic scaling
- **Amazon Bedrock AgentCore Memory** - Persistent conversation context with hour-based sessions
- **Amazon Bedrock AgentCore Gateway** - Secure integration with external tools and APIs
- **Amazon Bedrock AgentCore Code Interpreter** - Secure Python code execution in isolated sandboxes
- **Amazon Bedrock AgentCore Browser** - Cloud-based web research capabilities

### Business Use Case: Enterprise Travel Planning Assistant

This AI-powered travel planning assistant provides comprehensive trip planning capabilities for enterprise travel management:

**Core Capabilities:**
- **Trip Planning** - Weather forecasting, destination research, and budget calculations
- **Financial Analysis** - Expense splitting, tip calculations, and budget breakdowns
- **Destination Research** - Web-based research for activities, restaurants, and attractions
- **Real-Time Weather** - Current conditions for any global location
- **Context Awareness** - Maintains conversation history and user preferences across sessions

**Example Interaction:**

```
User: "I'm planning a 5-day trip to Miami. Check weather and calculate budget."

Agent: 
Weather: Sunny, 82°F, ideal beach conditions

Python Code:
```python
days = 5
hotel = 150
flights = 400
food_per_day = 60
total = (hotel * days) + flights + (food_per_day * days)
```

Result: Total budget: $1,450

Context Remembered: User preference for warm destinations and beach activities
```

## Architecture

### High-Level Component Diagram


### Component Details

#### 1. Amazon Bedrock AgentCore Runtime

**Purpose:** Serverless agent hosting and execution platform

**Capabilities:**
- Packages agent code directory into Docker container
- Deploys as managed serverless service
- Automatic scaling based on invocation demand
- Manages environment variables (MEMORY_ID, GATEWAY_URL)
- Integrated Amazon CloudWatch logging

#### 2. Amazon Bedrock AgentCore Memory

**Purpose:** Persistent conversation history with automatic session management

**Features:**
- Stores conversation history automatically
- Retrieves context for each agent invocation
- Hour-based session management: `session-2026-01-29-23`
- All conversations within same hour share memory context
- Automatic session reset each hour to prevent memory overflow

#### 3. Amazon Bedrock AgentCore Code Interpreter

**Purpose:** Secure Python code execution for calculations and data analysis

**Capabilities:**
- Executes Python code in isolated sandbox environments
- Performs mathematical calculations and data analysis
- Returns both code and execution results
- Automatic security isolation and resource limits

#### 4. Amazon Bedrock AgentCore Browser

**Purpose:** Cloud-based web research and information extraction

**Capabilities:**
- Managed Chrome browser in secure cloud environment
- Website navigation and data extraction
- JavaScript execution support
- Automatic session management and cleanup

#### 5. Amazon Bedrock AgentCore Gateway with AWS Lambda Target

**Purpose:** Secure integration with custom tools and external APIs

**Architecture:**
- AWS Lambda function for weather data retrieval
- Amazon Bedrock AgentCore Gateway for MCP protocol communication
- Amazon Cognito for machine-to-machine authentication
- Automatic IAM permission configuration


## Prerequisites

### Required Software and Services

- **AWS Account** with configured credentials
- **AWS CLI**: [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
  ```bash
  aws configure --profile [your-profile]
  AWS Access Key ID [None]: xxxxxx
  AWS Secret Access Key [None]: yyyyyyyyyy
  Default region name [None]: us-east-1
  Default output format [None]: json
  ```
- **AWS CDK CLI**: `npm install -g aws-cdk`
- **Node.js 18+** and npm
- **Python 3.10+**
- **Docker Desktop**: [Installation Guide](https://docs.docker.com/desktop/install/)
- **Amazon Bedrock** model access (Claude 3.7 Sonnet)

### Model Access

Ensure you enable model access to Claude 3.7 Sonnet in the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/home#/modelaccess) in the region you intend to deploy this sample.

## Deployment

### Step 1: Clone Repository

If not done already, clone this repository:

```bash
git clone https://github.com/aws-samples/generative-ai-cdk-constructs-samples.git
```

### Step 2: Navigate to Sample Directory

```bash
cd generative-ai-cdk-constructs-samples/samples/bedrock-agentcore
```

### Step 3: Install AWS CDK Dependencies

```bash
npm install
```

### Step 4: Configure Agent Dependencies

Navigate to the agent directory and set up Python environment:

```bash
cd agent

# Create Python virtual environment
python3 -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Return to project root
cd ..
```

### Step 5: Bootstrap AWS CDK (First Time Only)

```bash
# Replace ACCOUNT-ID and REGION with your AWS account details
cdk bootstrap aws://ACCOUNT-ID/us-east-1
```

### Step 6: Deploy Infrastructure

```bash
# Deploy all resources
cdk deploy --require-approval=never
```

**Deployment Duration:** Approximately 5-10 minutes

**Resources Deployed:**
- Amazon Bedrock AgentCore Runtime with containerized agent
- Amazon Bedrock AgentCore Memory with hour-based session configuration
- Amazon Bedrock AgentCore Gateway with Amazon Cognito authentication
- AWS Lambda function for weather data
- Amazon Bedrock AgentCore Gateway Target for Lambda integration
- All AWS Identity and Access Management (IAM) permissions automatically configured

### Step 7: Retrieve Deployment Outputs

After successful deployment, retrieve the required configuration values:

```bash
# Get Runtime Name
aws cloudformation describe-stacks \
  --stack-name AgentCoreDemoStack \
  --query 'Stacks[0].Outputs[?OutputKey==`RuntimeName`].OutputValue' \
  --output text

# Get Memory ID
aws cloudformation describe-stacks \
  --stack-name AgentCoreDemoStack \
  --query 'Stacks[0].Outputs[?OutputKey==`MemoryId`].OutputValue' \
  --output text

# Get Gateway URL
aws cloudformation describe-stacks \
  --stack-name AgentCoreDemoStack \
  --query 'Stacks[0].Outputs[?OutputKey==`GatewayUrl`].OutputValue' \
  --output text
```

### Step 8: Install CLI Tool (Optional)

For convenient access from any directory:

```bash
# Make wrapper script executable
chmod +x travel-agent-wrapper.sh

# Install globally (requires sudo on macOS/Linux)
sudo cp travel-agent-wrapper.sh /usr/local/bin/travel-agent
sudo chmod +x /usr/local/bin/travel-agent

# Verify installation
which travel-agent
# Expected output: /usr/local/bin/travel-agent
```

## Testing the Sample

### Basic Command Structure

From the project directory:

```bash
# Using Python script directly
python3 travel-agent "your prompt or question"

# Or if you installed the CLI tool globally
travel-agent "your prompt or question"
```

### Test Scenarios

#### Scenario 1: Memory Persistence (Hour-Based Sessions)

Test the Amazon Bedrock AgentCore Memory capability:

```bash
# First interaction - establish context
travel-agent "My name is Sarah and I love beach vacations"

# Second interaction within same hour - verify context retrieval
travel-agent "What's my name and what do I like?"
```

**Expected Result:** Agent retrieves and recalls "Sarah" and "beach vacation" preferences

#### Scenario 2: Code Interpreter Execution

Test the Amazon Bedrock AgentCore Code Interpreter:

```bash
travel-agent "Calculate: $1500 budget split as 40% hotel, 30% food, 20% activities, 10% miscellaneous"
```

**Expected Output:**
```
Python Code:
```python
budget = 1500
hotel = budget * 0.40
food = budget * 0.30
activities = budget * 0.20
misc = budget * 0.10
print(f"Hotel: ${hotel}, Food: ${food}, Activities: ${activities}, Misc: ${misc}")
```

Result:
Hotel: $600.0, Food: $450.0, Activities: $300.0, Misc: $150.0
```

#### Scenario 3: Weather Tool via Gateway

Test the Amazon Bedrock AgentCore Gateway integration with AWS Lambda:

```bash
travel-agent "What's the current weather in Miami?"
```

**Expected Result:** Current weather conditions including temperature, conditions, humidity, and wind speed

#### Scenario 4: Browser Tool for Research

Test the Amazon Bedrock AgentCore Browser capability:

```bash
travel-agent "Research popular beach activities in Miami"
```

**Expected Result:** Agent navigates websites and extracts relevant information about Miami beach activities

#### Scenario 5: Multi-Tool Orchestration

Test complete agent orchestration across all tools:

```bash
travel-agent "I'm planning a 5-day Seattle trip. Check weather, calculate $2000 budget breakdown, and research top attractions"
```

**Expected Result:** Agent coordinates multiple tools:
- Weather Tool → Current Seattle conditions
- Code Interpreter → Budget calculation with Python code
- Browser Tool → Top attractions research
- Memory → Conversation context preservation

### Verification Steps

1. **Check Amazon CloudWatch Logs**
   ```bash
   # View Runtime logs
   aws logs tail /aws/bedrock-agentcore/runtime/travel_planning_agent --follow
   ```

2. **Verify Memory Storage**
   - Run the memory test scenario twice within the same hour
   - Confirm agent recalls information from first conversation

3. **Test Tool Permissions**
   - Each scenario should execute without permission errors
   - Check CloudWatch logs for successful tool invocations

### Troubleshooting

**Common Issues:**

1. **"Access Denied" Errors**
   - Verify IAM permissions are correctly configured
   - Check AWS credentials are valid and have necessary permissions

2. **Memory Not Persisting**
   - Ensure both invocations occur within the same hour
   - Verify Memory ID is correctly configured in environment variables

3. **Code Interpreter Failures**
   - Check Amazon CloudWatch logs for detailed error messages
   - Verify Code Interpreter permissions in IAM role

4. **Gateway Connection Errors**
   - Confirm Gateway URL is correctly configured
   - Check Amazon Cognito authentication is functioning

## Monitoring and Operations

### Amazon CloudWatch Logs

View real-time logs for debugging and monitoring:

```bash
# Amazon Bedrock AgentCore Runtime logs
aws logs tail /aws/bedrock-agentcore/runtime/travel_planning_agent --follow

# AWS Lambda weather tool logs
aws logs tail /aws/lambda/AgentCoreDemoStack-WeatherToolFunction --follow
```

### Session Tracking

Monitor agent logs for session identifiers to track conversation flows:

```
Generated hour-based session ID: session-2026-01-29-23
```

### Performance Metrics

Key metrics to monitor in Amazon CloudWatch:
- Runtime invocation count
- Average invocation duration
- Tool execution latency
- Memory retrieval/storage operations
- Error rates

## Clean Up

To avoid incurring future charges, delete all deployed resources:

### Step 1: Destroy CDK Stack

```bash
cdk destroy AgentCoreDemoStack
```

### Step 2: Delete CloudWatch Log Groups

```bash
# Delete Runtime logs
aws logs delete-log-group --log-group-name /aws/bedrock-agentcore/runtime/travel_planning_agent

# Delete Lambda logs
aws logs delete-log-group --log-group-name /aws/lambda/AgentCoreDemoStack-WeatherToolFunction
```

### Step 3: Verify Resource Deletion

Ensure all resources have been removed:

```bash
# Verify stack deletion
aws cloudformation describe-stacks --stack-name AgentCoreDemoStack
# Should return: "Stack with id AgentCoreDemoStack does not exist"
```

### Step 4: Remove CLI Tool (If Installed)

```bash
sudo rm /usr/local/bin/travel-agent
```

## Project Structure

```
bedrock-agentcore/
├── agent/                      # Agent code (deployed to Runtime)
│   ├── agent.py               # Main entrypoint with @app.entrypoint decorator
│   ├── config.py              # System prompt and configuration
│   ├── tools.py               # Tool initialization and configuration
│   ├── memory.py              # Memory utilities (reference implementation)
│   ├── Dockerfile             # Container definition for Runtime
│   └── requirements.txt       # Python dependencies
├── lib/
│   └── agentcore-demo-stack.ts # AWS CDK L2 constructs infrastructure
├── lambda/
│   └── weather-tool/          # Gateway Lambda target implementation
├── travel-agent               # Demo CLI tool (Python)
├── travel-agent-wrapper.sh    # Wrapper script using virtual environment
├── package.json               # Node.js dependencies
├── cdk.json                   # CDK configuration
└── README.md                  # This file
```

## Technical Implementation Details

### Agent Entrypoint (agent/agent.py)

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Generate hour-based session identifier
    session_id = datetime.now().strftime("session-%Y-%m-%d-%H")
    
    # Initialize session manager for automatic memory management
    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=actor_id
        ),
        region_name=AWS_REGION
    )
    
    # Create agent with automatic memory handling
    agent = Agent(
        model=MODEL_ID,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        session_manager=session_manager  # Automatic memory retrieval/storage
    )
    
    # Invoke agent (memory managed automatically by session_manager)
    result = agent(payload.get("prompt"))
    
    return {"result": result.message}
```

### Infrastructure as Code (AWS CDK Stack)

```typescript
// 1. Amazon Bedrock AgentCore Runtime - Deploys agent container
const runtime = new agentcore.Runtime(this, 'TravelAgentRuntime', {
  runtimeName: 'travel_planning_agent',
  agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromAsset(
    path.join(__dirname, '../agent')
  ),
});

// 2. Amazon Bedrock AgentCore Memory - Conversation storage
const memory = new agentcore.Memory(this, 'TravelAgentMemory', {
  memoryName: 'travel_agent_memory',
  expirationDuration: cdk.Duration.days(90),
});

// 3. Amazon Bedrock AgentCore Gateway - External tool integration
const gateway = new agentcore.Gateway(this, 'TravelAgentGateway', {
  gatewayName: 'travel-agent-gateway',
  // Amazon Cognito M2M authentication created automatically
});

// 4. Amazon Bedrock AgentCore Gateway Target - Weather Lambda
const weatherTarget = gateway.addLambdaTarget('WeatherTarget', {
  lambdaFunction: weatherLambda,
  toolSchema: agentcore.ToolSchema.fromInline([/* schema */]),
  // IAM permissions granted automatically
});

// 5. IAM Permissions - Automatic grant methods
memory.grantRead(runtime);
memory.grantWrite(runtime);
gateway.grantInvoke(runtime);
```

### Session Management

**Hour-Based Session Format:** `session-YYYY-MM-DD-HH`

**Examples:**
```
10:00-10:59 → session-2026-01-29-10 (shared session)
11:00-11:59 → session-2026-01-29-11 (new session)
```

**Benefits:**
- Automatic memory reset every hour prevents overflow
- Same-hour conversations maintain full context
- No manual session lifecycle management required
- Predictable memory behavior for testing and debugging

### Tool Configuration

**Amazon Bedrock AgentCore Code Interpreter:**
```python
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

code_interpreter = AgentCoreCodeInterpreter(region=AWS_REGION)
tools.append(code_interpreter.code_interpreter)
```

**Amazon Bedrock AgentCore Browser:**
```python
from strands_tools.browser import AgentCoreBrowser

browser = AgentCoreBrowser(region=AWS_REGION)
tools.append(browser.browser)
```

**Weather Tool via Gateway:**
```typescript
gateway.addLambdaTarget('WeatherTarget', {
  gatewayTargetName: 'weather-tool',
  description: 'Real-time weather information tool',
  lambdaFunction: weatherLambda,
  toolSchema: agentcore.ToolSchema.fromInline([
    {
      name: 'get_weather',
      description: 'Retrieve current weather conditions for specified location',
      inputSchema: {/* schema definition */}
    }
  ]),
});
```

## Additional Resources

### Documentation

- **DEMO_SCRIPT.md** - Complete presentation guide with demonstration scenarios
- **TRAVEL_AGENT_QUICK_START.md** - Quick reference for CLI usage
- **MEMORY_SESSION_FIX.md** - Memory implementation technical details
- **AWS_CONSOLE_INVOCATION.md** - Manual invocation via AWS Management Console
- **STACK_REFACTOR_SUMMARY.md** - AWS CDK stack architecture explanation

### AWS Documentation

- [AWS CDK AgentCore L2 Constructs (Alpha)](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-bedrock-agentcore-alpha-readme.html)
- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AWS Cloud Development Kit (AWS CDK) Developer Guide](https://docs.aws.amazon.com/cdk/latest/guide/)

### Key Takeaways

**AWS CDK L2 Constructs Efficiency:**
- 70% code reduction compared to L1 constructs
- Type-safe, intuitive APIs with IntelliSense support
- Automatic IAM permission configuration
- Production-ready defaults with full customization

**Amazon Bedrock AgentCore Production Readiness:**
- Serverless scaling (Amazon Bedrock AgentCore Runtime)
- Persistent memory (Amazon Bedrock AgentCore Memory)
- Secure tool execution (Amazon Bedrock AgentCore Browser, Code Interpreter)
- Custom integrations (Amazon Bedrock AgentCore Gateway)

**Rapid Development Cycle:**
- Infrastructure: ~180 lines of TypeScript
- Agent implementation: ~100 lines of Python
- Complete AI assistant deployed in under 30 minutes

## Contributing

We welcome contributions to extend this demonstration:

**Potential Enhancements:**
- Additional Amazon Bedrock AgentCore Gateway targets (databases, CRM systems, APIs)
- Advanced memory strategies (semantic, episodic)
- Sophisticated custom tools and integrations
- Multi-agent workflows and collaboration patterns

Please refer to the [Contributing Guidelines](../../CONTRIBUTING.md) for submission process.

## Content Security Legal Disclaimer

The sample code; software libraries; command line tools; proofs of concept; templates; or other related technology (including any of the foregoing that are provided by our personnel) is provided to you as AWS Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon Bedrock AgentCore Runtime instances, Amazon Bedrock model invocations, or using Amazon CloudWatch logging.

## License

This sample is licensed under the MIT License. See the [LICENSE](../../LICENSE) file for details.

---

**Built with AWS Cloud Development Kit (AWS CDK) and Amazon Bedrock AgentCore L2 Constructs**

For questions, issues, or feature requests, please refer to the [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)