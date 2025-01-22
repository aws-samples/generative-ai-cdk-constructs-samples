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
import logging
import os

from typing import TypedDict

from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

AWS_REGION = os.getenv("AWS_REGION", default="us-east-1")
ACCOUNT = os.getenv("ACCOUNT")
STATE_MACHINE_NAME = os.getenv("STATE_MACHINE_NAME")
JOBS_TABLE_NAME = os.environ["JOBS_TABLE_NAME"]

s3_client = boto3.client("s3")
dynamodb_client = boto3.resource("dynamodb")

dynamodb = boto3.resource("dynamodb")
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)

step_functions = boto3.client("stepfunctions")


class Event(TypedDict):
    ExecutionArn: str
    Status: str


class MalformedRequest(ValueError):
    pass


def parse_event(event: Event) -> tuple[str, str]:
    if "ExecutionArn" in event and "Status" in event:
        execution_arn: str = event["ExecutionArn"]
        job_id: str = execution_arn.split(":")[-1]
        status: str = event["Status"]
    else:
        raise MalformedRequest("Unknown event structure")

    logger.info(f"Got job_id from event: {job_id}")

    return job_id, status


def handler(event: Event, context):
    """Lambda to record processing status for RFPs"""
    logger.debug("Received event %s", event)

    job_id, status = parse_event(event)

    try:
        response = jobs_table.update_item(
            Key={
                "job_id": job_id,
            },
            UpdateExpression="SET #st = :s",
            ExpressionAttributeValues={
                ":s": status,
            },
            ExpressionAttributeNames={"#st": "status"},
            ReturnValues="UPDATED_NEW",
        )

        logger.debug(response)

    except ClientError as exception:
        logger.error(exception, exc_info=True)
        raise exception
