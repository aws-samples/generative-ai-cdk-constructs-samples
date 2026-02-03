"""
Tools module for AgentCore demo agent
Hybrid approach: boto3 for Code Interpreter (custom ID), Strands for Browser (functional)
"""

import os
import boto3
from strands.tools import tool
from strands_tools.browser import AgentCoreBrowser


# Read Code Interpreter and Browser IDs from environment (set by CDK)
CODE_INTERPRETER_ID = os.environ.get('CODE_INTERPRETER_ID')
BROWSER_ID = os.environ.get('BROWSER_ID')  # Created by CDK but Strands uses default


# ========================================
# WEATHER TOOL
# ========================================
@tool
def get_weather(location: str, unit: str = "fahrenheit") -> str:
    """Get current weather information for a specific location
    
    Args:
        location: The city and state, e.g., San Francisco, CA
        unit: Temperature unit (celsius or fahrenheit), default is fahrenheit
    
    Returns:
        Weather information including temperature, conditions, humidity, and wind
    """
    print(f"[TOOL INVOKED] Weather tool called for: {location}")
    
    # Mock weather data for different cities
    weather_data = {
        "seattle": {"condition": "Rainy", "temp_f": 52, "temp_c": 11, "humidity": "75%", "wind": "12 mph"},
        "miami": {"condition": "Sunny", "temp_f": 82, "temp_c": 28, "humidity": "80%", "wind": "8 mph"},
        "new york": {"condition": "Cloudy", "temp_f": 45, "temp_c": 7, "humidity": "60%", "wind": "15 mph"},
        "san francisco": {"condition": "Fog", "temp_f": 58, "temp_c": 14, "humidity": "70%", "wind": "10 mph"},
        "chicago": {"condition": "Windy", "temp_f": 38, "temp_c": 3, "humidity": "55%", "wind": "20 mph"},
    }
    
    # Extract city name
    city = location.lower().split(',')[0].strip()
    
    # Get weather data or use default
    weather = weather_data.get(city, {
        "condition": "Partly Cloudy", 
        "temp_f": 68, 
        "temp_c": 20, 
        "humidity": "55%", 
        "wind": "10 mph"
    })
    
    # Format response based on unit
    if unit.lower() == "celsius":
        temp_str = f"{weather['temp_c']}°C"
    else:
        temp_str = f"{weather['temp_f']}°F"
    
    result = f"The current weather in {location} is {weather['condition']} with a temperature of {temp_str}, humidity at {weather['humidity']}, and wind speed of {weather['wind']}."
    
    print(f"[TOOL RESULT] Weather data returned successfully")
    return result


def initialize_tools(region: str):
    """
    Initialize all agent tools
    
    Hybrid approach:
    - Code Interpreter: boto3 with custom instance ID (demonstrates CDK integration)
    - Browser: Strands wrapper with default instance (functional, framework limitation)
    
    Args:
        region: AWS region
        
    Returns:
        List of initialized tools
    """
    tools = []
    
    # Create boto3 client for AgentCore services
    client = boto3.client('bedrock-agentcore', region_name=region)
    
    # ========================================
    # CODE INTERPRETER - boto3 with custom ID
    # ========================================
    try:
        # Use custom instance if provided, otherwise use AWS default
        code_interpreter_id = CODE_INTERPRETER_ID or "aws.codeinterpreter.v1"
        
        if CODE_INTERPRETER_ID:
            print(f"[CODE INTERPRETER] Using CDK custom instance: {CODE_INTERPRETER_ID}")
        else:
            print("[CODE INTERPRETER] Using AWS default instance: aws.codeinterpreter.v1")
        
        # Create Strands-compatible tool wrapper
        @tool
        def execute_python(code: str) -> str:
            """Execute Python code in a secure sandbox environment.
            
            Use this tool to:
            - Perform calculations and mathematical operations
            - Analyze data and generate insights
            - Validate answers through code execution
            - Process and transform data
            
            Args:
                code: Python code to execute
                
            Returns:
                The output or result of the code execution
            """
            try:
                # Start Code Interpreter session with custom instance
                session = client.start_code_interpreter_session(
                    codeInterpreterIdentifier=code_interpreter_id,
                    name="execution-session",
                    sessionTimeoutSeconds=900
                )
                session_id = session['sessionId']
                print(f"[CODE INTERPRETER] Started session: {session_id}")
                
                # Execute code
                response = client.invoke_code_interpreter(
                    codeInterpreterIdentifier=code_interpreter_id,
                    sessionId=session_id,
                    name="executeCode",
                    arguments={
                        "language": "python",
                        "code": code
                    }
                )
                
                # Process streaming response
                result_text = ""
                for event in response.get('stream', []):
                    if 'result' in event:
                        result_data = event['result']
                        if 'content' in result_data:
                            for content_item in result_data['content']:
                                if content_item.get('type') == 'text':
                                    result_text += content_item.get('text', '')
                
                # Stop session
                client.stop_code_interpreter_session(
                    codeInterpreterIdentifier=code_interpreter_id,
                    sessionId=session_id
                )
                print(f"[CODE INTERPRETER] Stopped session: {session_id}")
                
                return result_text if result_text else "Code executed successfully (no output)"
                
            except Exception as e:
                print(f"[CODE INTERPRETER] Error: {str(e)}")
                return f"Error executing code: {str(e)}"
        
        tools.append(execute_python)
        print("[CODE INTERPRETER] Tool initialized successfully")
        
    except Exception as e:
        print(f"[CODE INTERPRETER] Initialization ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # ========================================
    # BROWSER - Strands wrapper (uses default)
    # ========================================
    try:
        # Use Strands wrapper for functional Browser with full navigation support
        browser_tool = AgentCoreBrowser(region=region)
        tools.append(browser_tool.browser)
        print(f"[BROWSER] Using Strands wrapper (default instance)")
        
        if BROWSER_ID:
            print(f"[BROWSER] Note: CDK custom instance '{BROWSER_ID}' exists but Strands uses AWS default")
            print(f"[BROWSER] Reason: Strands framework doesn't support custom instance IDs yet")
        
    except Exception as e:
        print(f"[BROWSER] Initialization ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # ========================================
    # WEATHER TOOL
    # ========================================
    tools.append(get_weather)
    print("[WEATHER] Tool initialized")
    
    print(f"[TOOLS] Total tools initialized: {len(tools)}")
    return tools