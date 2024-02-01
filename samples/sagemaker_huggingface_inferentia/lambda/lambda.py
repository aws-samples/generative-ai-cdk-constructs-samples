import boto3
import json
import os

runtime= boto3.client('runtime.sagemaker')
    
ENDPOINT_NAME = os.environ['ENDPOINT_NAME']

def handler(event, context):
    
    dic = {
        "inputs": "Can you tell me an interesting fact about AWS?",
        "parameters": {
            "do_sample": True,
            "top_p": 0.6,
            "temperature": 0.9,
            "top_k": 50,
            "max_new_tokens": 256,
            "repetition_penalty": 1.03,
            "return_full_text": False,
            "stop": ["</s>"]
        }
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
   