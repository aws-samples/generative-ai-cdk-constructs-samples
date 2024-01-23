import boto3
import json
import os

runtime= boto3.client('runtime.sagemaker')

ENDPOINT_NAME = os.environ['ENDPOINT_NAME']

def handler(event, context):
    
    dic = {"inputs": "<s>[INST] Write the recipe for a lemon cake [/INST]"}
    
    response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                       ContentType='application/json',
                                       Body=json.dumps(dic))
    
    result = json.loads(response['Body'].read().decode())
    print(result)
    
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
   