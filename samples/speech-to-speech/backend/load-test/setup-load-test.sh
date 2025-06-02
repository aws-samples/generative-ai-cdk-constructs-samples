#!/bin/bash

# Exit on error
set -e

# Set AWS region
export AWS_REGION="us-east-1"

echo "Setting up load test environment..."
echo "Using AWS Region: $AWS_REGION"

# Get stack name from cdk.json
STACK_NAME=$(cat ../cdk.json | jq -r '.context.stackName // "NovaSonicSolutionBackendStack"')

# Get outputs from CloudFormation stack
echo "Fetching stack outputs..."
STACK_OUTPUTS=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs' --output json)

# Extract values from stack outputs
COGNITO_CLIENT_ID=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey | endswith("UserPoolClientId")) | .OutputValue')
COGNITO_USER_POOL_ID=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey | endswith("UserPoolId")) | .OutputValue')
WS_URL=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey | endswith("CloudFrontDistributionDomainName")) | .OutputValue')

# Verify we got all required values
if [ -z "$COGNITO_CLIENT_ID" ] || [ -z "$COGNITO_USER_POOL_ID" ] || [ -z "$WS_URL" ]; then
    echo "Error: Could not fetch all required values from stack outputs"
    echo "COGNITO_CLIENT_ID: $COGNITO_CLIENT_ID"
    echo "COGNITO_USER_POOL_ID: $COGNITO_USER_POOL_ID"
    echo "WS_URL: $WS_URL"
    exit 1
fi

# Convert HTTP URL to WebSocket URL
WS_URL="wss://$WS_URL/interact-s2s"

# Create test user if it doesn't exist
TEST_USERNAME="loadtest_user"
TEST_PASSWORD="LoadTest123!"

echo "Creating test user if it doesn't exist..."
if ! aws cognito-idp admin-get-user \
    --region $AWS_REGION \
    --user-pool-id $COGNITO_USER_POOL_ID \
    --username $TEST_USERNAME >/dev/null 2>&1; then
    
    aws cognito-idp admin-create-user \
        --region $AWS_REGION \
        --user-pool-id $COGNITO_USER_POOL_ID \
        --username $TEST_USERNAME \
        --temporary-password $TEST_PASSWORD \
        --message-action SUPPRESS

    # Set permanent password
    aws cognito-idp admin-set-user-password \
        --region $AWS_REGION \
        --user-pool-id $COGNITO_USER_POOL_ID \
        --username $TEST_USERNAME \
        --password $TEST_PASSWORD \
        --permanent
fi

# Create .env file
echo "Creating .env file..."
cat > .env << EOL
AWS_REGION=us-east-1
COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID
TEST_USERNAME=$TEST_USERNAME
TEST_PASSWORD=$TEST_PASSWORD
WS_URL=$WS_URL
EOL

echo "Load test environment setup complete!"
echo "Created .env file with the following values:"
echo "----------------------------------------"
cat .env
echo "----------------------------------------"
echo "You can now run './run-load-test.sh' to start the load test."
