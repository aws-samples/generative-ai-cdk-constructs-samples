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
import re
import tempfile

from typing import TypedDict
from urllib.parse import unquote_plus

from .processor import BedrockKBProcessor

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
QUESTIONNAIRE_TABLE_NAME = os.environ["QUESTIONNAIRE_TABLE_NAME"]

s3_client = boto3.client("s3")
dynamodb_client = boto3.resource("dynamodb")

dynamodb = boto3.resource("dynamodb")
questionnaire_table = dynamodb.Table(QUESTIONNAIRE_TABLE_NAME)

class Event(TypedDict):
    ExecutionName: str
    document_s3_path: str


class MalformedRequest(ValueError):
    pass


def parse_event(event: Event) -> tuple[str, str, str]:
    if "document_s3_path" in event and "ExecutionName" in event:
        document_s3_path: str = event["document_s3_path"]
        execution_name: str = event["ExecutionName"]
    else:
        raise MalformedRequest("Unknown event structure")

    logger.info(
        f"Got document_s3_path and execution_name from event: {document_s3_path} {execution_name}"
    )

    match = re.match("s3://(.+?)/(.+)", document_s3_path)

    if match:
        bucket = match.group(1)
        key = match.group(2)

        return bucket, unquote_plus(key), execution_name
    else:
        raise MalformedRequest(f"Invalid S3 URI: {document_s3_path}")


def handler(event: Event, context):
    """Lambda to preprocess an input RFP"""
    logger.debug("Received event %s", event)

    bucket, key, execution_name = parse_event(event)
    file_processor = BedrockKBProcessor(model_id=MODEL_ID)

    with tempfile.NamedTemporaryFile(suffix=f".{key.split(".")[-1]}") as doc_temp_file:
        s3_client.download_fileobj(bucket, key, doc_temp_file)
        doc_temp_file.seek(0)
        logger.info(f"Downloaded s3://{bucket}/{key}")

        file_date = None

        content = file_processor.process_file(doc_temp_file.name, file_date)

    for i in range(0, len(content)):
        content[i]["job_id"] = execution_name
        content[i]["question_number"] = i
        content[i]["approved"] = False

    logger.info("Writing questionnaire to DynamoDB")

    with questionnaire_table.batch_writer() as writer:
        for item in content:
            writer.put_item(Item=item)

    return {
        "JobId": execution_name,
        "QuestionNumbers": list(range(len(content))),
    }
