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
import json
import boto3
import os
from custom_errors import TaskTokenMissing,UserQuestionMissing

# Create an SQS client
sqs = boto3.client('sqs')
sfn_client = boto3.client('stepfunctions')



def handler(input,lambda_context):
    print(f'Received user feedback :: {input}')
    body_data = json.loads(input.get('body', ''))    
    print(f'body_data :: {body_data}')
    user_question = body_data.get('user_question')
    print(f'user_question :: {user_question}')
    unique_id = body_data.get('unique_id')
    print(f'unique_id :: {unique_id}')
    if user_question is None or unique_id is None:
        raise UserQuestionMissing("user question or question id is missing")
    
    task_token = body_data['task_token']
    print(f'task_token :: {task_token}')
    if task_token is None:
        raise TaskTokenMissing("TaskToken is missing in the input")
    
    reformualted_question = body_data.get('reformualted_question', None) 
    generated_query = body_data.get('generated_query', None)
    execute_sql_strategy = body_data.get('execute_sql_strategy', None)
    execution_start_time = body_data.get('execution_start_time', None)
    
    print(f'execute_sql_strategy:: {execute_sql_strategy}')
    print(f'generated_query :: {generated_query}')
    print(f'sending feedback...')
    # Send a task success response to Step Functions
    response = sfn_client.send_task_success(
                taskToken=task_token,
                output=json.dumps({'approved': True,
                    'reformulated_user_question':reformualted_question,
                    'user_question':user_question,
                    'feedback_response':'',
                    'question_unique_id':unique_id,
                    'generated_query':generated_query,
                    'execute_sql_strategy':execute_sql_strategy,
                    'execution_start_time':execution_start_time
                })
            )
    
    # Return a success response
    return {
            'statusCode': 200,
            'body': json.dumps(f'Status {response} sent to Step Functions.')
        }
    