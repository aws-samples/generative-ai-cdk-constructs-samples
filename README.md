# Sample Apps for AWS Generative AI CDK Constructs

This repo provides samples to demonstrate how to build your own Generative AI solutions using [AWS Generative AI CDK Constructs](https://github.com/awslabs/generative-ai-cdk-constructs).

## Getting started

|Use Case|Description|Language|
|-|-|-|
|[Document Explorer](samples/document_explorer/)| This sample provides an end-to-end experience that allows a user to ingest documents into a knowledge base, then summarize and ask questions against those documents.|TypeScript|
|[SageMaker JumpStart model](samples/sagemaker_jumpstart_model/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a Llama 2 foundation model developed by Meta from Amazon JumpStart, and an AWS Lambda function to run inference requests against that endpoint.|TypeScript|
|[SageMaker Hugging face model](samples/sagemaker_huggingface_model/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a model (Mistral 7B) from Hugging Face, and an AWS Lambda function to run inference requests against that endpoint.|TypeScript|
|[SageMaker Hugging face model on AWS Inferentia 2](samples/sagemaker_huggingface_inferentia/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a model (Zephyr 7B) from Hugging Face, and an AWS Lambda function to run inference requests against that endpoint. This sample uses Inferentia 2 as the hardware accelerator.|TypeScript|
|[SageMaker custom endpoint](samples/sagemaker_custom_endpoint/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a model with artifacts stored in an Amazon Simple Storage Service (S3) bucket, and an AWS Lambda function to run inference requests against that endpoint. This sample uses Inferentia 2 as the hardware accelerator. |TypeScript|
|[Bedrock Agents](samples/bedrock-agent/)| This sample provides a sample application which deploys a Bedrock Agent and Knowledge Base backed by an OpenSearch Serverless Collection and documents in S3. It demonstrates how to use the [Bedrock CDK construct](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/cdk-lib/bedrock). |TypeScript|

## Contributing

Please refer to the [CONTRIBUTING](CONTRIBUTING.md) document for further details on contributing to this repository.
