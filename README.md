# Sample Apps for AWS Generative AI CDK Constructs

This repo provides samples to demonstrate how to build your own Generative AI solutions using [AWS Generative AI CDK Constructs](https://github.com/awslabs/generative-ai-cdk-constructs).

## Getting started

|Use Case|Description|Type|Language|
|-|-|-|-|
|[SageMaker JumpStart model](samples/sagemaker_jumpstart_model/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a Llama 2 foundation model developed by Meta from Amazon JumpStart, and an AWS Lambda function to run inference requests against that endpoint.|Backend|TypeScript|
|[SageMaker Hugging Face model](samples/sagemaker_huggingface_model/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a model (Mistral 7B) from Hugging Face, and an AWS Lambda function to run inference requests against that endpoint.|Backend|TypeScript|
|[SageMaker Hugging Face model on AWS Inferentia2](samples/sagemaker_huggingface_inferentia/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a model (Zephyr 7B) from Hugging Face, and an AWS Lambda function to run inference requests against that endpoint. This sample uses Inferentia 2 as the hardware accelerator.|Backend|TypeScript|
|[SageMaker custom endpoint](samples/sagemaker_custom_endpoint/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a model with artifacts stored in an Amazon Simple Storage Service (S3) bucket, and an AWS Lambda function to run inference requests against that endpoint. This sample uses Inferentia2 as the hardware accelerator. |Backend|TypeScript|
|[SageMaker multimodal custom endpoint](samples/sagemaker_huggingface_model_llava/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting llava-1.5-7b, with artifacts stored in an Amazon Simple Storage Service (S3) bucket, a custom inference script, and an AWS Lambda function to run inference requests against that endpoint. |Backend|TypeScript|
|[SageMaker image to video endpoint](samples/sagemaker_huggingface_model_svd/)| This sample provides a sample application which deploys a SageMaker async endpoint hosting stable-video-diffusion-img2vid-xt-1-1, with artifacts stored in an Amazon Simple Storage Service (S3) bucket, a custom inference script, and an AWS Lambda function to run inference requests against that endpoint. |Backend|TypeScript|
|[LLM on SageMaker in GovCloud PDT](samples/llm-on-govcloud-sagemaker/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting Falcon-40b on GovCloud PDT. |Backend|TypeScript|
|[Amazon Bedrock Agents](samples/bedrock-agent/)| This sample provides a sample application which deploys an Amazon Bedrock Agent and Knowledge Base backed by an OpenSearch Serverless Collection and documents in S3. It demonstrates how to use the [Amazon Bedrock CDK construct](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/cdk-lib/bedrock). |Backend|TypeScript|
|[Python Samples](samples/python-samples/)| This project showcases the utilization of the 'generative-ai-cdk-constructs' package from the Python Package Index (PyPI).| Backend | Python|
|[.NET Samples](samples/dotnet-samples/)| This project showcases the utilization of the 'Cdklabs.GenerativeAiCdkConstructs' package from nuget library.| Backend | .NET|
|[Contract Compliance Analysis](samples/contract-compliance-analysis/)| This project automates the analysis of contracts by splitting them into clauses, determining clause types, evaluating compliance against a customer's legal guidelines, and assessing overall contract risk based on the number of compliant clauses. This is achieved through a workflow that leverages Large Language Models via Amazon Bedrock. | Backend + Frontend | Python for Backend, TypeScript (React) for Frontend |
|[RFP Answers with GenAI](samples/rfp-answer-generation/)| This project provides guidance on how you can use Knowledge Bases for Amazon Bedrock with custom transformations to create draft answers for Request for Proposal (RFP) documents, streamlining the answer of new potential contracts. This is achieved through a workflow that leverages Large Language Models via Amazon Bedrock. | Backend + Frontend | Python for Backend, TypeScript (React) for Frontend |
| [Code Expert](samples/code-expert/)                                                          | This project addresses the scalability limitations of manual code reviews by leveraging artificial intelligence to perform expert code reviews automatically. It leverages the [Bedrock Batch Step Functions CDK construct](https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/src/patterns/gen-ai/aws-bedrock-batch-stepfn/README.md). | Backend            | Python for Backend and Demo, TypeScript for CDK     |
|[Bedrock Agent UI Wrapper](samples/bedrock-agent-ui-wrapper/)| This sample provides a CDK construct that creates an API layer and frontend application for Amazon Bedrock Agents. It includes authentication with Amazon Cognito, agent trace streaming, and can be deployed locally or on ECS Fargate. | API layer + Frontend | Python|


## Contributing

Please refer to the [CONTRIBUTING](CONTRIBUTING.md) document for further details on contributing to this repository. 
