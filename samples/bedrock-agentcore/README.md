# 🌴 AI Travel Planning Agent - Amazon Bedrock AgentCore Demo

A production-ready AI Travel Planning Assistant built with **Amazon Bedrock AgentCore**, demonstrating serverless deployment, automatic memory management, and multi-tool orchestration using **AWS CDK L2 constructs**.

## 🎯 Business Use Case: AI Travel Planning Assistant

Your personal AI travel planner that helps you:

- ✈️ **Plan trips** - Get weather, research destinations, calculate budgets
- 🧮 **Calculate costs** - Split bills, compute tips, budget breakdowns
- 🌐 **Research destinations** - Browse websites for activities, restaurants, attractions
- 🌤️ **Check weather** - Real-time conditions for any location
- 🧠 **Remember preferences** - Maintains conversation context (warm destinations, beach activities, etc.)

### Example Interaction

```
You: "I'm planning a 5-day trip to Miami. Check weather and calculate budget."

Agent: 
🌤️ Weather: Sunny, 82°F, perfect beach weather!

📝 Python Code:
```python
days = 5
hotel = 150
flights = 400
food_per_day = 60
total = (hotel * days) + flights + (food_per_day * days)
```

📊 Result: Total budget: $1450

🧠 Remembers: You prefer warm destinations and beach activities!
```

## 🏗️ Architecture - How It Works

### High-Level Flow

```
┌──────────────────┐
│   travel-agent   │  Beautiful CLI tool
│   CLI Command    │
└────────┬─────────┘
         │ boto3.invoke_agent_runtime()
         ▼
┌─────────────────────────────────────────┐
│   Amazon Bedrock AgentCore Runtime      │  🚀 Serverless Container
│   ─────────────────────────────────────│
│   • Deployed via CDK L2 construct       │
│   • Auto-scales with demand             │
│   • Packages agent/ directory           │
│   • Manages environment variables       │
└────────┬────────────────────────────────┘
         │ Invokes agent/agent.py
         ▼
┌─────────────────────────────────────────┐
│   Strands Agent (agent/agent.py)        │
│   ─────────────────────────────────────│
│   • AgentCoreMemorySessionManager       │
│   • Automatic memory retrieval/storage  │
│   • Multi-tool orchestration            │
└────────┬────────────────────────────────┘
         │
    ┌────┴────┬──────────┬─────────┐
    ▼         ▼          ▼         ▼
┌────────┐ ┌──────┐ ┌────────┐ ┌────────┐
│ Memory │ │ Code │ │Browser │ │Weather │
│  (STM) │ │ Interp│ │  Tool  │ │Gateway │
└────────┘ └──────┘ └────────┘ └────────┘
```

### Component Breakdown

#### 1. 🚀 **AgentCore Runtime** - Serverless Agent Hosting

**What it does:**
- Packages `agent/` directory into Docker container
- Deploys as managed serverless service
- Auto-scales based on demand
- Manages environment variables (MEMORY_ID, GATEWAY_URL)
- No server management needed!

**How it's deployed:**
```typescript
const runtime = new agentcore.Runtime(this, 'ResearchAssistantRuntime', {
  runtimeName: 'research_assistant',
  agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromAsset(
    path.join(__dirname, '../agent')
  ),
});
```

#### 2. 🧠 **AgentCore Memory** - Hour-Based Sessions

**What it does:**
- Stores conversation history automatically
- Retrieves context for each invocation
- Hour-based sessions: `session-2026-01-29-23`
- All conversations within same hour share memory
- Automatic reset each hour (prevents overflow)

**Implementation:**
```python
# Automatic memory via SessionManager
agentcore_memory_config = AgentCoreMemoryConfig(
    memory_id=MEMORY_ID,
    session_id=session_id,  # Hour-based
    actor_id=actor_id
)

session_manager = AgentCoreMemorySessionManager(
    agentcore_memory_config=agentcore_memory_config,
    region_name=AWS_REGION
)

# Agent automatically retrieves and stores memory
agent = Agent(
    session_manager=session_manager,
    tools=tools
)
```

#### 3. 🖥️ **Code Interpreter** - Python Execution

**What it does:**
- Executes Python code securely
- Performs calculations, data analysis
- Shows both code AND results
- Isolated sandbox environment

**Permissions Required:**
```typescript
runtime.addToRolePolicy(new iam.PolicyStatement({
  actions: [
    'bedrock-agentcore:InvokeCodeInterpreter',
    'bedrock-agentcore:StartCodeInterpreterSession',
    'bedrock-agentcore:StopCodeInterpreterSession',
    'bedrock-agentcore:GetCodeInterpreterSession',
  ],
  resources: ['*'],
}));
```

