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

from decimal import Decimal
from typing import TypedDict

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "WARNING").upper())

dynamodb = boto3.resource("dynamodb")
jobs_table = dynamodb.Table(os.environ["JOBS_TABLE"])


class Job(TypedDict):
    job_id: str
    approved: bool
    status: str
    start_date: str
    filename: str


class OutputEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def handler(event, _context):
    response = {
        "headers": {
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
        }
    }

    jobs: list[Job] = []
    scan_kwargs = {}

    try:
        logger.debug(event)

        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs["ExclusiveStartKey"] = start_key
            ddb_response = jobs_table.scan(**scan_kwargs)
            jobs.extend([item for item in ddb_response.get("Items", [])])
            start_key = ddb_response.get("LastEvaluatedKey", None)
            done = start_key is None

        response["statusCode"] = 200
        response["body"] = json.dumps(jobs)

        logger.debug(response)

        return response
    except (KeyError, ValueError) as exception:
        logger.error(exception, exc_info=True)
        response["statusCode"] = 400

        return response
    except ClientError as exception:
        logger.error(exception, exc_info=True)
        response["statusCode"] = 500

        return response
