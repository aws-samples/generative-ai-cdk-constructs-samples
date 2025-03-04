#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import pytest

from amzn_code_expert_code_expert.EvaluateRules import EvaluateRules
from amzn_code_expert_code_expert.models.rules import RuleSet
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.manifest import (
    random_record_id,
)
from amzn_code_expert_code_expert.prompt_templates import get_prompt_templates
from amzn_code_expert_code_expert.ziprepo import ZipRepo


@pytest.mark.integration
def test_evaluate_rules_sync(bedrock_runtime_client, aws_resources_config, test_data_rules_json, test_data_repo):
    rules = RuleSet.model_validate_json(test_data_rules_json)
    prompt_templates = get_prompt_templates()
    repo_archive = test_data_repo
    with ZipRepo(repo_archive) as repo:
        evaluator = EvaluateRules(rules, repo, "us.anthropic.claude-3-haiku-20240307-v1:0", prompt_templates)
        findings = evaluator.evaluate(bedrock_runtime_client)
    assert "test_exclude.py" not in evaluator.rule_mapper.rules_by_file
    assert len(findings) >= 1


@pytest.mark.integration
def test_prepare_batch_evaluation(
    s3_client, bedrock_client, aws_resources_config, test_data_rules_json, test_data_repo
):
    rules = RuleSet.model_validate_json(test_data_rules_json)
    prompt_templates = get_prompt_templates()
    repo_archive = test_data_repo
    batch_bucket = aws_resources_config["batch_bucket"]
    bedrock_batch_role = aws_resources_config["bedrock_batch_role"]

    job_name = random_record_id()
    batch_prefix = "tests/" + job_name

    model_id = "us.anthropic.claude-3-haiku-20240307-v1:0"
    with ZipRepo(repo_archive) as repo:
        evaluator = EvaluateRules(rules, repo, model_id, prompt_templates)
        manifests = evaluator.prepare_batch_evaluation(s3_client, batch_bucket, batch_prefix)
    assert len(manifests) == 1
    manifest = s3_client.get_object(Bucket=batch_bucket, Key=manifests[0])["Body"].read().decode("utf-8")
    # count JSONL records in manifest
    assert len(manifest.splitlines()) >= 100
    print(manifests)
