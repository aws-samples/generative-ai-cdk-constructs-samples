# Document explorer

## Overview

The Sample Generative AI Application demonstrates how to build end-to-end solutions leveraging AWS services and the [Generative AI Constructs library](https://github.com/awslabs/generative-ai-cdk-constructs).

It includes examples of key components needed in generative AI applications:

- [Data Ingestion Pipeline](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-rag-appsync-stepfn-opensearch): Ingests documents, converts them to text, and stores them in a knowledge base for retrieval. This enables long context window approaches.

- [Document Summarization](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-summarization-appsync-stepfn): Summarizes PDF documents leveraging Large Language Models like Anthropic Claude V2 via Amazon Bedrock. 

- [Question Answering](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-qa-appsync-opensearch): Answers natural language questions by retrieving relevant documents from the knowledge base and leveraging Large Language Models.

By providing reusable constructs following AWS best practices, this app enables quickly building custom generative AI apps on AWS. The constructs abstract complexity of orchestrating AWS services like Lambda, OpenSearch, Step Functions, Bedrock, etc.

Here is the architecture diagram of the sample application:

![Architecture Diagram](docs/images/architecture.png)

## Folder Structure

This document explorer codebase is organized into folders containing the ```frontend``` and ```backend``` infrastructure code. The frontend client app is built with [Streamlit](https://streamlit.io/) and located in the ```client_app``` folder. The backend code lives in ```bin/document_explorer.ts``` and uses the AWS CDK resources defined in the ```lib``` folder.

If you need more information about 

The key folders are:

```
samples/document_explorer
├── client_app                                   # Frontend using Python Streamlit
│   │
│   ├── Home.ts                                  # Sample app entry point
│   ├── assets/                                  # Static files
│   ├── common/                                  # Utility classes
│   ├── graphql/                                 # GraphQL statements and client
│   └── pages/                                   # Streamlit pages for document selection, summarization, and QA
│
├── bin
│   └── document_explorer.ts                     # Backend - CDK app
├── lib                                          # CDK Stacks
│   ├── networking-stack.ts                      # VPC resources
│   ├── persistence-stack.ts                     # S3 and OpenSearch resources
│   └── api-stack.ts                             # Cognito, AppSync, and generative-ai constructs
│
└── generative-ai-cdk-constructs@0.0.58.jsii.tgz # Local copy of generative-ai CDK constructs
```

## Getting started

To deploy this document explorer, follow these steps to set up the required tools and configure your AWS environment:

### Pre-requisites

- An AWS account. We recommend to deploy this solution in a new account
- [AWS CLI](https://aws.amazon.com/cli/): configure your credentials

```
aws configure --profile [your-profile] 
AWS Access Key ID [None]: xxxxxx
AWS Secret Access Key [None]:yyyyyyyyyy
Default region name [None]: us-east-1 
Default output format [None]: json
```

- Node.js: v18.12.1
- [AWS CDK](https://github.com/aws/aws-cdk/releases/tag/v2.68.0): 2.68.0
- jq: jq-1.6

### Deploy the solution

This project is built using the [Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/). See [Getting Started With the AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) for additional details and prerequisites.

1. Clone this repository.
    ```shell
    git clone <this>
    ```

2. Enter the code sample backend directory.
    ```shell
    cd samples/document_explorer
    ```

3. Boostrap AWS CDK resources on the AWS account.
    ```shell
    cdk bootstrap aws://ACCOUNT_ID/REGION
    ```

4. The persistence layer requires the existence of the AWSServiceRoleForAmazonElasticsearchService Service-Linked Role (SLR). The following command checks if the SLR exists and creates one if needed:
    ```shell
    if ! aws iam get-role --role-name AWSServiceRoleForAmazonElasticsearchService > /dev/null 2>&1; then
    aws iam create-service-linked-role --aws-service-name es.amazonaws.com 
    fi
    ```

5. Enable Access to Bedrock Models
> You must explicitly enable access to models before they can be used with the Amazon Bedrock service. Please follow these steps in the [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) to enable access to the models (at minimum, ```Anthropic::Claude```):.

6. Deploy the sample in your account. 
    ```shell
    $ cdk deploy --all
    ```

The command above will deploy three stacks in your account. Some services require a certain amount of time to get provisioned, here are some values observed:
- Networking stack: ~181s (~3 minutes)
- Persistence stack: ~1137s (~19 minutes)
- Api stack: ~531 seconds (~9 minutes)

Between each stack, to protect you against unintended changes that affect your security posture, the AWS CDK Toolkit prompts you to approve security-related changes before deploying them. You will need to answer yes at each step to get all the stacks deployed.

7. Configure client_app
    ```shell
    cd client_app
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

8. Create an ```.env``` file with the following content. Replace the property values with the values retrieved from the stack outputs/console.

```
COGNITO_DOMAIN="<ApiStack.CognitoDomain>"
REGION="<ApiStack.Region>"
USER_POOL_ID="<ApiStack.UserPoolId>"
CLIENT_ID="<ApiStack.ClientId>"
CLIENT_SECRET="COGNITO_CLIENT_SECRET"
IDENTITY_POOL_ID="<ApiStack.IdentityPoolId>"
APP_URI="http://localhost:8501/"
AUTHENTICATED_ROLE_ARN="<ApiStack.AuthenticatedRoleArn>"
GRAPHQL_ENDPOINT = "<ApiStack.GraphQLEndpoint>"
S3_INPUT_BUCKET = "<PersistenceStack.InputsAssetsBucket>"
S3_PROCESSED_BUCKET = "<PersistenceStack.processedAssetsBucket>"

```

9. Run client_app
    ```shell
    streamlit run Home.py
    ```

### Test

- Create a user in the Cognito user pool. Go to the [Amazon Cognito page](https://console.aws.amazon.com/cognito/home) in the AWS console, then select the created user pool. Under users, select Create user and fill in the form

- Access the webapp (either locally or through the Amplify hosted domain) and sign in using the user credentials you just created 

- Upload sample PDF files to the input bucket. For example, download Amazon's Annual Letters to Shareholders from 1997-2022 from [ir.aboutamazon.com](https://ir.aboutamazon.com/annual-reports-proxies-and-shareholder-letters/default.aspx). Then:

### Steo 01. Test document ingestion
`Subscription` *(Optional - to track completion)*
```graphql
subscription UpdateIngestionJobStatus {
  updateIngestionJobStatus(ingestionjobid: "1997-2022") {
    files {
      name
      status
    }
  }
}
```

`Mutation`
```graphql
mutation IngestDocuments {
  ingestDocuments(
    ingestioninput: {
      files: [
        {status: "", name: "1997 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "1998 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "1999 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2000 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2001 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2002 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2003 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2004 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2005 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2006 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2007 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2008 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2009 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2010 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2011 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2012 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2013 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2014 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2015 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2016 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2017 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2018 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2019 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2020 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2021 Amazon Shareholder Letter.pdf"}, 
        {status: "", name: "2022 Amazon Shareholder Letter.pdf"}, 
      ], 
      ingestionjobid: "1997-2022"}
    ) {
    __typename
  }
}
```

### Steo 02. Run summarization
```Subscription```
```graphql
subscription UpdateSummaryJobStatus {
  updateSummaryJobStatus(summary_job_id: "2022_Amazon_Shareholder_Letter") {
    summary_job_id
    files {
      name
      status
      summary
    }
  }
}
```

```Mutation```
```graphql
mutation GenerateSummary {
    generateSummary(summaryInput: {
        summary_job_id: "2022_Amazon_Shareholder_Letter",
        files: [{name: "2022 Amazon Shareholder Letter.txt"}],
    }) {
    __typename
  }
}
```

### Steo 03. Ask Question
```Subscription```
```graphql
subscription UpdateQAJobStatus {
  updateQAJobStatus(jobid: "11a94ffc-423a-4157-a9c2-892446f9a1fe") {
    question
    answer
    jobstatus
  }
}
```

```Post Question```
```graphql
mutation PostQuestion {
    postQuestion(
        jobid: "11a94ffc-423a-4157-a9c2-892446f9a1fe"
        jobstatus: ""
        filename: "2022 Amazon Shareholder Letter.txt"
        question: "V2hvIGlzIEJlem9zPw=="
        max_docs: 1
        verbose: false
    ) {
    __typename
    }
}
```

## Clean up

Do not forget to delete the stack to avoid unexpected charges

First make sure to remove all data from the Amazon Simple Storage Service (Amazon S3) Buckets. Then:

```shell
    $ cdk destroy --all
```

Then in the AWS console delete the S3 buckets

# Content Security Legal Disclaimer
The sample code; software libraries; command line tools; proofs of concept; templates; or other related technology (including any of the foregoing that are provided by our personnel) is provided to you as AWS Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.

# Operational Metrics Collection
This solution collects anonymous operational metrics to help AWS improve the quality and features of the solution. Data collection is subject to the AWS Privacy Policy (https://aws.amazon.com/privacy/). To opt out of this feature, simply remove the tag(s) starting with “uksb-” or “SO” from the description(s) in any CloudFormation templates or CDK TemplateOptions.