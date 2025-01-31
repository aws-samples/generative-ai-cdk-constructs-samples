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


class OutputEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def validate_str_input(input: str):
    if not input or len(input) > 100:
        raise ValueError


def get_questionnaire(job_id: str) -> list[Question]:
    logger.info("Getting jobs from DynamoDB")

    questionnaire = []
    query_kwargs = {"KeyConditionExpression": Key("job_id").eq(job_id)}

    try:
        done = False
        start_key = None
        while not done:
            if start_key:
                query_kwargs["ExclusiveStartKey"] = start_key
            ddb_response = questionnaire_table.query(**query_kwargs)
            questionnaire.extend(ddb_response.get("Items", []))
            start_key = ddb_response.get("LastEvaluatedKey", None)
            done = start_key is None
    except ClientError as exception:
        logger.debug(exception, exc_info=True)
        raise
    return questionnaire


def get_job_info(job_id: str) -> Job:
    response = jobs_table.get_item(Key={"job_id": job_id})
    info = response.get("Item", {})

    return info


def group_by_topic(questionnaire: dict) -> dict[str, list[Question]]:
    logger.info("Grouping questionnaire by topic")

    topics = {}
    for question in questionnaire:
        topic = question["topic"]
        if topic in topics:
            topics[topic].append(question)
        else:
            topics[topic] = [question]

    return topics


def handler(event, _context):
    response = {
        "headers": {
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
        }
    }
    questionnaire = []
    try:
        logger.debug(event)
        job_id: str = event["pathParameters"]["job_id"]
        validate_str_input(job_id)
        questionnaire = get_questionnaire(job_id)
        questionnaire_by_topic = group_by_topic(questionnaire)
        job_info = get_job_info(job_id)

    except (KeyError, ValueError) as exception:
        logger.debug(exception, exc_info=True)
        response["statusCode"] = 400
        return response
    except ClientError as exception:
        logger.debug(exception, exc_info=True)
        response["statusCode"] = 500
        return response

    response["statusCode"] = 200
    response["body"] = json.dumps(
        {
            "questionnaire": questionnaire_by_topic,
            "filename": job_info["filename"],
            "job_id": job_info["job_id"],
            "start_date": job_info["start_date"],
        },
        cls=OutputEncoder,
    )
    return response
