from strands import Agent
from strands.models import BedrockModel
from strands_tools import http_request
from typing import Dict, Any
from aws_durable_execution_sdk_python import (
    durable_execution,
    DurableContext,
    durable_step,
    StepContext,
)
import os

# Define a weather-focused system prompt
WEATHER_SYSTEM_PROMPT = """You are a weather assistant with HTTP capabilities. You can:

1. Make HTTP requests to the National Weather Service API
2. Process and display weather forecast data
3. Provide weather information for locations in the United States

When retrieving weather information:
1. First get the coordinates or grid information using https://api.weather.gov/points/{latitude},{longitude} or https://api.weather.gov/points/{zipcode}
2. Then use the returned forecast URL to get the actual forecast

When displaying responses:
- Format weather data in a human-readable way
- Highlight important information like temperature, precipitation, and alerts
- Handle errors appropriately
- Convert technical terms to user-friendly language

Always explain the weather conditions clearly and provide context for the forecast.
"""

@durable_step
def run_agent(step_context: StepContext, prompt: str, model_id: str) -> str:
    """
    Execute the weather agent as a durable step.
    This step is checkpointed, so if execution is interrupted, it can resume from here.
    """
    # Create a Bedrock model instance
    bedrock_model = BedrockModel(
        model_id=model_id,
        temperature=0.3,
    )

    weather_agent = Agent(
        system_prompt=WEATHER_SYSTEM_PROMPT,
        tools=[http_request],
        model=bedrock_model,
    )

    # Execute the agent - this is checkpointed automatically
    response = weather_agent(prompt)
    return str(response)

@durable_execution
def handler(event: dict, context: DurableContext) -> str:
    """
    Durable execution handler that uses steps for checkpointing.
    If the Lambda times out or fails, execution can resume from the last checkpoint.
    """
    model_id = os.environ.get('MODEL_ID', 'global.anthropic.claude-sonnet-4-5-20250929-v1:0')
    if not model_id:
        raise ValueError('MODEL_ID environment variable is not set')

    # Extract prompt from event
    prompt = event.get('prompt') or event.get('message') or event.get('input')
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('Event must contain a "prompt", "message", or "input" field with a non-empty string value')

    # Execute the agent as a durable step
    # This step is checkpointed, so if execution is interrupted, it can resume
    response = context.step(run_agent(prompt, model_id))
    return response