import boto3
import json
import os

runtime= boto3.client('runtime.sagemaker')
    
ENDPOINT_NAME = os.environ['SG_ENDPOINT_NAME']

def handler(event, context):
    
    dic = {
        "inputs": "the mesmerizing performances of the leads keep the film grounded and keep the audience riveted .",
    }
    
    response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                       ContentType='application/json',
                                       Body=json.dumps(dic))
    
    result = json.loads(response['Body'].read().decode())
    print(result)
    
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
   