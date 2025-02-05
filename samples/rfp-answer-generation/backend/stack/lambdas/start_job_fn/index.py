#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import boto3
import datetime
import json
import logging
import os
import re

from decimal import Decimal
from urllib.parse import unquote_plus

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "WARNING").upper())

dynamodb = boto3.resource("dynamodb")
jobs_table = dynamodb.Table(os.environ["JOBS_TABLE"])

state_machine_arn = os.environ["STATE_MACHINE_ARN"]
step_functions = boto3.client("stepfunctions")


class OutputEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def start_state_machine_execution(document_s3_path, start_date):
    logger.info(f"Starting state machine {state_machine_arn}")
    result = step_functions.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps(
            {
                "document_s3_path": document_s3_path,
                "start_date": start_date,
            }
        ),
    )
    if (
        "ResponseMetadata" not in result
        or result["ResponseMetadata"]["HTTPStatusCode"] != 200
    ):
        raise AssertionError

    execution_arn = result["executionArn"]
    job_id = execution_arn.split(":")[-1]

    return execution_arn, job_id


def get_execution_status(execution_arn):
    logger.info(f"Getting status for execution {execution_arn}")
    result = step_functions.describe_execution(
        executionArn=execution_arn,
    )

    if (
        "ResponseMetadata" not in result
        or result["ResponseMetadata"]["HTTPStatusCode"] != 200
    ):
        raise AssertionError

    status = result["status"]

    return status


def handler(event, _context):
    logger.debug(event)

    if "Records" in event:
        for record in event["Records"]:
            bucket = record["s3"]["bucket"]["name"]
            object_key = unquote_plus(record["s3"]["object"]["key"])

            filename = object_key.split("/")[-1]
            filename = re.sub(r"\.csv$", "", filename)
            filename = re.sub(r"\.xlsx$", "", filename)

            start_date = datetime.datetime.now().isoformat()

            try:
                execution_arn, job_id = start_state_machine_execution(
                    f"s3://{bucket}/{object_key}", start_date
                )

                jobs_table.put_item(
                    Item=json.loads(
                        json.dumps(
                            {
                                "job_id": job_id,
                                "filename": filename,
                                "start_date": start_date,
                                "status": get_execution_status(execution_arn),
                                "approved": False,
                            }
                        ),
                        parse_float=Decimal,
                    )
                )

                return job_id
            except ClientError as exception:
                logger.error(exception, exc_info=True)
