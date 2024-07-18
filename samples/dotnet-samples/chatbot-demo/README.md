
# .NET Samples!

This project showcases the utilization of the [Cdklabs.GenerativeAiCdkConstructs](https://www.nuget.org/packages/Cdklabs.GenerativeAiCdkConstructs) package from the nuget library. It encompasses exemplary implementations of critical components commonly required in generative AI applications. The [BedrockAgentStack.cs](./src/ChatbotDemo.Infrastructure/Stacks/BedrockAgentStack.cs) file orchestrates the synthesis of multiple constructs sourced from the [Cdklabs.GenerativeAiCdkConstructs](https://www.nuget.org/packages/Cdklabs.GenerativeAiCdkConstructs) library. Depending on your specific requirements, you may opt to selectively deploy only the constructs pertinent to your use case, rather than deploying the entirety of the available constructs.

It includes examples of key components needed in generative AI applications:

- [Amazon Bedrock](https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/src/cdk-lib/bedrock/README.md): CDK L2 Constructs for Amazon Bedrock.	

- [Amazon OpenSearch Serverless Vector Collection](https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/src/cdk-lib/opensearchserverless/README.md): CDK L2 Constructs to create a vector collection.

- [Amazon OpenSearch Vector Index](https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/src/cdk-lib/opensearch-vectorindex/README.md): CDK L1 Custom Resource to create a vector index.		

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

- Python : v3.11
- [AWS CDK](https://github.com/aws/aws-cdk/releases/tag/v2.68.0): 2.68.0
- [Docker](https://www.docker.com/products/docker-desktop/): Docker must be up and running in your machine.

## Getting started

You should explore the contents of this project. It demonstrates a CDK app with an instance of the following stacks (`BedrockAgentStack`, `BedrockGuardrailStack`, `WebSocketStack`)

The `cdk.json` file tells the CDK Toolkit how to execute your app.

It uses the [.NET Core CLI](https://docs.microsoft.com/dotnet/articles/core/) to compile and execute your project.

## Useful commands

* `dotnet build src` compile this app
* `cdk ls`           list all stacks in the app
* `cdk synth`       emits the synthesized CloudFormation template
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk docs`        open CDK documentation

Enjoy!
