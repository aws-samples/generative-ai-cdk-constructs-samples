# WebSocket Load Testing Suite

This suite provides tools for load testing the WebSocket audio streaming service using Artillery.io.

## Prerequisites

- Node.js 14+
- AWS CLI configured with appropriate credentials
- Artillery.io (`npm install -g artillery`)
- The NovaSonic stack must be deployed to AWS in us-east-1 region

## Running the Load Test

1. Set up the test environment:
```bash
./setup-load-test.sh
```
This script will:
- Fetch necessary configuration from your deployed stack
- Create a test user in Cognito
- Generate a .env file with all required values

2. Execute the test:
```bash
./run-load-test.sh
```

The test will:
- Ramp up to 100 concurrent users over 5 minutes
- Maintain 100 concurrent users for 10 minutes
- Each user will send 100 simulated audio packets

## Test Phases

1. Warm-up Phase (2 minutes):
   - Start with 1 user
   - Ramp up to 10 users

2. Gradual Ramp-up (5 minutes):
   - Start with 10 users
   - Ramp up to 50 users

3. Medium Load (5 minutes):
   - Start with 50 users
   - Ramp up to 100 users

4. Peak Load (10 minutes):
   - Maintain 100 concurrent users

5. Cool Down (3 minutes):
   - Decrease from 100 to 10 users

## Test Results

After the test completes, two files are generated:
- `report.json`: Raw test results
- `report.html`: HTML report with visualizations

The HTML report includes:
- Connection success rates
- Message latency statistics
- Concurrent user graphs
- Error rates and types
- Detailed performance metrics

## Success Criteria

The test is considered successful if:
- Message latency remains under 1000ms
- Connection success rate is above 95%
- Error rate stays below 5%

## Troubleshooting

1. Setup Issues:
   - Ensure AWS CLI is configured correctly
   - Verify the stack is deployed successfully
   - Check if you have necessary permissions

2. Authentication Issues:
   - Run setup-load-test.sh again to recreate the test user
   - Check token expiration in functions.js
   - Verify Cognito user pool settings

3. Connection Issues:
   - Verify WebSocket endpoint URL in .env file
   - Check security group settings
   - Verify NLB health checks

4. Performance Issues:
   - Check ECS task scaling
   - Review ECS service logs
   - Analyze Artillery reports for bottlenecks

## Files Overview

- `setup-load-test.sh`: Configures the test environment
- `run-load-test.sh`: Executes the load test
- `artillery-websocket.yml`: Test scenarios and configuration
- `functions.js`: Custom test functions
- `.env`: Environment variables (auto-generated)
