#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import boto3
import pytest
from moto import mock_aws

from check_legislation.agent.repository.s3_document_repository import S3DocumentRepository


@mock_aws
def test_get_document():
    # Setup
    bucket_name = "test-bucket"
    key = "test-document.pdf"
    s3_uri = f"s3://{bucket_name}/{key}"
    test_content = b"test document content"

    # Create mock S3 bucket and object
    s3_client = boto3.client('s3', region_name='us-east-1')
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=test_content)

    # Test
    repository = S3DocumentRepository()
    result = repository.get_document(s3_uri)

    # Assert
    assert result == test_content
