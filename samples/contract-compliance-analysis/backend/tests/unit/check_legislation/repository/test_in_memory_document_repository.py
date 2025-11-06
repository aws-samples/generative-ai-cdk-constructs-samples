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

import pytest

from check_legislation.agent.repository.in_memory_document_repository import InMemoryDocumentRepository


def test_get_document():
    # Setup
    uri = "test://document.pdf"
    test_content = b"test document content"

    repository = InMemoryDocumentRepository()
    repository.add_document(uri, test_content)

    # Test
    result = repository.get_document(uri)

    # Assert
    assert result == test_content


def test_get_document_not_found():
    # Setup
    repository = InMemoryDocumentRepository()

    # Test & Assert
    with pytest.raises(FileNotFoundError, match="Document not found: nonexistent://doc"):
        repository.get_document("nonexistent://doc")
