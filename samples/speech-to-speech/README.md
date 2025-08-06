# Nova Sonic Solution

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Deployment](#deployment)
- [User creation](#user-creation)
- [Usage](#usage)
- [Load testing](#load-testing)
- [Clean Up](#clean-up)

## Overview

A real-time speech-to-speech communication platform powered by Amazon Bedrock's Nova model for advanced language processing and AWS real-time messaging capabilities, featuring a Java WebSocket server and React frontend. Nova enables natural, context-aware speech-to-speech conversations through its state-of-the-art language understanding and generation capabilities.

## Architecture

![Architecture Diagram](docs/images/architecture.png)

The solution consists of three main components:

1. **Frontend Application**
   - React + TypeScript application
   - Real-time WebSocket communication
   - AWS Amplify for authentication
   - Tailwind CSS for styling

2. **Backend Infrastructure**
   - AWS CDK for infrastructure as code
   - Java WebSocket server running on AWS Fargate
   - Amazon Cognito for user authentication
   - CloudFront for content delivery
   - S3 for static website hosting
   - Network Load Balancer for WebSocket traffic

3. **Development Tools**
   - Load testing suite for WebSocket performance testing
   - Automated deployment pipeline

## Project Structure

```
.
├── frontend/           # React + TypeScript frontend application
├── backend/           # AWS CDK infrastructure and Java WebSocket server
│   ├── app/          # Java WebSocket server implementation
│   ├── stack/        # CDK infrastructure code
│   └── load-test/    # WebSocket load testing suite
└── images/           # Architecture diagrams and documentation images
```

## Prerequisites

- [Python](https://www.python.org/downloads/) 3.11 or higher
- [Docker Desktop](https://docs.docker.com/desktop/install/)
- [Gradle](https://gradle.org/install/) 7.x or higher
- [Git](https://git-scm.com/downloads)
- [AWS CDK Toolkit](https://docs.aws.amazon.com/cdk/v2/guide/cli.html)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- Node.js 16.x or higher
- npm 8.x or higher
- Ensure you enable model access to Amazon Nova Sonic in the [Bedrock console](https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess) in the region you intend to deploy this sample. For an up to date list of supported regions for Amazon Nova Sonic, please refer to the [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html)
- Chrome, Safari, or Edge browser environment (Firefox is currently not supported)
- Microphone and speakers

## Regional Access Configuration

⚠️ **Important**: By default, this solution restricts CloudFront access to **US and Canada only**. International users will be blocked and see access denied errors.

To modify regional access for your deployment, edit the following file:
**File**: `backend/stack/stack_constructs/cloudfront_constructs.py`
**Line**: ~108

### Configuration Options:

**Current Default (US & Canada only):**
```python
geo_restriction=cloudfront.GeoRestriction.allowlist("US", "CA"),
```

**Allow Worldwide Access:**
```python
geo_restriction=cloudfront.GeoRestriction.allowlist(),  # Empty allowlist = worldwide access
```

**Allow Specific Countries (example: US, Canada, UK, Germany):**
```python
geo_restriction=cloudfront.GeoRestriction.allowlist("US", "CA", "GB", "DE"),
```

> **Note**: Use [ISO 3166-1 alpha-2 country codes](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) (e.g., "US", "CA", "GB", "DE", "JP", "AU").

## Deployment

1. If not done already, clone this repository:

   ```shell
   $ git clone https://github.com/aws-samples/generative-ai-cdk-constructs-samples.git
   ```

2. Enter the sample directory:

   ```shell
   $ cd samples/speech-to-speech
   ```

3. Build the frontend first:

   ```shell
   $ cd frontend
   ```

   Install dependencies:

   ```shell
   $ npm install
   ```

   Build the web application

   ```shell
   $ npm run build
   ```

The build output in `frontend/dist/` directory will be automatically deployed by the backend CDK stack to S3 and served through CloudFront. The environment variables are automatically configured by the `custom_resource_construct.py` in the CDK stack, which updates the frontend configuration during deployment.

4. Go to the backend directory:

   ```shell
   $ cd ../backend
   ```

5. Create a virtualenv on MacOS and Linux:

   ```shell
   $ python3 -m venv .venv
   ```

   After the init process completes and the virtualenv is created, you can use the following
   step to activate your virtualenv.

   ```shell
   $ source .venv/bin/activate
   ```

   If you are a Windows platform, you would activate the virtualenv like this:

   ```shell
   $ .venv\Scripts\activate.bat
   ```

6. Once the virtualenv is activated, you can install the required dependencies.

   ```shell
   $ pip install -r requirements.txt
   ```

7. Run the following to bootstrap your account:

   ```shell
   $ cdk bootstrap
   ```

8. Run AWS CDK Toolkit to deploy the Backend stack with the runtime resources.

   ```shell
   $ cdk deploy --require-approval=never
   ```

   Any modifications made to the code can be applied to the deployed stack by running the same command again.

   ```shell
   cdk deploy --require-approval=never
   ```

Get the CloudFront domain name:

```shell
aws cloudformation describe-stacks \
  --stack-name NovaSonicSolutionBackendStack \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionDomainName`].OutputValue' \
  --output text
```

The frontend can be accessed at the domain name above.

## User creation

First, locate the Cognito User Pool ID, through the AWS CLI:

```shell
$ aws cloudformation describe-stacks --stack-name NovaSonicSolutionBackendStack --query "Stacks[0].Outputs[?contains(OutputKey, 'UserPoolId')].OutputValue"

[
    "OutputValue": "<region>_a1aaaA1Aa"
]
```

1. Navigate to AWS Console:
2. Search for "Cognito" in the AWS Console search bar, Click on "Cognito" under Services, Click on "User Pools" in the left navigation.
   Find and click on the User Pool created by the CDK stack you recovered above.
3. In the User Pool dashboard, click "Users" in the left navigation. Click the "Create user" button and create user with password.

## Usage

1. Go to the application URL - `https://$CLOUDFRONT_URL/` (CloudFront domain from CDK outputs)
2. Click on "Speech to Speech" in the navigation menu.
3. Click the "Start Streaming" button. When prompted, allow access to your microphone.
4. Begin speaking - you should see your speech being transcribed in real-time on the UI
5. The assistant will automatically process your message and respond through speech
6. Click "Stop Streaming" when you're done

![Speech to Speech Interface](docs/images/speechToSpeech_home.png)
   
> Note: Ensure your microphone is properly connected and working before testing. The browser may require you to grant microphone permissions the first time you use the feature.

## Load testing

The [backend/load-test](backend/load-test/) directory contains [Artillery](https://www.artillery.io/docs) scripts for WebSocket performance testing. This will require the installation of [Artillery](https://www.artillery.io/docs/get-started/get-artillery).

1. Set up load testing:

   ```shell
   $ cd backend/load-test
   $ npm install
   $ ./setup-load-test.sh
   ```

2. Run load tests:

   ```shell
   $ ./run-load-test.sh
   ```

3. Generate HTML report

   ```shell
   $ artillery report report.json
   ```

## Clean Up

Do not forget to delete the stack to avoid unexpected charges.

```shell
cdk destroy NovaSonicSolutionBackendStack
```

Delete the associated logs created by the different services in Amazon CloudWatch logs.

Ensure S3 buckets are emptied before deletion.
