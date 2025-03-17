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

import json
import os
import boto3
import botocore
from typing import Any, Dict
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

LOGGER = Logger(serialize_stacktrace=True, name="%(name)s")

lambda_client = boto3.client('lambda')

def get_stream_arn_secrets():
    """Retrieve secrets from AWS Secrets Manager"""
    secret_name = os.environ['STREAM_ARN_SECRET_NAME']
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager'
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        LOGGER.error(f"Error retrieving secrets: {str(e)}")
        raise e
    else:
        if 'SecretString' in get_secret_value_response:
            secret = json.loads(get_secret_value_response['SecretString'])
            return secret
        raise ValueError("No SecretString found in secret")

try:
    stream_arn_secrets = get_stream_arn_secrets()
    LOGGER.info("Stream function ARN loaded from secrets manager")
    STREAM_HANDLER_ARN = stream_arn_secrets['STREAM_HANDLER_ARN']
except Exception as e:
    LOGGER.error(f"Error initializing services: {str(e)}")
    raise


def _lambda_handler(event):
    try:
        LOGGER.info(f"Received event: {json.dumps(event)}")
        question = event['question']
        session_id = event['sessionId']

        # Asynchronously invoke the streaming handler
        lambda_client.invoke(
            FunctionName=STREAM_HANDLER_ARN,
            InvocationType='Event',  # This makes it asynchronous
            Payload=json.dumps({
                'sessionId': session_id,
                'question': question
            })
        )

        # Return immediately with the session ID
        return {
            'sessionId': session_id,
            'status': 'STARTED'
        }

    except Exception as e:
        LOGGER.error(f"Error: {str(e)}")
        return {
            'sessionId': event.get('sessionId', "Unknown sessionId"),
            'status': 'ERROR',
            'error': str(e)
        }
    
@LOGGER.inject_lambda_context(clear_state=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    LOGGER.info(f"Received event: {event}")
    try:
        response = _lambda_handler(event=event)
    except botocore.exceptions.ClientError as error:
        op_name = error.operation_name
        err_name = error.response["Error"]["Code"]
        err_message = error.response["Error"]["Message"]
        message = f"Call to the {op_name} operation returned a {err_name} error: {err_message}"
        LOGGER.exception(f"AWS service-side error: {message}")
        error_message = f"Internal server error (AWS service-side error): {message}"
        raise Exception(error_message)
    except Exception as error:
        LOGGER.exception("Unhandled error")
        error_message = f"Unhandled internal server error ({type(error).__name__}): {error}"
        raise Exception(error_message)

    return response
