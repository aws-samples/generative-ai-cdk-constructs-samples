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

from .chain import QuestionAnsweringChainFacade
from .context import ContextRetriever

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

context_retriever = ContextRetriever()
qa_chain_facade = QuestionAnsweringChainFacade(context_retriever)

dynamodb_client = boto3.resource("dynamodb")
questionnaire_table = dynamodb_client.Table(os.environ["QUESTIONNAIRE_TABLE"])


class MalformedRequest(ValueError):
    pass


def parse_event(event) -> tuple[str, int]:
    if "JobId" in event and "QuestionNumber" in event:
        job_id: str = event["JobId"]
        question_number: int = event["QuestionNumber"]
    else:
        raise MalformedRequest("Unknown event structure")

    logger.debug(
        f"Got job_id and question_number from event: {job_id} {question_number}"
    )

    return job_id, question_number


def answer_question(question):
    result = qa_chain_facade.answer_question(question)

    return result["answer"], result["llm_output"]


def handler(event, context):

    job_id, question_number = parse_event(event)

    ddb_response = questionnaire_table.get_item(
        Key={"job_id": job_id, "question_number": question_number}
    )

    question_record = ddb_response.get("Item")
    logger.debug(f"Question record: {question_record}")

    answer, full_llm_output = answer_question(question_record["question"])
    logger.debug(f"LLM output:\n{full_llm_output.content}")

    question_record["answer"] = answer
    question_record["reasoning"] = full_llm_output.content
    question_record["qa_lambda_request_id"] = context.aws_request_id

    ddb_response = questionnaire_table.put_item(Item=question_record)

    logger.debug("DynamoDB update response: %s", ddb_response)

    return "OK"
