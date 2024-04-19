
# Python Samples!

This project showcases the utilization of the 'generative-ai-cdk-constructs' package from the Python Package Index (PyPI). It encompasses exemplary implementations of critical components commonly required in generative AI applications. The 'app.py' file orchestrates the synthesis of multiple constructs sourced from the 'generative-ai-cdk-constructs' library. Depending on your specific requirements, you may opt to selectively deploy only the constructs pertinent to your use case, rather than deploying the entirety of the available constructs.

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


The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

Deploy the sample in your account.
 
```
$ cdk deploy
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
