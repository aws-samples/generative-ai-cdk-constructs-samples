#!/bin/bash

# Get the Lambda function name from the CDK stack output
LAMBDA_NAME=$(aws cloudformation describe-stacks \
  --stack-name cdk-lambda-strands-durable-demo-app-one \
  --query 'Stacks[0].Outputs[?OutputKey==`PythonLambdaName`].OutputValue' \
  --output text)

if [ -z "$LAMBDA_NAME" ]; then
  echo "Error: Could not retrieve PythonLambdaName from stack cdk-lambda-strands-durable-demo-app-one"
  exit 1
fi

# Durable Lambda functions require a qualified ARN (with version, alias, or $LATEST)
# Append :$LATEST to make it a qualified identifier
QUALIFIED_LAMBDA_NAME="${LAMBDA_NAME}:\$LATEST"

echo "Invoking Lambda function: $QUALIFIED_LAMBDA_NAME"

aws lambda invoke \
  --function-name "$QUALIFIED_LAMBDA_NAME" \
  --cli-binary-format raw-in-base64-out \
  --payload '{"prompt": "What is the weather in Seattle?"}' \
  response.json