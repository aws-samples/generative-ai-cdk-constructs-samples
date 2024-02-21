# SageMaker custom model deployment

## Overview

The "SageMaker Custom model deployment" sample generative AI application demonstrates how to deploy and interact with a model where artifacts are stored in an Amazon Simple Storage Service (S3) bucket, leveraging AWS services and [AWS Generative AI CDK Constructs](https://github.com/awslabs/generative-ai-cdk-constructs).

Specifically, this sample deploys an AWS Lambda function which interacts with a SageMaker real-time endpoint, hosting [bge-base-en-v1.5](https://huggingface.co/BAAI/bge-base-en-v1.5) to generate embeddings on AWS Inferentia2. 

If you are interested to learn more about training and deploying models using [AWS Trainium](https://aws.amazon.com/machine-learning/trainium/) and [AWS Inferentia](https://aws.amazon.com/machine-learning/inferentia/), this [workshop](https://github.com/aws-samples/ml-specialized-hardware/tree/main) provides several accelerators and tutorials.

By providing reusable constructs following AWS best practices, this app helps you quickly build custom generative AI apps on AWS.

Here is the architecture diagram of the sample application:

![Architecture Diagram](./doc/images/architecture.png)

## Folder Structure

This sample application codebase is organized into folders : the backend code lives in ```bin/sagemaker_custom_model.ts``` and uses the AWS CDK resources defined in the ```lib``` folder.

The key folders are:

```
samples/sagemaker_custom_model
│
├── bin
│   └── sagemaker_custom_model.ts             # Backend - CDK app
├── lib                                       # CDK Stacks
│   ├── sagemaker_custom_model-stack.ts       # Stack deploying the AWS Lambda function and SageMaker real-time endpoint
```

## Getting started

> **Warning**
> Warning This sample allows you to interact with models from third party providers. Your use of the third-party generative AI (GAI) models is governed by the terms provided to you by the third-party GAI model providers when you acquired your license to use them (for example, their terms of service, license agreement, acceptable use policy, and privacy policy).

> You are responsible for ensuring that your use of the third-party GAI models comply with the terms governing them, and any laws, rules, regulations, policies, or standards that apply to you.

> You are also responsible for making your own independent assessment of the third-party GAI models that you use, including their outputs and how third-party GAI model providers use any data that might be transmitted to them based on your deployment configuration. AWS does not make any representations, warranties, or guarantees regarding the third-party GAI models, which are “Third-Party Content” under your agreement with AWS. This sample is offered to you as “AWS Content” under your agreement with AWS.

### Prepare your model

First, you need to prepare the model to run on the AWS Inferentia2 hardware. For this, you can follow steps 1 to 3 from this [blog post](https://www.philschmid.de/inferentia2-embeddings). Save the location where your model artifacts are saved.

> Note
> This sample was tested in the region us-east-2. The Amazon S3 bucket containing your model artifacts needs to be in the same region where your real-time endpoint is deployed.

To deploy this sample application, follow these steps to set up the required tools and configure your AWS environment:

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
- Make sure you have sufficient quota for the instance type implemented in this sample (service Amazon SageMaker, instance type `ml_inf2_xlarge` for endpoint usage). For more information, refer to [AWS service quotas](https://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html).

### Deploy the solution

This project is built using the [AWS Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/). See [Getting Started With the AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) for additional details and prerequisites.

1. Clone this repository.
    ```shell
    git clone https://github.com/aws-samples/generative-ai-cdk-constructs-samples.git
    ```

2. Enter the code sample backend directory.
    ```shell
    cd samples/sagemaker_custom_model
    ```

3. Update the location of your model artifacts. Update in [sagemaker_custom_endpoint-stack.ts](./lib/sagemaker_custom_endpoint-stack.ts) the field ```modelDataUrl``` to specify the location where your saved your model artifacts during the [prepare your model](#prepare-your-model) step. The field should look like this: ```s3//BUCKET//KEY```. Also, replace the bucket arn field (```BUCKET_ARN```) in the same file with the ARN of the Amazon S3 bucket containing your model artifacts. This will give the permissions to the construct to pull your model artifacts.

3. Boostrap AWS CDK resources on the AWS account.
    ```shell
    cdk bootstrap aws://ACCOUNT_ID/REGION
    ```

6. Deploy the sample in your account. 
    ```shell
    $ cdk deploy
    ```

The command above will deploy one stack in your account. With the default configuration of this sample, the observed deployment time was ~381 seconds (6.5 minutes).

To protect you against unintended changes that affect your security posture, the AWS CDK Toolkit prompts you to approve security-related changes before deploying them. You will need to answer yes to get all the stack deployed.

### Test

- In the AWS console, navigate to [AWS Lambda](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions?sb=lastModified&so=DESCENDING) and select the function named ```testbgecustom```

- Under the Code tab, click ```Test```. This will send a request to the SageMaker endpoint, and display the result. 

- You can update the parameters and prompt sent to the endpoint in the ```dic``` (file lambda.py) structure.

## Clean up

Do not forget to delete the stack to avoid unexpected charges.

First make sure to remove all data from the Amazon Simple Storage Service (Amazon S3) Bucket.

```shell
    $ cdk destroy
```

Delete all the associated logs created by the different services in Amazon CloudWatch logs

# Content Security Legal Disclaimer
The sample code; software libraries; command line tools; proofs of concept; templates; or other related technology (including any of the foregoing that are provided by our personnel) is provided to you as AWS Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.

# Operational Metrics Collection
This solution collects anonymous operational metrics to help AWS improve the quality and features of the solution. Data collection is subject to the AWS Privacy Policy (https://aws.amazon.com/privacy/). To opt out of this feature, simply remove the tag(s) starting with “uksb-” or “SO” from the description(s) in any CloudFormation templates or CDK TemplateOptions.
