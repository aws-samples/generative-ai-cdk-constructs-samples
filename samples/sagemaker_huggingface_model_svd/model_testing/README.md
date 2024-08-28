# Model testing

## 1. Introduction

This testing tool provides a simple way to test the Amazon SageMaker Async endpoint deployed in this sample to generate a video from a source image.

For this workflow, you can specify in the provided Python script the URL of the image you want to use as source. The tool will then upload the image to your Amazon Simple Storage Service (S3)bucket, and submit a request to the endpoint for inference. The output of inference will be stored in the same bucket, at the path configured in the AWS CDK construct. The tool will then poll the bucket until an output is available, download the generated video and store in locally.

> Note: You can modify this sample to take advantage of the Amazon Simple Notification Service (SNS) topics provisioned by the CDK construct to be notified when the inference output is available.

## 2. Getting started

### Prerequisites

- An AWS account containing the deployed model as described in the previous steps of the sample.
- [AWS CLI](https://aws.amazon.com/cli/): configure your credentials

```
aws configure --profile [your-profile] 
AWS Access Key ID [None]: xxxxxx
AWS Secret Access Key [None]:yyyyyyyyyy
Default region name [None]: us-east-1 
Default output format [None]: json
```
- Python (tested with Python 3.12.2)

### Deployment

1. Clone this repository.
    ```shell
    git clone https://github.com/aws-samples/generative-ai-cdk-constructs-samples.git
    ```

2. Enter the code testing tool directory.
    ```shell
    cd samples/sagemaker_huggingface_model_svd/model_testing
    ```

4. Create a virtual environment and install the dependencies
   ```shell
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. Update the configuration in the [model_testing.py](./model_testing.py) file (L15-21) with your own values:
```
S3_BUCKET : replace this with the name of your bucket containing your model artifacts
ENDPOINT_NAME : replace this with the name of your async sagemaker endpoint
INPUT_IMAGE_URL = replace this with the URL of an image you want to use as input for inference. You can keep the default value.
```

6. Run the tool
    ```shell
    python model_testing.py
    ```

The video generated is stored locally, in the model_testing folder (*.mp4).

## Example

Using the [following image](https://raw.githubusercontent.com/Stability-AI/generative-models/main/assets/test_image.png):

![Example video](https://raw.githubusercontent.com/Stability-AI/generative-models/main/assets/test_image.png)

It generates the following video:

[![Inference output](https://raw.githubusercontent.com/Stability-AI/generative-models/main/assets/test_image.png)](./output_video_sample.mp4)