#### 4. 🌐 **Browser Tool** - Web Research

**What it does:**
- Managed Chrome browser in cloud
- Navigates websites
- Extracts information
- Secure isolated environment

**Complete Permissions:**
```typescript
runtime.addToRolePolicy(new iam.PolicyStatement({
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
```

#### 5. 🌦️ **Weather Tool** - Gateway + Lambda

**What it does:**
- Custom Lambda function for weather data
- Integrated via AgentCore Gateway
- MCP protocol communication
- Demonstrates custom tool integration

**Architecture:**
```typescript
// Lambda function
const weatherLambda = new lambda.Function(...);

// Gateway connection (automatic permissions!)
gateway.addLambdaTarget('WeatherTarget', {
  lambdaFunction: weatherLambda,
  toolSchema: agentcore.ToolSchema.fromInline([...]),
});
```

## 🚀 Quick Start

### Prerequisites

- **AWS Account** with configured credentials
- **AWS CDK CLI**: `npm install -g aws-cdk`
- **Node.js 18+** and npm
- **Python 3.10+**
- **Amazon Bedrock** model access (Claude 3.7 Sonnet)

### Installation & Deployment

```bash
# 1. Clone and install dependencies
git clone <repo-url>
cd agentcore-demo
npm install

# 2. Install agent dependencies
cd agent
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..

# 3. Bootstrap CDK (first time only)
cdk bootstrap aws://ACCOUNT-ID/us-east-1

# 4. Deploy the stack
cdk deploy
```

**Deployment time:** ~5-10 minutes

**What gets deployed:**
- ✅ AgentCore Runtime with agent container
- ✅ AgentCore Memory (short-term, hour-based)
- ✅ AgentCore Gateway with Cognito auth
- ✅ Weather Lambda function + Gateway Target
- ✅ All IAM permissions automatically configured

### Install travel-agent CLI

```bash
# Make wrapper executable
chmod +x travel-agent-wrapper.sh

# Install globally
sudo cp travel-agent-wrapper.sh /usr/local/bin/travel-agent
sudo chmod +x /usr/local/bin/travel-agent

# Verify installation
which travel-agent
# Output: /usr/local/bin/travel-agent
```

## 🎮 Using the travel-agent CLI

### Basic Usage

```bash
# From any directory
travel-agent "your prompt"
```

### Demo Scenarios

#### 1. Memory Demo (Hour-Based Sessions)
```bash
# First interaction
travel-agent "My name is Sarah and I love beach vacations"

# Second interaction (same hour)
travel-agent "What's my name and what do I like?"
# Agent remembers: "Sarah" and "beach vacations"
```

#### 2. Code Interpreter Demo
```bash
travel-agent "Calculate: $1500 budget split as 40% hotel, 30% food, 20% activities, 10% misc"

# Expected output with GREEN highlighting:
📝 Python Code:
```python
budget = 1500
hotel = budget * 0.40
food = budget * 0.30
activities = budget * 0.20
misc = budget * 0.10
print(f"Hotel: ${hotel}, Food: ${food}, Activities: ${activities}, Misc: ${misc}")
```

📊 Result:
Hotel: $600.0, Food: $450.0, Activities: $300.0, Misc: $150.0
```

#### 3. Weather Tool Demo
```bash
travel-agent "What's the current weather in Miami?"

# Uses Gateway + Lambda integration
# Returns: Temperature, conditions, humidity, wind
```

#### 4. Browser Tool Demo
```bash
travel-agent "Research popular beach activities in Miami"

# Agent navigates websites and extracts information
```

#### 5. Multi-Tool Complete Workflow
```bash
travel-agent "I'm planning a 5-day Seattle trip. Check weather, calculate $2000 budget breakdown, and research top attractions"

# Uses all tools:
# 🌦️ Weather → Seattle conditions
# 🖥️ Code → Budget calculation with code shown
# 🌐 Browser → Attractions research
# 🧠 Memory → Remembers the conversation
```

## 🎨 CLI Features

The `travel-agent` command provides:

- 🌴 **Beautiful branding** - Palm tree theme
- 🎨 **Color-coded output** - Green agent responses, yellow results
- 📊 **Feature icons** - Visual indicators for each tool
- 🧠 **Session tracking** - Shows current session ID
- ✨ **Automatic highlighting** - Code blocks, results, tools

