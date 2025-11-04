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
from urllib.parse import urlparse
from . import DocumentRepository


class S3DocumentRepository(DocumentRepository):
    """S3 implementation of DocumentRepository"""

    def __init__(self):
        self.s3_client = boto3.client('s3')

    def get_document(self, uri: str) -> bytes:
        """Download document from S3 and return bytes"""
        parsed_uri = urlparse(uri)
        bucket = parsed_uri.netloc
        key = parsed_uri.path.lstrip('/')

        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
