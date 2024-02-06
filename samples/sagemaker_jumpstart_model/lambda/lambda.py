#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
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
   