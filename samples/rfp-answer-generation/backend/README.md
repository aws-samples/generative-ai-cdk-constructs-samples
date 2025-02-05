# RFP Answering with GenAI - Backend

## Prequisites

The following tooling needs to be installed:

In order to deploy this project, you need to have installed:

- [Python](https://www.python.org/downloads/) 3.12 or higher
- [Docker](https://docs.docker.com/engine/install/)
- Git (if using code repository)
- [AWS CDK Toolkit](https://docs.aws.amazon.com/cdk/v2/guide/cli.html)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)

With all installed, run this command:

```shell
$ python3 -V && cdk --version && docker info -f "{{.OperatingSystem}}"
```

An output similar to the following indicates that all is ok to proceed:

```shell
Python 3.13.1
2.175.1 (build afe6e87)
Docker Desktop
```

If any of these commands fails, you can revisit the documentation and check for possible steps you have forgotten to complete.
Ensure that your CDK version is using CDK V2, by checking if the second line of the output follows the pattern 2._._.

With these installed, it is time to configure your environment to connect to your AWS Account. We **highly recommend
using an isolated AWS Account** to test this project. If you do not have such account, reach out to your Account Manager,
and ask him for guidance on how to provision the account on your company.

To set up your local environment to use such an AWS account you can follow the steps described at
https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html}

### Create Python virtual environment

To manually create a virtualenv on MacOS and Linux:

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
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```shell
$ pip install -r requirements.txt
```

### Bootstrap CDK

Run the following

```
$ cdk bootstrap
```

## Deployment

The backend stack is divided into `Ingestion` and `Inference` substacks. You can deploy each substack on its own provided the business application requirements are met.

To deploy the `Ingestion` stack directly into your AWS account:

1. Run AWS CDK Toolkit to deploy the `RFPAnswers-IngestionStack` with the runtime resources.
   ```shell
   $ cdk deploy RFPAnswers-IngestionStack --require-approval=never --verbose
   ```
2. Any modifications made to the code can be applied to the deployed stack by running the same command again.
   ```shell
   $ cdk deploy RFPAnswers-IngestionStack --require-approval=never --verbose
   ```

To deploy the `Inference` stack directly into your AWS account:

1. Run AWS CDK Toolkit to deploy the `RFPAnswers-InferenceStack` with the runtime resources.
   ```shell
   $ cdk deploy RFPAnswers-InferenceStack --require-approval=never --verbose
   ```
2. Any modifications made to the code can be applied to the deployed stack by running the same command again.
   ```shell
   $ cdk deploy RFPAnswers-InferenceStack --require-approval=never --verbose
   ```

## Clean up

Do not forget to delete the stack to avoid unexpected charges.

First make sure to remove all data from the Amazon Simple Storage Service (Amazon S3) Buckets.

```shell
    $ cdk destroy RFPAnswers-IngestionStack
```

```shell
    $ cdk destroy RFPAnswers-InferenceStack
```

Delete all the associated logs created by the different services in Amazon CloudWatch logs. 