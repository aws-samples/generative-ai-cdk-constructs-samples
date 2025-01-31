#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import os
from typing import TYPE_CHECKING, Optional

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel

from amzn_code_expert_code_expert.EvaluateRules import EvaluateRules
from amzn_code_expert_code_expert.models.rules import RuleSet, load_rules_s3
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.manifest import (
    random_record_id,
)
from amzn_code_expert_code_expert.prompt_templates import get_prompt_templates
from amzn_code_expert_code_expert.ziprepo import ZipRepo, get_repo_content

if TYPE_CHECKING:
    # mypy_boto3_* is a test-dependency only and not available at runtime
    # It is also only ever used as type-hints, so we can import it during TYPE_CHECKING only
    from mypy_boto3_s3 import S3Client

INPUT_BUCKET = os.getenv("INPUT_BUCKET")
BATCH_BUCKET = os.getenv("BATCH_BUCKET")
CONFIG_BUCKET = os.getenv("CONFIG_BUCKET")
RULES_KEY = os.getenv("RULES_KEY")
MODEL_ID = os.getenv("MODEL_ID")

logger = Logger()
s3_client: "S3Client" = boto3.client("s3")

_rules: RuleSet | None = None


class AnalyzeRepoTaskInput(BaseModel):
    repo_key: str
    multiple_evaluation: Optional[bool] = True
    model_id: Optional[str] = None


class AnalyzeRepoTaskResult(BaseModel):
    job_name: str
    manifests: list[str]


def load_rules(s3_client, bucket, key):
    #  amazonq-ignore-next-line
    global _rules
    _rules = load_rules_s3(s3_client, bucket, key)


@event_parser(model=AnalyzeRepoTaskInput)
def handler(event: AnalyzeRepoTaskInput, _context: LambdaContext) -> dict:
    logger.info(f"Received event: {event.model_dump()}")
    model_id = event.model_id if event.model_id else MODEL_ID
    batch_bucket = BATCH_BUCKET
    job_name = random_record_id()
    batch_prefix = "input/" + job_name
    logger.debug(f"Using batch prefix: {batch_prefix}")

    if not _rules:
        logger.info("Loading rules from S3")
        load_rules(s3_client, CONFIG_BUCKET, RULES_KEY)
    rules: RuleSet = _rules
    prompt_templates = get_prompt_templates()

    logger.info(f"Loading repo content from key: {event.repo_key}")
    repo_content = get_repo_content(s3_client, INPUT_BUCKET, event.repo_key)
    with ZipRepo(repo_content) as repo:
        logger.info("Evaluating rules against repo content")
        evaluator = EvaluateRules(
            rules, repo, model_id, prompt_templates, multiple_evaluation=event.multiple_evaluation
        )
        logger.debug(
            {
                "all_files": evaluator.file_manager.all_files,
                "languages_in_repo": [l.model_dump() for l in evaluator.rule_detector.languages],
                "categories_in_repo": [c.name for c in evaluator.rule_detector.categories],
                "rules_to_evaluate": [r.model_dump() for r in evaluator.rule_detector.simple_rules],
                "files_to_evaluate": list(evaluator.rule_mapper.rules_by_file.keys()),
            }
        )
        manifests = evaluator.prepare_batch_evaluation(s3_client, batch_bucket, batch_prefix)
    result = AnalyzeRepoTaskResult(manifests=manifests, job_name=job_name)
    logger.info(f"Generated {len(manifests)} manifests for evaluation")
    logger.debug(f"Result: {result.model_dump()}")
    return result.model_dump()
