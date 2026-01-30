"""
Research Assistant Agent - Main Entry Point

This agent demonstrates Amazon Bedrock AgentCore capabilities using L2 CDK constructs:
- Memory: Automatic memory management via AgentCoreMemorySessionManager
- Tools: Weather, Code Interpreter, Browser
- Runtime: Deployed via CDK L2 construct

Business Use Case: AI Travel Planning Assistant

Session Management:
- Default: Hour-based sessions (session-YYYY-MM-DD-HH)
- New session every hour for automatic memory reset
- Can override with custom session_id from console
"""

from typing import Dict, Any
from datetime import datetime
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

# Import our modular components (same directory)
from config import MEMORY_ID, AWS_REGION, MODEL_ID, SYSTEM_PROMPT, log_config
from tools import initialize_tools

# Initialize the AgentCore runtime app
app = BedrockAgentCoreApp()

# Log configuration on startup
log_config()

# Initialize tools
tools = initialize_tools(AWS_REGION)

# Note: Agent will be created per-invocation with session-specific memory config
print("Agent initialization ready (will be created per invocation)")


@app.entrypoint
def invoke(payload: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main entry point using AgentCoreMemorySessionManager for automatic memory.
    
    Flow (automatic via session_manager):
    1. Session manager retrieves relevant memories
    2. Agent processes with memory context
    3. Session manager stores conversation
    
    Args:
        payload: Request payload with 'prompt'
        context: Runtime context with session_id and user_id
        
    Returns:
        Dict with "result" key containing agent's response
    """
    print("=" * 80)
    print("INVOKE FUNCTION CALLED")
    print("=" * 80)
    
    try:
        # Extract input and identifiers
        user_input = payload.get("prompt", "Hello")
        actor_id = getattr(context, 'user_id', 'default-user')
        
        # Always generate hour-based session ID
        # Format: session-YYYY-MM-DD-HH (new session every hour)
        # Ignores any Runtime-provided UUID to ensure consistent memory behavior
        now = datetime.now()
        session_id = now.strftime("session-%Y-%m-%d-%H")
        print(f"Generated hour-based session ID: {session_id}")
        
        print(f"\n{'='*60}")
        print(f"Processing request")
        print(f"Actor: {actor_id}")
        print(f"Session: {session_id}")
        print(f"Prompt: {user_input[:100]}...")
        print(f"{'='*60}\n")
        
        # Create session manager if memory is configured
        session_manager = None
        if MEMORY_ID:
            print(f"Creating session manager with Memory ID: {MEMORY_ID}")
            
            # Configure memory for this session
            agentcore_memory_config = AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=actor_id
            )
            
            # Create session manager (handles automatic memory)
            session_manager = AgentCoreMemorySessionManager(
                agentcore_memory_config=agentcore_memory_config,
                region_name=AWS_REGION
            )
            print("Session manager created - automatic memory enabled")
        else:
            print("Memory not configured (MEMORY_ID not set)")
        
        # Create agent with session manager (automatic memory)
        print("Creating agent for this invocation...")
        agent = Agent(
            model=MODEL_ID,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            session_manager=session_manager,  # Automatic memory handling
        )
        
        # Invoke agent (session_manager automatically handles memory)
        print(f"Invoking agent...")
        result = agent(user_input)
        
        print(f"Agent invocation completed")
        print(f"Result type: {type(result)}")
        
        print("=" * 80)
        print(f"Returning response to runtime")
        print("=" * 80)
        
        # Return dict with "result" key (AWS sample pattern)
        return {"result": result.message}
        
    except Exception as e:
        error_msg = f"Error in invoke function: {str(e)}"
        print("=" * 80)
        print("ERROR OCCURRED:")
        print(error_msg)
        print("=" * 80)
        import traceback
        traceback.print_exc()
        # Return error in same format as success
        return {"result": error_msg, "error": True}


if __name__ == "__main__":
    # Run locally for testing
    app.run()