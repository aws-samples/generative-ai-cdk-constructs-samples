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

from typing import Dict
from . import DocumentRepository


class InMemoryDocumentRepository(DocumentRepository):
    """In-memory implementation of DocumentRepository"""

    def __init__(self):
        self._documents: Dict[str, bytes] = {}

    def add_document(self, uri: str, content: bytes) -> None:
        """Add a document to the in-memory store"""
        self._documents[uri] = content

    def get_document(self, uri: str) -> bytes:
        """Retrieve document bytes from in-memory store"""
        if uri not in self._documents:
            raise FileNotFoundError(f"Document not found: {uri}")
        return self._documents[uri]
