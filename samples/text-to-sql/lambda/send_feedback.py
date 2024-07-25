import json
import boto3
import os

# Create an SQS client
sqs = boto3.client('sqs')
account_id = os.environ["ACCOUNT_ID"]

# Set the queue URL
queue_url = f'https://sqs.us-east-1.amazonaws.com/{account_id}/feedbackqueuedevtexttosqlstacktexttosql1eb82bd03'

sfn_client = boto3.client('stepfunctions')

def lambda_handler(event, context):
    # Receive messages from the SQS queue
    print(f'input message {event}')
    # poll messages from the queue
    # response = sqs.receive_message(
    #     QueueUrl=queue_url,
    #     MaxNumberOfMessages=1,  # Receive at most 1 message at a time
    #     WaitTimeSeconds=10  # Wait for up to 10 seconds for a message to arrive
    # )
    #print(f'response {response}')
    input_message = event['message']

    if input_message :
        # Get the first message from the response
        
        # Extract the task token and status from the message body
        #event_data = json.loads(input_message)
        task_token = event['TaskToken']
        user_question = event['user_question']['value']
        reformulated_user_question = event['reformualted_question']['value']
        status = 'approve'
        
        # Check if the status is 'approve' or 'reject'
        if status.lower() == 'approve':
            # Send a task success response to Step Functions
            response = sfn_client.send_task_success(
                taskToken=task_token,
                output=json.dumps({'approved': True,
                    'reformulated_user_question':reformulated_user_question,
                    'user_question':user_question,
                    'feedback_response':'No issue',
                })
            )
        elif status.lower() == 'reject':
            # Send a task failure response to Step Functions
            response = sfn_client.send_task_failure(
                taskToken=task_token,
                error='Rejected',
                cause='The task was rejected.',
                output=json.dumps({'approved': True,
                    'reformulated_user_question':reformulated_user_question,
                    'user_question':user_question,
                    'feedback_response':'No issue',
                })
            )
        else:
            # Invalid status
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid status. Expected "approve" or "reject".')
            }

        # Delete the processed message from the queue
        # sqs.delete_message(
        #     QueueUrl=queue_url,
        #     ReceiptHandle=message['ReceiptHandle']
        # )

        # Return a success response
        return {
            'statusCode': 200,
            'body': json.dumps(f'Status {status} sent to Step Functions.')
        }
    else:
        # No messages in the queue
        return {
            'statusCode': 200,
            'body': json.dumps('No messages in the queue.')
        }
