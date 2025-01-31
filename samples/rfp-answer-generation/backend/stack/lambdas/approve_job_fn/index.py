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

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "WARNING").upper())

dynamodb = boto3.resource("dynamodb")
questionnaire_table = dynamodb.Table(os.environ["QUESTIONNAIRE_TABLE"])
jobs_table = dynamodb.Table(os.environ["JOBS_TABLE"])


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


class QuestionnaireNotFound(ValueError):
    pass


class OutputEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def update_job(job_id: str):
    jobs_table.update_item(
        Key={
            "job_id": job_id,
        },
        UpdateExpression="SET #ap = :a",
        ExpressionAttributeValues={
            ":a": True,
        },
        ExpressionAttributeNames={"#ap": "approved"},
        ReturnValues="UPDATED_NEW",
    )


def update_questionnaire(job_id: str):
    response = questionnaire_table.query(
        KeyConditionExpression=Key("job_id").eq(job_id)
    )

    if "Items" not in response:
        raise QuestionnaireNotFound

    questionnaire: list[Question] = response["Items"]

    with questionnaire_table.batch_writer() as writer:
        for item in questionnaire:
            approved_item = item.copy()
            approved_item["approved"] = True
            writer.put_item(Item=approved_item)


def handler(event, context):
    logger.debug("Received event %s", event)

    response = {
        "headers": {
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
        }
    }

    try:
        job_id: str = event["pathParameters"]["job_id"]

        update_questionnaire(job_id)
        update_job(job_id)

    except (KeyError, ValueError) as exception:
        logger.debug(exception, exc_info=True)
        response["statusCode"] = 400
        return response
    except (ClientError, QuestionnaireNotFound) as exception:
        logger.debug(exception, exc_info=True)
        response["statusCode"] = 500
        return response

    response["statusCode"] = 200
    return response
