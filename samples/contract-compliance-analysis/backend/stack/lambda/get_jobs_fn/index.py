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
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError
import awswrangler as wr

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())

dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])
step_functions = boto3.client('stepfunctions')


def get_state_machine_execution_details(job_id):
    logger.info(f'Getting state machine execution status')
    execution_arn = f"{os.environ['STATE_MACHINE_ARN'].replace('stateMachine', 'execution')}:{job_id}"
    return step_functions.describe_execution(executionArn=execution_arn)


class OutputEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        return json.JSONEncoder.default(self, obj)


def fill_job_details(job):
    if 'status' not in job or job['status'] != 'SUCCEEDED':
        try:
            execution_details = get_state_machine_execution_details(job['id'])

            logger.info(f"Execution Details: {execution_details}")

            job['status'] = execution_details['status']
            job['start_date'] = execution_details['startDate'].isoformat()
            if job['status'] != 'RUNNING':
                job['end_date'] = execution_details['stopDate'].isoformat()

            wr.dynamodb.put_items(
                table_name=jobs_table.name,
                items=[job]
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ExecutionDoesNotExist':
                print(f"Execution {job['id']} does not exist or has already completed.")
            else:
                raise

    job['filename'] = job['document_s3_path'].split('/')[-1]
    job.pop('document_s3_path')

    return job


def get_jobs():
    logger.info('Getting jobs from DynamoDB')
    jobs = []
    scan_kwargs = {
        'ProjectionExpression': 'id, document_s3_path, needs_review, #s, start_date, end_date, total_clause_types_by_risk, total_compliance_by_impact, total_compliance_by_severity, unknown_total',
        'ExpressionAttributeNames': {'#s': 'status'}
    }
    done = False
    start_key = None
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = jobs_table.scan(**scan_kwargs, )
        jobs.extend(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [
            pool.submit(
                fill_job_details, job
            ) for job in jobs
        ]
        jobs = [r.result() for r in as_completed(futures)]
    return jobs


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
    except (KeyError, ValueError) as exception:
        logger.debug(exception, exc_info=True)
        response['statusCode'] = 400
        return response
    except ClientError as exception:
        logger.debug(exception, exc_info=True)
        response['statusCode'] = 500
        return response

    response['statusCode'] = 200
    response['body'] = json.dumps(get_jobs(), cls=OutputEncoder)
    return response
