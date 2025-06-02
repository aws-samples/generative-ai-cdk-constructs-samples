# Nova Sonic Solution Backend

The backend infrastructure for the Nova Sonic Solution, built with AWS CDK and Java WebSocket server.

## Project Structure

```
backend/
├── app/                    # Java WebSocket Server
│   ├── src/               # Source code
│   │   └── main/
│   │       ├── java/     # Java implementation
│   │       └── resources/ # Configuration files
│   └── build.gradle.kts   # Gradle build configuration
├── stack/                 # AWS CDK Infrastructure
│   ├── __init__.py       # Main stack definition
│   ├── lambdas/          # Lambda function implementations
│   └── stack_constructs/ # CDK construct implementations
├── load-test/            # Load Testing Suite
│   ├── artillery-websocket.yml  # Test scenarios
│   ├── functions.js      # Test functions
│   └── setup-load-test.sh # Test setup script
├── nova/                 # Additional resources
├── cdk.json             # CDK configuration
└── Dockerfile           # Container definition
```

## Architecture Components

### AWS Infrastructure (CDK)

1. **VPC Configuration**
   - Custom VPC with public and private subnets
   - NAT Gateways for outbound internet access
   - Security groups for Fargate services

2. **Container Infrastructure**
   - AWS Fargate for running the WebSocket server
   - Network Load Balancer for WebSocket traffic
   - ECR repository for Docker images
   - Auto-scaling configuration

3. **Authentication & Security**
   - Amazon Cognito User Pool
   - User Pool Client for frontend integration
   - Server access logging bucket
   - CloudFront distribution with SSL/TLS

4. **Static Website Hosting**
   - S3 bucket for frontend assets
   - CloudFront distribution for content delivery
   - Custom resource for configuration updates

### Java WebSocket Server

- Java-based WebSocket server implementation
- Real-time speech-to-speech communication
- Cognito token validation
- Connection management
- Error handling and logging

## Development Setup

### Prerequisites

1. AWS CLI configured with appropriate permissions
2. AWS CDK CLI installed globally
3. Java 17 or later
4. Docker installed and running
5. Node.js 18.x or later (for CDK)

### AWS Deployment

1. Build the frontend first (see [Frontend Build Instructions](../frontend/README.md#aws-deployment))

```
cd NovaSonicSolution/backend
```

2. Set up Python virtual environment:
   ```bash
   # Create virtual environment
   python -m venv .venv

   # Activate virtual environment
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install and configure AWS CDK:
   ```bash
   # Install AWS CDK globally if not already installed
   npm install -g aws-cdk

   # Bootstrap CDK (first time only, replace ACCOUNT-NUMBER and REGION)
   cdk bootstrap aws://ACCOUNT-NUMBER/REGION
   ```

5. Deploy the stack:
   ```bash
   cdk deploy
   ```

6. Note the outputs for:
   - CloudFront distribution domain
   - Cognito User Pool ID
   - Cognito Client ID
   - Load Balancer DNS

7. For instructions on accessing the deployed application, see [Application Testing Guide](../frontend/README.md#application-testing)

### Local Development

1. Build and run with Docker:
   ```bash
   # Build the Docker image
   docker build -t nova-sonic-backend .
   
   # Run the container locally
   docker run -p 8080:8080 nova-sonic-backend
   
   # Check container health
   docker ps --filter "name=nova-sonic-backend" --format "{{.Status}}"
   
   # View container logs
   docker logs -f nova-sonic-backend
   
   # Check container resource usage
   docker stats nova-sonic-backend
   ```

2. Alternative: Build and run without Docker:
   ```bash
   # Build the Java application
   ./gradlew build
   
   # Run locally
   ./gradlew run
   ```

## Load Testing

The `load-test` directory contains Artillery scripts for WebSocket performance testing.

1. Set up load testing:
   ```bash
   cd load-test
   npm install
   ./setup-load-test.sh
   ```

2. Run load tests:
   ```bash
   ./run-load-test.sh
   ```
3. Generate HTML report

```
artillery report report.json
```

## Security Best Practices

1. **CDK Nag Integration**
   - AWS Solutions security checks enabled
   - Automated security best practice validation
   - Suppression documentation required

2. **Network Security**
   - Private subnets for Fargate tasks
   - Security group restrictions
   - SSL/TLS encryption for all traffic

3. **Authentication**
   - Cognito token validation
   - Secure WebSocket connections
   - User session management

## Monitoring and Logging

1. **CloudWatch Integration**
   - Container logs
   - WebSocket connection metrics
   - Custom metrics for speech processing

2. **Access Logging**
   - S3 access logs
   - CloudFront logs
   - Load balancer access logs

## Infrastructure Updates

1. Make changes to CDK stack in `stack/` directory
2. Update Java application in `app/` directory
3. Run tests:
   ```bash
   ./gradlew test
   ```
4. Deploy changes:
   ```bash
   cdk diff  # Review changes
   cdk deploy
   ```

## Troubleshooting

1. **Connection Issues**
   - Verify security group settings
   - Check NLB health checks
   - Validate WebSocket URL format

2. **Deployment Failures**
   - Review CloudFormation events
   - Check CDK synthesis output
   - Verify IAM permissions

3. **Container Issues**
   - Check ECS task logs
   - Verify container health checks
   - Review resource allocation

## Contributing

1. Follow Java code style guidelines
2. Update tests for new features
3. Document infrastructure changes
4. Update load tests as needed
5. Create detailed pull requests

## Clean up

Before destroying the stack, perform these cleanup steps in order:

1. Remove all data from the Amazon Simple Storage Service (Amazon S3) buckets:
   - Frontend static assets bucket
   - Access logging bucket
   - Any other S3 buckets created by the stack

2. Delete CloudWatch logs:
   - Navigate to CloudWatch in the AWS Console
   - Find and delete the following log groups:
     - `/aws/fargate/nova-sonic` (WebSocket server logs)
     - `/aws/lambda/*` (any Lambda function logs)
     - `/aws/cloudfront/*` (CloudFront access logs)
     - Any other log groups created during testing

3. Destroy the stack:
   ```shell
   cdk destroy
   ```

4. After stack deletion, verify:
   - All CloudWatch log groups are deleted
   - All S3 buckets are removed
   - All ECR repositories are cleaned up
   - No orphaned resources remain in your AWS account
