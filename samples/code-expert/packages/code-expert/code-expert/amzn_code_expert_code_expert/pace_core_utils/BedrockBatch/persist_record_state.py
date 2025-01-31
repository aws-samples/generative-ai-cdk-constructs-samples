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
from abc import ABC, abstractmethod

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class PersistRecordState(ABC):
    def __init__(self):
        self.state = {}

    @abstractmethod
    def add_record(self, record_id: str, record: dict):
        pass

    def get_record(self, record_id: str) -> dict | None:
        return self.state.get(record_id)

    @abstractmethod
    def persist_state(self):
        pass

    @abstractmethod
    def load_state(self):
        pass


class PersistRecordStateS3(PersistRecordState):
    def __init__(self, s3_client: "S3Client", bucket: str, prefix: str):
        super().__init__()
        self.s3_client = s3_client
        self.bucket = bucket
        self.prefix = prefix

    def add_record(self, record_id: str, record: dict):
        self.state[record_id] = record

    def persist_state(self):
        key = f"{self.prefix}/state.json"
        self.s3_client.put_object(Bucket=self.bucket, Key=key, Body=json.dumps(self.state))

    def load_state(self):
        key = f"{self.prefix}/state.json"
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            self.state = json.loads(response["Body"].read().decode("utf-8"))
        except self.s3_client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"No state file found at s3://{self.bucket}/{key}")
