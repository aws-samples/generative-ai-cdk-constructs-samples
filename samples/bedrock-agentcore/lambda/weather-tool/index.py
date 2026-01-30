"""
Weather Tool Lambda Function

This Lambda function provides weather information for the Research Assistant agent.
It's invoked through AgentCore Gateway as a demonstration of Gateway → Lambda integration.

The function returns mock weather data for demo purposes.
In a production scenario, this would integrate with a real weather API.
"""

import json
import logging
import random
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mock weather data for different cities
WEATHER_DATA = {
    "seattle": {
        "conditions": ["Rainy", "Cloudy", "Partly Cloudy", "Drizzle"],
        "temp_range_c": (5, 18),
        "temp_range_f": (41, 64),
        "humidity": (65, 85),
    },
    "san francisco": {
        "conditions": ["Fog", "Sunny", "Partly Cloudy", "Windy"],
        "temp_range_c": (12, 22),
        "temp_range_f": (54, 72),
        "humidity": (55, 75),
    },
    "miami": {
        "conditions": ["Sunny", "Partly Cloudy", "Hot and Humid", "Thunderstorms"],
        "temp_range_c": (22, 32),
        "temp_range_f": (72, 90),
        "humidity": (70, 90),
    },
    "new york": {
        "conditions": ["Sunny", "Cloudy", "Rainy", "Snowy", "Windy"],
        "temp_range_c": (-5, 25),
        "temp_range_f": (23, 77),
        "humidity": (45, 75),
    },
    "chicago": {
        "conditions": ["Windy", "Cloudy", "Sunny", "Snowy", "Rainy"],
        "temp_range_c": (-8, 28),
        "temp_range_f": (18, 82),
        "humidity": (50, 80),
    },
    "default": {
        "conditions": ["Partly Cloudy", "Sunny", "Cloudy"],
        "temp_range_c": (10, 25),
        "temp_range_f": (50, 77),
        "humidity": (40, 70),
    }
}


def extract_city(location: str) -> str:
    """
    Extract city name from location string.
    
    Args:
        location: Location string (e.g., "Seattle, WA" or "New York")
    
    Returns:
        Normalized city name
    """
    # Remove state/country codes and normalize
    city = location.split(',')[0].strip().lower()
    return city


def get_weather_data(location: str, unit: str = "fahrenheit") -> dict:
    """
    Generate mock weather data for the specified location.
    
    Args:
        location: City and state/country
        unit: Temperature unit (celsius or fahrenheit)
    
    Returns:
        Dictionary containing weather information
    """
    city = extract_city(location)
    
    # Get city-specific data or use default
    city_data = WEATHER_DATA.get(city, WEATHER_DATA["default"])
    
    # Generate random values within the city's typical range
    condition = random.choice(city_data["conditions"])
    
    if unit.lower() == "celsius":
        temp_min, temp_max = city_data["temp_range_c"]
        temp_unit = "°C"
    else:
        temp_min, temp_max = city_data["temp_range_f"]
        temp_unit = "°F"
    
    temperature = random.randint(temp_min, temp_max)
    humidity = random.randint(*city_data["humidity"])
    wind_speed = random.randint(5, 25)
    
    return {
        "location": location,
        "temperature": temperature,
        "temperature_unit": temp_unit,
        "condition": condition,
        "humidity": f"{humidity}%",
        "wind_speed": f"{wind_speed} mph",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "forecast": f"{condition} with a temperature of {temperature}{temp_unit}"
    }


def handler(event, context):
    """
    Lambda handler function for weather tool.
    
    The event structure from AgentCore Gateway includes the tool name and parameters.
    Gateway automatically prefixes the tool name with the target name (e.g., "weather_tool__get_weather").
    
    Args:
        event: Event data from AgentCore Gateway
        context: Lambda context
    
    Returns:
        Weather information or error response
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract parameters from the event
        # The event structure from Gateway may vary, so we handle both formats
        if isinstance(event, dict):
            # Check if we have tool parameters directly
            if 'location' in event:
                location = event.get('location')
                unit = event.get('unit', 'fahrenheit')
            # Or if they're nested in a parameters/arguments field
            elif 'parameters' in event:
                params = event['parameters']
                location = params.get('location')
                unit = params.get('unit', 'fahrenheit')
            elif 'arguments' in event:
                params = event['arguments']
                location = params.get('location')
                unit = params.get('unit', 'fahrenheit')
            else:
                # Try to find location in nested structures
                location = None
                unit = 'fahrenheit'
                logger.warning(f"Unexpected event structure: {event}")
        else:
            raise ValueError("Invalid event format")
        
        # Validate required parameters
        if not location:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: location',
                    'message': 'Please provide a location (e.g., "Seattle, WA")'
                })
            }
        
        # Get weather data
        weather = get_weather_data(location, unit)
        
        logger.info(f"Returning weather for {location}: {weather['condition']}, {weather['temperature']}{weather['temperature_unit']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'data': weather
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing weather request: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }