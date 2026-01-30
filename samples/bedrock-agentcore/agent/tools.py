"""
Tools module for AgentCore demo agent
Provides weather, code interpreter, and browser tools
"""

from strands.tools import tool
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from strands_tools.browser import AgentCoreBrowser


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
    
    Args:
        region: AWS region
        
    Returns:
        List of initialized tools
    """
    tools = []
    
    # Add Code Interpreter
    try:
        code_interpreter = AgentCoreCodeInterpreter(region=region)
        tools.append(code_interpreter.code_interpreter)
        print("Code Interpreter tool initialized")
    except Exception as e:
        print(f"Code Interpreter error: {str(e)}")
    
    # Add Browser
    try:
        browser = AgentCoreBrowser(region=region)
        tools.append(browser.browser)
        print("Browser tool initialized")
    except Exception as e:
        print(f"Browser error: {str(e)}")
    
    # Add Weather
    tools.append(get_weather)
    print("Weather tool initialized")
    
    return tools