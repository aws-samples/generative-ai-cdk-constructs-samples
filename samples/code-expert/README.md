# Code Expert

This prototype aims to address the scalability limitations of manual code reviews by leveraging artificial intelligence
to perform expert code reviews automatically.
The key goals of this prototype are:

1. To automatically evaluate code repositories against a comprehensive set of software engineering guidelines;
2. To generate detailed findings reports that development teams can use to improve their code quality;
3. To provide a scalable solution that can handle multiple projects and a large number of guidelines simultaneously.

It leverages [AWS Generative AI CDK Constructs](https://github.com/awslabs/generative-ai-cdk-constructs).

The key constructs used in this sample app are:

- [Bedrock Batch Step Functions](...): Manage Bedrock model invocation jobs(batch inference) in AWS Step Functions state
  machines

By wrapping the complexity of orchestrating services like AWS Lambda, Amazon AppSync, and Amazon Bedrock, the Generative
AI Constructs library enables you to quickly build custom generative AI applications following AWS best practices.

## Example

Consider a typical Java class from a financial application's service layer.
When submitted to the prototype for review, the system first determines which guidelines are applicable based on the
file's characteristics and project context.
It then prepares the code and relevant guidelines for AI evaluation.
The AI model, guided by carefully crafted prompts, analyzes the code against these guidelines.

Example findings for the code might look like this:

```json
[
  {
    "rule": "JAVA001",
    "file": "src/main/java/com/example/services/TransactionService.java",
    "snippet": "public void processTransaction(String accountId, BigDecimal amount) {",
    "description": "Method 'processTransaction' lacks input validation for 'accountId' and 'amount' parameters.",
    "suggestion": "Add null checks for 'accountId' and ensure 'amount' is positive at the beginning of the method. Consider using Objects.requireNonNull() for null checks and throwing an IllegalArgumentException for invalid amounts."
  },
  {
    "rule": "JAVA023",
    "file": "src/main/java/com/example/services/TransactionService.java",
    "snippet": "catch (Exception e) {\n    logger.error(\"Error processing transaction\", e);\n}",
    "description": "Overly broad exception handling. Catching Exception may mask underlying issues and make debugging difficult.",
    "suggestion": "Catch specific exceptions that are expected and can be handled meaningfully. For unexpected exceptions, consider wrapping and rethrowing as a specific application exception to maintain the exception hierarchy."
  }
]
```

## Technical Approach

This prototype describes an AWS-based automated code review system that leverages Amazon Bedrock for AI analysis. At its
core, the system evaluates code using two distinct types of rules: simple rules that analyze files in isolation, and
context rules that consider broader repository content when performing evaluations. Both approaches share a common
workflow that includes analyzing repository structure, mapping rules to files, generating AI prompts, and parsing
responses into actionable findings. While the system supports both synchronous and batch processing methods, batch
processing is preferred for its superior cost-efficiency and throughput capabilities.

[View Detailed Technical Approach](documentation/technical-approach.md#technical-details)

## Cost

You are responsible for the cost of the AWS services used while running this prototype. As of this revision, the cost
for running this prototype with the default settings in the US East (N. Virginia) Region is approximately $2,068.96 per
month with 100 rules and 100 repositories evaluated per month using Amazon Bedrock Batch Inference.

The costs shown represent pricing without consideration of AWS free tier benefits.

We recommend creating a budget through [AWS Cost Explorer](http://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
to help manage costs. Prices are subject to change. For full details, refer to the pricing webpage for each AWS service
used in this solution.

The following table provides a sample cost breakdown for deploying this solution with the default parameters in the **US
East (N. Virginia)** Region for **one month**.

### Cost estimate with batch inference

| **AWS Service**    | **Usage**                                        | **Cost [USD]** |
|:-------------------|:-------------------------------------------------|----------------|
| Amazon Bedrock     | Rule Evaluation with Anthropic Claude 3.5 Sonnet | $2,062.50      |
| AWS Lambda         | Compute                                          | $0.80          |
| AWS Step Functions | Orchestration                                    | $0.40          |
| Amazon S3          | Input, Output, and Temporary Storage             | $0.26          |
| AWS CloudWatch     | Logs                                             | $5.00          |
| **Total**          |                                                  | **$2,068.96**  |

For comparison, with on-demand inference, the Amazon Bedrock usage would increase to $4,125.00.

## Deployment and Development

### Repository Structure

This prototype is a monorepo managed by [AWS PDK](https://aws.github.io/aws-pdk/) with packages for infrastructure,
business logic, the demo, and
notebooks for experimentation.

| Folder                                                                                                     | Package                                                                                            |
|------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| packages/infra/                                                                                            | Infrastructure as Code in [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) |
| [packages/code-expert/code-expert/](packages/code-expert/code-expert/README.md#code-expert-implementation) | Business logic in Python used in AWS Lambda                                                        |
| [demo/](demo/README.md#code-expert-demo-app)                                                               | [Streamlit](https://streamlit.io) demo (Optional)                                                  |

### Prerequisites

* Configure the AWS Credentials in your environment. Refer
  to [Authentication and access](https://docs.aws.amazon.com/sdkref/latest/guide/access.html).
* Download and install AWS CLI. Refer
  to [Installing the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
* Install and configure AWS CDK. Refer to Installing
  the [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html).
* Download and install Docker. Refer to [Docker](https://www.docker.com/products/docker-desktop/).
* NodeJS >= 18.0.0 and < 22
* Python >= 3.12 preferably with [pyenv](https://github.com/pyenv/pyenv)
* Poetry >= 1.5.1 and < 2.0.0
* Pnpm >= 8.6.3 and < 9

```shell
pip install poetry==1.8.5
npm install -g pnpm@^8.15.9 aws-cdk
```

### First build

```shell
pnpm i
pnpm pdk install:ci
pnpm pdk build
```

### Deploy

```shell
pushd packages/infra
pnpm cdk bootstrap
pnpm cdk deploy
```

Once completed, you should see the CloudFormation outputs.

Example

```
CodeExpert: deploying... [1/1]

CodeExpert

Deployment time: 64.35s

Outputs:
CodeExpert.BedrockBatchBucketName = codeexpert-bedrockbatchbucket1234
CodeExpert.BedrockBatchRole4AD7B7FB = arn:aws:iam::123456789012:role/CodeExpert-BedrockBatchRole1234
CodeExpert.ConfigBucketName = codeexpert-configbucket1234
CodeExpert.InputBucketName = codeexpert-inputbucket1234
CodeExpert.OutputBucketName = codeexpert-outputbucket1234
CodeExpert.StateMachineArn = arn:aws:states:us-east-1:123456789012:stateMachine:CodeExpertWorkflowStateMachine1234
Stack ARN:
arn:aws:cloudformation:us-east-1:123456789012:stack/CodeExpert/1234

Total time: 122.13s
```

### Activate Models in Amazon Bedrock

This prototype can use the Amazon Nova and Anthropic Claude models on Amazon Bedrock. You will need
to [enable them](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) for your account in the regions
you want to use.

If you choose to
use [Cross-Region Inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html) for
increased throughput, you will need to activate the models in each region that will be used.

### Configure Rules

Prepare your rules file according to the [format](documentation/rules.md#code-expert-rules-configuration-format).

Upload your **rules.json** file to the configuration bucket in **ConfigBucketName** from the deployment output.

```shell
aws s3 cp rules.json s3://<ConfigBucketName>/rules.json
```

### Demo

You are now ready to perform code reviews!

To run the [demo](demo/README.md#code-expert-demo-app), you will need the **InputBucketName** and **StateMachineArn**
outputs from the CDK deployment.

### Development

#### Modify project

To change the project settings, edit `.projenrc.ts`

and run

```shell
pnpm pdk
```

#### Update Code

```shell
pnpm pdk build
pushd packages/infra
pnpm cdk deploy smart-product-onboarding
popd
```

### Troubleshooting

#### Errors about accessing `public.ecr.aws`

You may have logged in to `public.ecr.aws` with Docker and the credentials have expired.

```shell
docker logout public.ecr.aws
```

## Cleanup

In the event that you decide to stop using the prototype, we recommend that you follow a tear-down procedure. Most of
the services used have no cost when there is no active use with the notable exception of storage in S3, DynamoDB, and
CloudWatch Logs. AWS CloudFormation via CDK will tear down all resources except for Amazon S3 buckets and AWS CloudWatch
Logs log groups with data.

1. On the AWS CloudFormation console or using AWS CDK in the terminal, destroy the stacks that were deployed. Some of
   the S3 buckets will remain as they will not be empty.
2. Delete any CloudWatch Logs log groups that you do not wish to keep.
3. In any S3 buckets that remain that you do not wish to keep, empty the buckets by disabling logging and configuring a
   lifecycle policy that expires objects after one day. Wait a day.
4. After a day, go back and delete the buckets.

## Improvements

As part of the prototype process, we have some [improvement ideas](documentation/improvements.md#improvements) for your
path to production.

## Security Guideline

Please see the [security guidelines](documentation/security.md#security).

## Content Security Legal Disclaimer

Sample code, software libraries, command line tools, proofs of concept, templates, or other related technology are
provided as AWS Content or Third-Party Content under the AWS Customer Agreement, or the relevant written agreement
between you and AWS (whichever applies). You should not use this AWS Content or Third-Party Content in your production
accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS
Content or Third-Party Content, such as sample code, as appropriate for production grade use based on your specific
quality control practices and standards. Deploying AWS Content or Third-Party Content may incur AWS charges for creating
or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.

# Operational Metrics Collection

This solution collects anonymous operational metrics to help AWS improve the quality and features of the solution. Data
collection is subject to the AWS Privacy Policy (https://aws.amazon.com/privacy/). To opt out of this feature, simply
remove the tag(s) starting with “uksb-” or “SO” from the description(s) in any CloudFormation templates or CDK
TemplateOptions.