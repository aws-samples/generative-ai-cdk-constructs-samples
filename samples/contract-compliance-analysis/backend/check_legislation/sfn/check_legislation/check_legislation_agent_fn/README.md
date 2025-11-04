# Check Legislation Agent Lambda Function

This Lambda function serves as a bridge between AWS Step Functions and Bedrock AgentCore, since AgentCore is not yet supported in Step Functions' CallAwsService integration.

## Purpose

The function receives input from Step Functions, invokes a Bedrock AgentCore runtime agent, and returns the agent's response back to the Step Functions workflow.

## Environment Variables

- `AGENT_RUNTIME_ARN`: The ARN of the Bedrock AgentCore runtime agent to invoke

## Dependencies

- `boto3 ^1.40.5`: Required for Bedrock AgentCore support
- `python ^3.13`: Lambda runtime version

## Usage

This function is automatically invoked by the Step Functions workflow as part of the legislation checking process. It:

1. Receives the Step Functions event as input
2. Encodes the event as base64 JSON payload
3. Invokes the AgentCore runtime with the payload
4. Returns the agent's response to Step Functions

## Development

Dependencies are managed using Poetry. The `pyproject.toml` file defines the required packages.
