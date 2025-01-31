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

import pytest

from amzn_code_expert_code_expert.ziprepo import ZipRepo


def create_zip_file(files):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, content in files.items():
            zip_file.writestr(file_name, content)
    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def valid_zip_file():
    test_files = {"test1.txt": "content1", "folder/test2.txt": "content2"}
    return create_zip_file(test_files)


@pytest.fixture
def invalid_zip_file():
    return BytesIO(b"invalid zip content")


def test_zip_repo_initialization(valid_zip_file):
    repo = ZipRepo(valid_zip_file)
    assert isinstance(repo.file, BytesIO)
    assert repo.path is ""


def test_extract_archive(valid_zip_file):
    with ZipRepo(valid_zip_file) as temp_dir:
        assert os.path.isdir(temp_dir)
        assert os.path.exists(os.path.join(temp_dir, "test1.txt"))
        assert os.path.exists(os.path.join(temp_dir, "folder", "test2.txt"))

        with open(os.path.join(temp_dir, "test1.txt"), "r") as f:
            assert f.read() == "content1"

        with open(os.path.join(temp_dir, "folder", "test2.txt"), "r") as f:
            assert f.read() == "content2"


def test_extract_archive_security():
    test_files = {"/etc/passwd": "malicious content", "../outside.txt": "malicious content", "safe.txt": "safe content"}
    zip_file = create_zip_file(test_files)

    with ZipRepo(zip_file) as temp_dir:
        assert os.path.isdir(temp_dir)
        assert not os.path.exists(os.path.join(temp_dir, "etc", "passwd"))
        assert not os.path.exists(os.path.join(os.path.dirname(temp_dir), "outside.txt"))
        assert os.path.exists(os.path.join(temp_dir, "safe.txt"))


def test_context_manager(valid_zip_file):
    with ZipRepo(valid_zip_file) as temp_dir:
        assert os.path.isdir(temp_dir)
        assert os.path.exists(os.path.join(temp_dir, "test1.txt"))

    assert not os.path.exists(temp_dir)


def test_context_manager_exception_in_enter(invalid_zip_file):
    with pytest.raises(zipfile.BadZipFile):
        with ZipRepo(invalid_zip_file) as temp_dir:
            pass  # This should not be reached

    # The temporary directory should have been cleaned up
    assert not hasattr(ZipRepo, "path") or not os.path.exists(ZipRepo.path)


def test_context_manager_exception_in_block(valid_zip_file):
    with pytest.raises(RuntimeError):
        with ZipRepo(valid_zip_file) as temp_dir:
            raise RuntimeError("Test exception")

    # The temporary directory should have been cleaned up
    assert not hasattr(ZipRepo, "path") or not os.path.exists(ZipRepo.path)


def test_file_as_path(tmp_path):
    test_files = {"test.txt": "test content"}
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for file_name, content in test_files.items():
            zip_file.writestr(file_name, content)

    with ZipRepo(zip_path) as temp_dir:
        assert os.path.isdir(temp_dir)
        assert os.path.exists(os.path.join(temp_dir, "test.txt"))


def test_file_as_file_object(tmp_path):
    test_files = {"test.txt": "test content"}
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for file_name, content in test_files.items():
            zip_file.writestr(file_name, content)

    with open(zip_path, "rb") as file:
        with ZipRepo(file) as temp_dir:
            assert os.path.isdir(temp_dir)
            assert os.path.exists(os.path.join(temp_dir, "test.txt"))
