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
    