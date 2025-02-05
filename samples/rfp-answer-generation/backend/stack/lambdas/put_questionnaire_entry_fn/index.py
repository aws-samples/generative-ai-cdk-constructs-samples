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
questionnaire_table = dynamodb.Table(os.environ["QUESTIONNAIRE_TABLE"])


class Job(TypedDict):
    approved: bool
    filename: str
    job_id: str
    start_date: str
    status: str


class Question(TypedDict):
    job_id: str
    question_number: int
    answer: str
    question: str
    approved: bool
    date: str
    qa_lambda_request_id: str
    reasoning: str
    topic: str


class OutputEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def validate_questionnaire_entry(entry: Question):
    if {"question", "answer", "approved", "job_id", "question_number", "topic"} > set(
        entry
    ):
        raise ValueError
    if type(entry["question"]) != str | type(entry["answer"]) != str:
        raise TypeError
    if type(entry["question_number"]) != int:
        raise TypeError
    if type(entry["approved"]) != bool:
        raise TypeError
    if not entry["job_id"] or len(entry["job_id"]) > 100:
        raise ValueError


def handler(event, _context):
    logger.debug(event)

    response = {
        "headers": {
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
        }
    }
    try:
        body = json.loads(event["body"])

        if not body or not isinstance(body, dict):
            raise ValueError

        validate_questionnaire_entry(body)

        questionnaire_table.put_item(
            Item=json.loads(json.dumps(body), parse_float=Decimal)
        )

    except (KeyError, ValueError) as exception:
        logger.error(exception, exc_info=True)
        response["statusCode"] = 400

        return response

    except ClientError as exception:
        logger.error(exception, exc_info=True)
        response["statusCode"] = 500

        return response

    response["statusCode"] = 200

    return response
