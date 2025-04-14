# Bedrock BDA Multimodal Media Solution - Backend

## Table of contents

- [Local deployment](#local-deployment)
- [User creation](#user-creation)

## Local deployment

In order to deploy this project, you need to have installed:

- [Python](https://www.python.org/downloads/) 3.11 or higher
- [Docker](https://docs.docker.com/engine/install/)
- Git (if using code repository)
- [AWS CDK Toolkit](https://docs.aws.amazon.com/cdk/v2/guide/cli.html)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)

With all installed, run this command:

```shell
$ python3 -V && cdk --version && docker info -f "{{.OperatingSystem}}"
Python 3.12.2
2.176.0 (build 899965d)
Docker Desktop
```

An output similar to the above indicates that all is ok to proceed.

If any of these commands fails, you can revisit the documentation and check for possible steps you have forgotten to complete.
Ensure that your CDK version is using CDK V2, by checking if the second line of the output follows the pattern 2.*.*.

Having those installed, it is time to configure your environment to connect to your AWS Account.
To set up your local environment to use such an AWS account you can follow the steps described at [https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)

### Get source code

If not done already, clone this repository

```shell
git clone https://github.com/aws-samples/generative-ai-cdk-constructs-samples.git
```

Enter the backend directory

```shell
cd samples/bedrock-bda-media-solution/backend
```

### Create Python virtual environment

To manually create a virtualenv on MacOS and Linux:

```shell
python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```shell
source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```shell
.venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```shell
pip install -r requirements.txt
```

### Bootstrap CDK

Run the following

```shell
cdk bootstrap
```

### Deployment

1. Run AWS CDK Toolkit to deploy the Backend stack with the runtime resources.

    ```shell
    cdk deploy --require-approval=never
    ```

2. Any modifications made to the code can be applied to the deployed stack by running the same command again.

    ```shell
    cdk deploy --require-approval=never
    ```

## Samples files

The [samples](./samples/) folder contains samples files you can use to test the application.

## User creation

First, locate the Cognito User Pool ID, through the AWS CLI:

```shell
$ aws cloudformation describe-stacks --stack-name BDAMediaSolutionBackendStack --query "Stacks[0].Outputs[?contains(OutputKey, 'UserPoolId')].OutputValue"

[
    "OutputValue": "<region>_a1aaaA1Aa"
]
```

You can then go the Amazon Cognito page at the AWS Console, search for the User Pool and add users.