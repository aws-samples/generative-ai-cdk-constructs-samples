# Sample Apps for AWS Generative AI CDK Constructs

This repo provides samples to demonstrate how to build your own Generative AI solutions using [AWS Generative AI CDK Constructs](https://github.com/awslabs/generative-ai-cdk-constructs).

## Getting started

|Use Case|Description|Type|Language|
|-|-|-|-|
|[Document Explorer](samples/document_explorer/)| This sample provides an end-to-end experience that allows a user to ingest documents into a knowledge base, then summarize and ask questions against those documents.| Backend + Frontend |TypeScript for Backend, Python for Frontend ([Streamlit](https://streamlit.io/))|
|[Content Generation](samples/content-generation/)| This sample provides an end-to-end experience that allows a user to generate images from text using Amazon titan-image-generator-v1 or stability stable-diffusion-xl model.| Backend + Frontend |TypeScript for Backend, Python for Frontend ([Streamlit](https://streamlit.io/))|
|[Image Description](samples/image-description/)| This sample provides an end-to-end experience that allows a user to generate descriptive text for uploaded images.| Backend + Frontend |TypeScript for Backend, Python for Frontend ([Streamlit](https://streamlit.io/))|
|[SageMaker JumpStart model](samples/sagemaker_jumpstart_model/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a Llama 2 foundation model developed by Meta from Amazon JumpStart, and an AWS Lambda function to run inference requests against that endpoint.|Backend|TypeScript|
|[SageMaker Hugging Face model](samples/sagemaker_huggingface_model/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a model (Mistral 7B) from Hugging Face, and an AWS Lambda function to run inference requests against that endpoint.|Backend|TypeScript|
|[SageMaker Hugging Face model on AWS Inferentia2](samples/sagemaker_huggingface_inferentia/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a model (Zephyr 7B) from Hugging Face, and an AWS Lambda function to run inference requests against that endpoint. This sample uses Inferentia 2 as the hardware accelerator.|Backend|TypeScript|
|[SageMaker custom endpoint](samples/sagemaker_custom_endpoint/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting a model with artifacts stored in an Amazon Simple Storage Service (S3) bucket, and an AWS Lambda function to run inference requests against that endpoint. This sample uses Inferentia2 as the hardware accelerator. |Backend|TypeScript|
|[SageMaker multimodal custom endpoint](samples/sagemaker_huggingface_model_llava/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting llava-1.5-7b, with artifacts stored in an Amazon Simple Storage Service (S3) bucket, a custom inference script, and an AWS Lambda function to run inference requests against that endpoint. |Backend|TypeScript|
|[LLM on SageMaker in GovCloud PDT](samples/llm-on-govcloud-sagemaker/)| This sample provides a sample application which deploys a SageMaker real-time endpoint hosting Falcon-40b on GovCloud PDT. |Backend|TypeScript|
|[Amazon Bedrock Agents](samples/bedrock-agent/)| This sample provides a sample application which deploys an Amazon Bedrock Agent and Knowledge Base backed by an OpenSearch Serverless Collection and documents in S3. It demonstrates how to use the [Amazon Bedrock CDK construct](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/cdk-lib/bedrock). |Backend|TypeScript|
|[Python Samples](samples/python-samples/)| This project showcases the utilization of the 'generative-ai-cdk-constructs' package from the Python Package Index (PyPI).| Backend | Python|

## Contributing

Please refer to the [CONTRIBUTING](CONTRIBUTING.md) document for further details on contributing to this repository. 
