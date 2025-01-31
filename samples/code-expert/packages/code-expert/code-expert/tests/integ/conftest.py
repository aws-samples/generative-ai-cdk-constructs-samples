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
import zipfile
from io import BytesIO
from typing import TYPE_CHECKING

import pytest
from dotenv import load_dotenv

if TYPE_CHECKING:
    from mypy_boto3_bedrock import BedrockClient
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient
    from mypy_boto3_s3 import S3Client


def pytest_addoption(parser):
    parser.addoption("--env-file", action="store", default=".env.test", help="Environment file to load")
    parser.addoption("--repo", action="store", default=None, help="repo path")
    parser.addoption("--rules", action="store", default=None, help="rules json file")


@pytest.fixture(scope="session", autouse=True)
@pytest.mark.integration
def load_test_env(pytestconfig):
    env_file = pytestconfig.getoption("env_file")
    load_dotenv(env_file, override=True)


@pytest.fixture(scope="session")
@pytest.mark.integration
def aws_resources_config() -> dict:
    return {
        "input_bucket": os.environ.get("INPUT_BUCKET"),
        "output_bucket": os.environ.get("OUTPUT_BUCKET", os.environ.get("INPUT_BUCKET")),
        "config_bucket": os.environ.get("CONFIG_BUCKET"),
        "batch_bucket": os.environ.get("BATCH_BUCKET"),
        "rules_key": os.environ.get("RULES_KEY", "test-rules.json"),
        "repo_key": os.environ.get("REPO_KEY", "test-repo.zip"),
        "bedrock_batch_role": os.environ.get("BEDROCK_BATCH_ROLE"),
    }


@pytest.fixture(scope="session")
@pytest.mark.integration
def s3_client() -> "S3Client":
    import boto3

    s3: "S3Client" = boto3.client("s3")
    return s3


@pytest.fixture(scope="session")
@pytest.mark.integration
def bedrock_client() -> "BedrockClient":
    import boto3

    bedrock: "BedrockClient" = boto3.client("bedrock")
    return bedrock


@pytest.fixture(scope="session")
@pytest.mark.integration
def bedrock_runtime_client() -> "BedrockRuntimeClient":
    import boto3

    bedrock_runtime: "BedrockRuntimeClient" = boto3.client("bedrock-runtime")
    return bedrock_runtime


@pytest.fixture(scope="session")
@pytest.mark.integration
def test_data_path() -> str:
    return os.path.join(os.path.dirname(__file__), "..", "..", "test_data")


@pytest.fixture(scope="session")
@pytest.mark.integration
def test_data_rules_json(test_data_path, pytestconfig) -> str:
    rules_path = pytestconfig.getoption("rules") or test_data_path + "/evaluate_rules/rules.json"

    with open(rules_path, "r") as f:
        return f.read()


@pytest.fixture(scope="session")
@pytest.mark.integration
def test_data_repo(test_data_path, pytestconfig) -> BytesIO:
    repo_path = pytestconfig.getoption("repo") or test_data_path + "/evaluate_rules/code"

    archive = BytesIO()
    with zipfile.ZipFile(archive, mode="w") as z:
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                # Get the full file path
                file_path = os.path.join(root, file)
                # Calculate the archive name (path relative to the root directory)
                arcname = os.path.relpath(file_path, repo_path)
                # Add the file to the zip archive
                z.write(file_path, arcname)
    archive.seek(0)
    return archive
