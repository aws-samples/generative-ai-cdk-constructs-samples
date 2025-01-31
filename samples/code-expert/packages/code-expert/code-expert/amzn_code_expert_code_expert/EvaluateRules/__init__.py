#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from typing import TYPE_CHECKING, Optional, Callable

import jinja2

from amzn_code_expert_code_expert.models.findings import RuleFinding, EvaluationError
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.manifest import (
    BedrockBatchInputProcessor,
)
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.persist_record_state import PersistRecordStateS3

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient
    from mypy_boto3_s3 import S3Client

from amzn_code_expert_code_expert.models.rules import RuleSet
from .file_manager import FileManager
from .rule_detector import RuleDetector
from .rule_evaluator import RuleEvaluator, create_batch_manifests
from .rule_mapper import RuleMapper


class EvaluateRules:
    def __init__(
        self,
        rules: RuleSet,
        repo: str,
        model_id: str,
        prompt_templates: jinja2.Environment,
        multiple_evaluation: bool = True,
    ):
        """Initialize the rule evaluator with a RuleSet and a repository path.

        Args:
            rules (RuleSet): The rule set that can be evaluated on the code
            repo (str): The path to the code to evaluate
            model_id (str): The Bedrock model id
            multiple_evaluation (bool, optional): Minimize model inference by evaluating multiple rules per file. Defaults to True.
        """
        self.file_manager = FileManager(repo)
        self.rule_detector = RuleDetector(self.file_manager, rules)
        self.rule_mapper = RuleMapper(self.file_manager, self.rule_detector)
        self.rule_evaluator = RuleEvaluator(
            self.file_manager, self.rule_mapper, prompt_templates, model_id, multiple_evaluation=multiple_evaluation
        )
        self.model_id = model_id
        self.multiple_evaluation = multiple_evaluation

    def evaluate(
        self, bedrock_runtime: "BedrockRuntimeClient", heartbeat: Optional[Callable[[], None]] = None
    ) -> tuple[list[RuleFinding], list[EvaluationError]]:
        """Evaluate the rules on the repository and return findings.

        Args:
            bedrock_runtime (BedrockRuntimeClient, optional): The Bedrock runtime client to use.
            heartbeat: Optional callback function to send a heartbeat while the task runs.

        Returns:
            tuple[list[RuleFinding], list[EvaluationError]]: A tuple containing:
                - A list of RuleFinding objects representing the findings from evaluating the rules
                - A list of EvaluationError objects representing any errors that occurred during evaluation
        """
        findings: list[RuleFinding] = []
        errors: list[EvaluationError] = []
        simple_findings, simple_errors = self.rule_evaluator.evaluate_simple_rules(bedrock_runtime, heartbeat)
        findings.extend(simple_findings)
        errors.extend(simple_errors)
        context_findings, context_errors = self.rule_evaluator.evaluate_context_rules(bedrock_runtime, heartbeat)
        findings.extend(context_findings)
        errors.extend(context_errors)
        return findings, errors

    def prepare_batch_evaluation(
        self, s3_client: "S3Client", batch_bucket: str, batch_prefix: str
    ) -> list[str]:
        """Prepare the batch evaluation of the rules on the repository and return the S3 keys of the manifests.

        Args:
            s3_client: The S3 client to use for interacting with S3
            batch_bucket: The S3 bucket name where batch processing artifacts will be stored
            batch_prefix: The prefix (folder path) within the S3 bucket for batch artifacts

        Returns:
            list[str]: A list of S3 keys for model inference job manifests.
        """
        bedrock_batch_input = BedrockBatchInputProcessor(s3_client, self.model_id, batch_bucket, batch_prefix)
        persist_record_state = PersistRecordStateS3(s3_client, batch_bucket, batch_prefix)

        self.rule_evaluator.prepare_batch_evaluate_simple_rules(bedrock_batch_input, persist_record_state)
        self.rule_evaluator.prepare_batch_evaluate_context_rules(bedrock_batch_input, persist_record_state)

        persist_record_state.persist_state()

        return create_batch_manifests(bedrock_batch_input)
