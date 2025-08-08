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

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

CLAUSE_FIELDS = {'clause_number', 'text', 'types'}
CLAUSE_TYPE_FIELDS = {'type_id', 'level', 'type_name', 'analysis', 'classification_analysis', 'compliant'}

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())

dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])
clauses_table = dynamodb.Table(os.environ['CLAUSES_TABLE'])
step_functions = boto3.client('stepfunctions')


def get_state_machine_execution_details(job_id):
    logger.info(f'Getting state machine execution status')
    execution_arn = f"{os.environ['STATE_MACHINE_ARN'].replace('stateMachine', 'execution')}:{job_id}"
    return step_functions.describe_execution(executionArn=execution_arn)


class OutputEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def remove_extra_fields(clauses):
    def pop_extra(item, fields_to_keep):
        fields_to_remove = set(item.keys()) - fields_to_keep
        for field in fields_to_remove:
            item.pop(field)

    for clause in clauses:
        pop_extra(clause, CLAUSE_FIELDS)
        if 'types' in clause:
            for clause_type in clause['types']:
                pop_extra(clause_type, CLAUSE_TYPE_FIELDS)


def get_clauses(job_id):
    logger.info('Getting clauses from DynamoDB')
    clauses = []
    query_kwargs = {
        'KeyConditionExpression': Key('job_id').eq(job_id)
    }
    done = False
    start_key = None
    while not done:
        if start_key:
            query_kwargs['ExclusiveStartKey'] = start_key
        response = clauses_table.query(**query_kwargs)
        clauses.extend(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None
    remove_extra_fields(clauses)
    return clauses


def get_job(job_id):
    logger.info('Getting job from DynamoDB')
    response = jobs_table.get_item(Key={'id': job_id})
    if 'Item' in response:
        job = response['Item']
        execution_details = get_state_machine_execution_details(job['id'])
        job['status'] = execution_details['status']
        job['start_date'] = execution_details['startDate']
        job['filename'] = job['document_s3_path'].split('/')[-1]
        job.pop('document_s3_path')
        if job['status'] != 'RUNNING':
            job['end_date'] = execution_details['stopDate']
        if job['status'] == 'SUCCEEDED':
            job['clauses'] = get_clauses(job_id)
        return job


def validate_str_input(str_input):
    if not str_input or len(str_input) > 100:
        raise ValueError


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
        job_id = event['pathParameters']['id']
        validate_str_input(job_id)
    except (KeyError, ValueError) as exception:
        logger.debug(exception, exc_info=True)
        response['statusCode'] = 400
        return response
    except ClientError as exception:
        logger.debug(exception, exc_info=True)
        response['statusCode'] = 500
        return response

    job = get_job(job_id)
    if job:
        response['statusCode'] = 200
        response['body'] = json.dumps(job, cls=OutputEncoder)
    else:
        response['statusCode'] = 404
        response['body'] = json.dumps({})
    return response
