#!/bin/bash

# Source environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    set -a
    source .env
    set +a
else
    echo "Error: .env file not found"
    echo "Please run ./setup-load-test.sh first to create the .env file"
    exit 1
fi

# Verify environment variables are set
if [ -z "$AWS_REGION" ] || [ -z "$COGNITO_CLIENT_ID" ] || [ -z "$TEST_USERNAME" ] || [ -z "$TEST_PASSWORD" ] || [ -z "$WS_URL" ]; then
    echo "Error: Required environment variables are not set in .env file"
    echo "Required variables:"
    echo "  - AWS_REGION"
    echo "  - COGNITO_CLIENT_ID"
    echo "  - TEST_USERNAME"
    echo "  - TEST_PASSWORD"
    echo "  - WS_URL"
    echo "Please run ./setup-load-test.sh to regenerate the .env file"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Run the load test
echo "Starting load test..."
echo "Target WebSocket URL: $WS_URL"
echo "Region: $AWS_REGION"

npx artillery run \
    --output report.json \
    artillery-websocket.yml

# Generate HTML report
npx artillery report \
    --output report.html \
    report.json

echo "Load test completed. Check report.html for results."