**Sample Output:**
```
══════════════════════════════════════════════════════
  🌴 AMAZON BEDROCK AGENTCORE - TRAVEL PLANNING DEMO
══════════════════════════════════════════════════════

✨ AgentCore Features:
  🚀 Runtime       : Serverless deployment
  🧠 Memory        : Hour-based sessions
  🖥️ Code Interpreter: Python execution
  🌐 Browser       : Web research
  🌦️ Weather       : Real-time data

🎯 Your Request:
  Calculate 15% tip on $85

🧠 [SESSION] session-2026-01-29-23-00000000000
🚀 [RUNTIME] Invoking agent...

🤖 Agent Response:

[All text in GREEN with code blocks and results highlighted]
```

## 📁 Project Structure

```
agentcore-demo/
├── agent/                      # Agent code (deployed to Runtime)
│   ├── agent.py               # Main entrypoint with @app.entrypoint
│   ├── config.py              # System prompt & configuration
│   ├── tools.py               # Tool initialization
│   ├── memory.py              # Memory utilities (reference)
│   ├── Dockerfile             # Container definition
│   └── requirements.txt       # Python dependencies
├── lib/
│   └── agentcore-demo-stack.ts # CDK L2 constructs
├── lambda/
│   └── weather-tool/          # Gateway Lambda target
├── travel-agent               # Demo CLI tool (Python)
├── travel-agent-wrapper.sh    # Wrapper using venv
└── DEMO_SCRIPT.md            # Presentation guide
```

## 🔧 Technical Implementation

### agent/agent.py - Main Entrypoint

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Generate hour-based session ID
    session_id = datetime.now().strftime("session-%Y-%m-%d-%H")
    
    # Create session manager (automatic memory)
    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=actor_id
        ),
        region_name=AWS_REGION
    )
    
    # Create agent with automatic memory
    agent = Agent(
        model=MODEL_ID,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        session_manager=session_manager  # Handles memory automatically
    )
    
    # Invoke (memory handled automatically by session_manager)
    result = agent(payload.get("prompt"))
    
    return {"result": result.message}
```

### CDK Stack - Infrastructure as Code

```typescript
// 1. Runtime - Deploys agent container
const runtime = new agentcore.Runtime(this, 'ResearchAssistantRuntime', {
  runtimeName: 'research_assistant',
  agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromAsset(
    path.join(__dirname, '../agent')
  ),
});

// 2. Memory - Short-term conversation storage
const memory = new agentcore.Memory(this, 'ResearchAssistantMemory', {
  memoryName: 'research_assistant_memory',
  expirationDuration: cdk.Duration.days(90),
  // Default STM strategy - immediate retrieval
});

// 3. Gateway - External tool integration
const gateway = new agentcore.Gateway(this, 'ResearchAssistantGateway', {
  gatewayName: 'research-assistant-gateway',
  // Cognito M2M auth created automatically
});

// 4. Gateway Target - Weather Lambda
const weatherTarget = gateway.addLambdaTarget('WeatherTarget', {
  lambdaFunction: weatherLambda,
  toolSchema: agentcore.ToolSchema.fromInline([...]),
  // IAM permissions granted automatically!
});

// 5. Tool Permissions - Granted automatically
memory.grantRead(runtime);
memory.grantWrite(runtime);
gateway.grantInvoke(runtime);
```

## 🎯 Key Features Demonstrated

### 1. Serverless Deployment (Runtime)
- ✅ CDK packages and deploys agent code automatically
- ✅ No manual Docker builds or ECR pushes
- ✅ Auto-scaling with demand
- ✅ Managed infrastructure

### 2. Automatic Memory (Hour-Based)
- ✅ `AgentCoreMemorySessionManager` handles everything
- ✅ Hour-based sessions: `session-2026-01-29-23`
- ✅ Same hour = shared memory context
- ✅ New hour = fresh start (prevents overflow)
- ✅ No manual retrieve/store calls

### 3. Multi-Tool Orchestration
- ✅ **Code Interpreter** - Secure Python execution
- ✅ **Browser** - Cloud-based Chrome automation
- ✅ **Weather** - Custom Lambda via Gateway
- ✅ Agent decides which tools to use

### 4. Production-Ready Patterns
- ✅ CDK L2 constructs for type safety
- ✅ Automatic IAM permissions
- ✅ Cognito authentication
- ✅ CloudWatch logging
- ✅ Best practices built-in

## 📊 Session Management

### Hour-Based Sessions

**Format:** `session-YYYY-MM-DD-HH`

**Example:**
```
10:00-10:59 → session-2026-01-29-10 (same session)
11:00-11:59 → session-2026-01-29-11 (new session)
```

**Benefits:**
- ✅ Automatic memory reset every hour
- ✅ Prevents memory overflow
- ✅ Same-hour conversations maintain context
- ✅ No manual session management

**How it works:**
```python
# agent.py generates session ID
now = datetime.now()
session_id = now.strftime("session-%Y-%m-%d-%H")

