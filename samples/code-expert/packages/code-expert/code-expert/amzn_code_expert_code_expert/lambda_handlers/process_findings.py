#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import json
import os
from enum import Enum
from typing import TYPE_CHECKING, Optional, TypeVar

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field

from amzn_code_expert_code_expert.EvaluateRules.rule_evaluator import process_batch_evaluate_simple_rules
from amzn_code_expert_code_expert.models.findings import RuleFinding, EvaluationError
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.output import BedrockBatchOutputProcessor
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.persist_record_state import PersistRecordStateS3

if TYPE_CHECKING:
    # mypy_boto3_* is a test-dependency only and not available at runtime
    # It is also only ever used as type-hints, so we can import it during TYPE_CHECKING only
    from mypy_boto3_s3 import S3Client

logger = Logger()

BATCH_BUCKET = os.getenv("BATCH_BUCKET")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET")
MODEL_ID = os.getenv("MODEL_ID")

s3_client: "S3Client" = boto3.client("s3")


class BatchJobStatus(Enum):
    SUBMITTED = "Submitted"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    STOPPING = "Stopping"
    STOPPED = "Stopped"
    PARTIALLY_COMPLETED = "PartiallyCompleted"
    EXPIRED = "Expired"
    VALIDATING = "Validating"
    SCHEDULED = "Scheduled"




class BatchInferenceJobSFNOutput(BaseModel):
    status: BatchJobStatus = Field(..., description="Status of the batch job")
    bucket: str = Field(..., description="S3 bucket where the output is stored")
    keys: list[str] = Field(..., description="Keys of the output files")

class ProcessFindingsTaskInput(BaseModel):
    job_name: str
    jobs: list[BatchInferenceJobSFNOutput]
    model_id: Optional[str] = None


class ProcessFindingsTaskResult(BaseModel):
    bucket: str
    key: str
    errors_key: str


T = TypeVar("T", RuleFinding, EvaluationError)


def put_s3_objects(s3: "S3Client", output_bucket: str, objects: list[T], prefix: str, job_name: str) -> str:
    """
    Generic function to put objects to S3 with specified prefix.

    Args:
        s3: S3 client instance
        output_bucket: Name of the S3 bucket
        objects: List of objects to serialize and store
        prefix: Folder prefix for the S3 key (e.g., 'findings/', 'errors/')

    Returns:
        str: The generated S3 key
    """
    output_key = os.path.join(prefix, f"{job_name}.json")
    logger.info(f"Putting objects to S3 bucket {output_bucket} with key {output_key}")

    s3.put_object(
        Bucket=output_bucket,
        Key=output_key,
        Body=json.dumps([obj.model_dump() for obj in objects], default=str, indent=2).encode("utf-8"),
    )
    return output_key


# Wrapper functions for specific use cases
def put_findings(s3: "S3Client", output_bucket: str, job_name: str, findings: list[RuleFinding]) -> str:
    return put_s3_objects(s3, output_bucket, findings, "findings/", job_name)


def put_errors(s3: "S3Client", output_bucket: str, job_name: str, errors: list[EvaluationError]) -> str:
    return put_s3_objects(s3, output_bucket, errors, "errors/", job_name)


@event_parser(model=ProcessFindingsTaskInput)
def handler(event: ProcessFindingsTaskInput, _context: LambdaContext) -> dict:
    logger.info(f"Received event: {event.model_dump()}")

    model_id = event.model_id if event.model_id else MODEL_ID
    batch_bucket = BATCH_BUCKET
    output_bucket = OUTPUT_BUCKET
    job_name = event.job_name
    batch_prefix = "input/" + job_name

    persist_record_state = PersistRecordStateS3(s3_client, batch_bucket, batch_prefix)
    persist_record_state.load_state()

    findings: list[RuleFinding] = []
    errors: list[EvaluationError] = []
    for job in event.jobs:
        logger.info(f"Processing job: {job.model_dump()}")

        if job.bucket != batch_bucket:
            logger.warning(f"Bucket {event.bucket} does not match expected bucket {batch_bucket}")

        batch_output_processor = BedrockBatchOutputProcessor(s3_client, model_id)
        for key in job.keys:
            logger.info(f"Processing output for key: {key}")
            f, e = process_batch_evaluate_simple_rules(batch_output_processor, job.bucket, key, persist_record_state)
            logger.info(f"Found {len(f)} findings")
            logger.debug(f)
            logger.info(f"Found {len(e)} errors")
            logger.debug(e)
            findings.extend(f)
            errors.extend(e)

    output_key = put_findings(s3_client, output_bucket, job_name, findings)
    logger.info(f"Findings put to S3 bucket {output_bucket} with key {output_key}")
    errors_key = put_errors(s3_client, output_bucket, job_name, errors)
    logger.info(f"Errors put to S3 bucket {output_bucket} with key {errors_key}")
    return ProcessFindingsTaskResult(bucket=output_bucket, key=output_key, errors_key=errors_key).model_dump()
