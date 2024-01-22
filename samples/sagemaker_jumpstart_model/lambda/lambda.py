import boto3
import json
import os

ENDPOINT_NAME = os.environ['ENDPOINT_NAME']
runtime= boto3.client('runtime.sagemaker')

def handler(event, context):
    
    dic = {
     "inputs": [
      [
       {"role": "system", "content": "You are chat bot who writes songs"},
       {"role": "user", "content": "Write a rap song about Amazon Web Services"}
      ]
     ],
     "parameters": {"max_new_tokens":256, "top_p":0.9, "temperature":0.6}
    }
    
    response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                       ContentType='application/json',
                                       Body=json.dumps(dic),
                                       CustomAttributes="accept_eula=false")
    
    result = json.loads(response['Body'].read().decode())
    print(result)
    
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
   