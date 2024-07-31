import boto3
import botocore
from PIL import Image
from io import BytesIO
import base64
import json
from diffusers.utils import export_to_video
from time import sleep
import os

s3_client = boto3.client("s3")
s3_resource = boto3.resource("s3")
sagemaker_client = boto3.client("sagemaker-runtime")

# Configuration
S3_BUCKET = "XXXXX"
S3_BUCKET_KEY = "svd-hf-1"
S3_BUCKET_OUTPUT_KEY = "output" # this is the output folder in the S3 bucket (configured in the asyncInference construct settings)
ENDPOINT_NAME = "svdendpoint" # endpoint name configured in the construct
FRAME_PER_SECOND = 7
INPUT_IMAGE_URL = 'https://raw.githubusercontent.com/Stability-AI/generative-models/main/assets/test_image.png'

# Local File Paths
REQUEST_PAYLOAD = "input.json"
RESPONSE_PAYLOAD = "output.json"

def decode_base64_image(image_string):
    base64_image = base64.b64decode(image_string)
    buffer = BytesIO(base64_image)
    return Image.open(buffer)

def upload_file(file_path):
    s3_client.upload_file(
        Filename=file_path,
        Bucket=S3_BUCKET,
        Key="input.json",
        ExtraArgs={"ContentType": "application/json"},
    )

def invoke_async_endpoint():

    data = {
        "inputs": INPUT_IMAGE_URL,
    }

    with open(REQUEST_PAYLOAD, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    upload_file(REQUEST_PAYLOAD)

    response = sagemaker_client.invoke_endpoint_async(
        EndpointName=ENDPOINT_NAME,
        InputLocation=f"s3://{S3_BUCKET}/input.json",
        InvocationTimeoutSeconds=3600,
    )

    return response.get("OutputLocation")

try:
    invoke_response = invoke_async_endpoint()

except Exception as e:
    print(e)
    exit(1)

output_object_name = invoke_response.split("/")[-1]
output_key = os.path.join(S3_BUCKET_KEY, S3_BUCKET_OUTPUT_KEY, output_object_name)
print(f"Output Key: {output_key}")

head_response = None
try:
    head_response = s3_resource.Object(S3_BUCKET, output_key).load()
except botocore.exceptions.ClientError as e:
    retry_count = 10
    if e.response['Error']['Code'] == "404":
        while retry_count > 0 or head_response is None:
            print(f"Waiting for output object: {output_key}")
            print(f"Retries left: {retry_count}")

            retry_count -= 1
            sleep(30)
            try:
                head_response = s3_resource.Object(
                    S3_BUCKET, output_key).load()
                break
            except:
                continue
    else:
        # Something else has gone wrong.
        raise

# download output object from s3
s3_client.download_file(
    Bucket=S3_BUCKET, Key=output_key, Filename=RESPONSE_PAYLOAD
)

with open(RESPONSE_PAYLOAD) as f:
    frames = json.load(f)

decoded_images = [decode_base64_image(image) for image in frames["frames"]]

export_to_video(decoded_images, f"{output_object_name}.mp4", fps=FRAME_PER_SECOND)