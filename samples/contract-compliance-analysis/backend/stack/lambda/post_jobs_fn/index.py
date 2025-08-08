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
import datetime
import json
import logging
import os
from decimal import Decimal
from json import JSONDecodeError

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())

dynamodb = boto3.resource('dynamodb')
step_functions = boto3.client('stepfunctions')
jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])


class OutputEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def validate_body(body_obj):
    if not body_obj or not isinstance(body_obj, dict):
        raise ValueError
    if 'filename' not in body_obj or len(body_obj['filename']) > 200:
        raise ValueError


def start_state_machine_execution(document_s3_path):
    state_machine_arn = os.environ['STATE_MACHINE_ARN']
    logger.info(f'Starting state machine {state_machine_arn}')
    result = step_functions.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps({
            'document_s3_path': document_s3_path
        })
    )
    if 'ResponseMetadata' not in result or result['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise AssertionError
    return result['executionArn']


def get_state_machine_execution_details(execution_arn):
    logger.info(f'Getting state machine execution status')
    return step_functions.describe_execution(executionArn=execution_arn)


def record_job(job_id, document_s3_path):
    logger.info('Recording job')
    jobs_table.put_item(Item={
        'id': job_id,
        'document_s3_path': document_s3_path
    })


def handler(event, _context):
    response = {
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*'
        }
    }
    try:
        logger.debug(event)
        body_obj = json.loads(event['body'])
        validate_body(body_obj)
        filename = body_obj['filename']
        document_s3_path = f"s3://{os.environ['DOCUMENTS_BUCKET']}/{os.environ['DOCUMENTS_FOLDER']}/{filename}"
        execution_arn = start_state_machine_execution(document_s3_path)
        job_id = execution_arn.split(':')[-1]
        record_job(job_id, filename)
        execution_details = get_state_machine_execution_details(execution_arn)
        job = {
            'id': job_id,
            'filename': filename,
            'status': execution_details['status'],
            'start_date': execution_details['startDate']
        }
        if job['status'] != 'RUNNING':
            job['end_date'] = execution_details['stopDate']
        response['body'] = json.dumps(job, cls=OutputEncoder)

    except (JSONDecodeError, KeyError, ValueError, TypeError) as exception:
        logger.debug(exception, exc_info=True)
        status_code = 400
    except (AssertionError, ClientError) as exception:
        logger.debug(exception, exc_info=True)
        status_code = 500
    else:
        status_code = 200

    response['statusCode'] = status_code
    return response
