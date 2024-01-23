import boto3
import json
import os

runtime= boto3.client('runtime.sagemaker')

ENDPOINT_NAME = os.environ['ENDPOINT_NAME']

def handler(event, context):
    
    dic = {
        "inputs": "<s>[INST] write the recipe for a mayonnaise [/INST]",
        "parameters" : {
          "temperature" : 0.6,
          "top_p" : 0.95,
          "repetition_penalty" : 1.2,
          "top_k" : 50,
          "max_new_tokens" : 4000,
          "stop" : ["</s>"]
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
   