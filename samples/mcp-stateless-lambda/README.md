# Stateless MCP Server on AWS Lambda

This is a sample MCP Server running natively on AWS Lambda and API Gateway without any extra bridging components or custom transports. This is now possible thanks to the [Streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http) introduced in v2025-03-26.

The solution provides the CDK code to deploy the server on AWS, as well as a sample client to test the deployed server.

The original Terraform version of this sample is available [here](https://github.com/aws-samples/sample-serverless-mcp-servers/tree/main/stateless-mcp-on-lambda-nodejs)

## Overview

MCP Server can run in two modes - stateless and stateful. This repo demonstrates the stateless mode.

In stateless mode, clients do not establish persistent SSE connections to MCP Server. This means clients will not receive proactive notifications from the server. On the other hand, stateless mode allows you to scale your server horizontally.

This sample implements simple authorization demo with API Gateway Custom Authorizer.

![Architecture Diagram](./doc/architecture.png)

## Folder Structure

This sample application codebase is organized into folders : the backend code lives in ```bin/mcp-stateless-lambda.ts``` and uses the AWS CDK resources defined in the ```lib``` folder.

The key folders are:

```
samples/mcp-stateless-lambda
│
├── bin
│   └── mcp-stateless-lambda.ts               # Backend - CDK app
├── lib                                       # CDK Stacks
│   ├── mcp-stateless-lambda-stack.ts         # Stack deploying the resources
├── mcp_client                                # test mcp client to connect to the remote server
├── lambdas                                   # lambda functions
```

## Getting started

### Prerequisites

- An AWS account. We recommend you deploy this solution in a new account.
- [AWS CLI](https://aws.amazon.com/cli/): configure your credentials

```
aws configure --profile [your-profile] 
AWS Access Key ID [None]: xxxxxx
AWS Secret Access Key [None]:yyyyyyyyyy
Default region name [None]: us-east-1 
Default output format [None]: json
```

- Node.js: v18.12.1
- [AWS CDK](https://github.com/aws/aws-cdk/releases/tag/v2.114.0): 2.114.0
- jq: jq-1.6

### Deploy the solution

This project is built using the [AWS Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/). See [Getting Started With the AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) for additional details and prerequisites.

1. Clone this repository.

    ```shell
    git clone https://github.com/aws-samples/generative-ai-cdk-constructs-samples.git
    ```

2. Enter the code sample backend directory.

    ```shell
    cd samples/mcp-stateless-lambda
    ```

3. Install packages

   ```shell
   npm install
   ```

4. Install the dependencies

    ```shell
   (cd src/mcpclient && npm install)
   (cd src/mcpserver && npm install)
   ```

5. Boostrap AWS CDK resources on the AWS account.

    ```shell
    cdk bootstrap aws://ACCOUNT_ID/REGION
    ```

6. Deploy the sample in your account.

    ```shell
    $ cdk deploy
    ```

The command above will deploy one stack in your account. With the default configuration of this sample.

To protect you against unintended changes that affect your security posture, the AWS CDK Toolkit prompts you to approve security-related changes before deploying them. You will need to answer yes to get all the stack deployed.

7. Retrieve the value of the CfnOutput related to your remote MCP server endpoint from the stack

    ```shell
    $ aws cloudformation describe-stacks --stack-name McpStatelessLambdaStack --query "Stacks[0].Outputs[?contains(OutputKey, 'McpServerEndpoint')].OutputValue"

    [
        "OutputValue": "https://<endpoint>/dev/mcp"
    ]
    ```

8. Export an env variable named `MCP_SERVER_ENDPOINT` with the previous output value

    ```shell
    export MCP_SERVER_ENDPOINT='value'
    ```

### Test your remote MCP Server with MCP client

Use the provided mcp client to test your remote mcp server

```shell
node mcp_client/index.js
```

Observe the response:

```
Connecting ENDPOINT_URL=XXXXXXXX.amazonaws.com/dev/mcp
connected
listTools response:  { tools: [ { name: 'ping', inputSchema: [Object] } ] }
callTool:ping response:  {
  content: [
    {
      type: 'text',
      text: 'pong! logStream=2025/05/06/[$LATEST]7037eebd7f314fa18d6320801a54a50f v=0.0.12 d=49'
    }
  ]
}
callTool:ping response:  {
  content: [
    {
      type: 'text',
      text: 'pong! logStream=2025/05/06/[$LATEST]7037eebd7f314fa18d6320801a54a50f v=0.0.12 d=101'
    }
  ]
}
```

## Clean up

Do not forget to delete the stack to avoid unexpected charges.

```shell
    $ cdk destroy
```

Delete associated logs created by the different services in Amazon CloudWatch logs.

## Content Security Legal Disclaimer

The sample code; software libraries; command line tools; proofs of concept; templates; or other related technology (including any of the foregoing that are provided by our personnel) is provided to you as AWS Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.

## Operational Metrics Collection

This solution collects anonymous operational metrics to help AWS improve the quality and features of the solution. Data collection is subject to the AWS Privacy Policy (https://aws.amazon.com/privacy/). To opt out of this feature, simply remove the tag(s) starting with “uksb-” or “SO” from the description(s) in any CloudFormation templates or CDK TemplateOptions.
