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
import sys
import tempfile
import zipfile
from io import IOBase, BytesIO
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class ZipRepo(tempfile.TemporaryDirectory):
    file: str | os.PathLike[str] | IO[bytes] | IOBase
    path: str = ""

    def __init__(self, file: str | os.PathLike[str] | IO[bytes]):
        super().__init__()
        self.file = file

    def _extract_archive(self) -> None:
        """Separate method to handle zip extraction"""
        with zipfile.ZipFile(self.file) as zip_ref:
            for file_info in zip_ref.infolist():
                if os.path.isabs(file_info.filename) or ".." in file_info.filename:
                    continue
                zip_ref.extract(file_info, self.path)

    def __enter__(self) -> str:
        self.path = super().__enter__()
        try:
            self._extract_archive()
            return self.path
        except Exception as e:
            self.__exit__(*sys.exc_info())
            raise e

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)


def get_repo_content(s3_client: "S3Client", bucket: str, repo_key: str) -> BytesIO:
    repo_content = s3_client.get_object(Bucket=bucket, Key=repo_key)["Body"].read()
    return BytesIO(repo_content)