# CLI provides 33+ char version for API validation
cli_session_id = f"session-{hour}-00000000000"  # Padded to 33 chars

# agent.py ignores CLI session, uses own hour-based ID
# All invocations same hour → same memory
```

## 🛠️ Tools Configuration

### Code Interpreter

**Located:** `agent/tools.py`

```python
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

code_interpreter = AgentCoreCodeInterpreter(region=AWS_REGION)
tools.append(code_interpreter.code_interpreter)
```

**System Prompt** enforces showing code:
```python
SYSTEM_PROMPT = """
CODE INTERPRETER OUTPUT FORMAT (MANDATORY):

📝 **Python Code:**
```python
[code here]
```

📊 **Result:**
[execution result]
"""
```

### Browser Tool

**Located:** `agent/tools.py`

```python
from strands_tools.browser import AgentCoreBrowser

browser = AgentCoreBrowser(region=AWS_REGION)
tools.append(browser.browser)
```

**Requirements:**
- Complete browser permissions (11 actions)
- `playwright` and `nest-asyncio` dependencies

### Weather Tool (Gateway + Lambda)

**Lambda:** `lambda/weather-tool/index.py`
**Gateway Target:** Configured in CDK stack

```typescript
gateway.addLambdaTarget('WeatherTarget', {
  gatewayTargetName: 'weather-tool',
  description: 'Weather information tool',
  lambdaFunction: weatherLambda,
  toolSchema: agentcore.ToolSchema.fromInline([
    {
      name: 'get_weather',
      description: 'Get current weather for a location',
      inputSchema: {...}
    }
  ]),
});
```

## 📚 Documentation

- **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)** - Complete presentation guide with 7 demo scenarios
- **[TRAVEL_AGENT_QUICK_START.md](TRAVEL_AGENT_QUICK_START.md)** - Quick reference for CLI usage
- **[MEMORY_SESSION_FIX.md](MEMORY_SESSION_FIX.md)** - Memory implementation details
- **[AWS_CONSOLE_INVOCATION.md](AWS_CONSOLE_INVOCATION.md)** - Invoke from AWS Console
- **[STACK_REFACTOR_SUMMARY.md](STACK_REFACTOR_SUMMARY.md)** - CDK structure explanation

## 🔍 Monitoring & Debugging

### CloudWatch Logs

```bash
# View Runtime logs
# Location: /aws/bedrock-agentcore/runtime/research_assistant/

# View Lambda logs
aws logs tail /aws/lambda/AgentCoreDemoStack-WeatherToolFunction --follow
```

### Session Tracking

Check agent logs for session IDs:
```
Generated hour-based session ID: session-2026-01-29-23
```

## 🧹 Cleanup

```bash
# Destroy all resources
cdk destroy
```

## 🎓 Key Takeaways

### What This Demo Proves

1. **L2 Constructs Are Powerful**
   - 70% less code vs L1 constructs
   - Type-safe, intuitive APIs
   - Automatic IAM permissions

2. **AgentCore is Production-Ready**
   - Serverless scaling (Runtime)
   - Persistent memory (Memory)
   - Secure tool access (Browser, Code)
   - Custom integrations (Gateway)

3. **Rapid Development**
   - Infrastructure: ~180 lines TypeScript
   - Agent code: ~100 lines Python
   - Full AI assistant in <30 minutes

### Production Considerations

- **Scaling:** Runtime auto-scales, no configuration needed
- **Security:** Cognito M2M auth, IAM permissions, isolated tools
- **Cost:** Pay-per-use, no idle costs
- **Monitoring:** CloudWatch Logs, built-in metrics
- **Memory:** Hour-based sessions prevent overflow

## 🤝 Contributing

Extend this demo with:
- Additional Gateway targets (database, CRM, etc.)
- Custom memory strategies
- More sophisticated tools
- Multi-agent workflows

## 📝 License

MIT License

---

**Built with ❤️ using Amazon Bedrock AgentCore L2 Constructs**

For questions or issues, check the [AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)