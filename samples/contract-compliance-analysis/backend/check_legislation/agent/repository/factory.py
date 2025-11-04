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

import os
from repository import ClauseRepository, DocumentRepository
from repository.dynamodb_clause_repository import DynamoDBClauseRepository
from repository.in_memory_clause_repository import InMemoryClauseRepository
from repository.s3_document_repository import S3DocumentRepository


class RepositoryFactory:
    """Factory for creating repository instances"""

    @staticmethod
    def create_clause_repository(table_name: str) -> ClauseRepository:
        """Create a clause repository instance"""
        # Use in-memory repo for local development
        if os.getenv('TEST_LOCAL'):
            return InMemoryClauseRepository()
        return DynamoDBClauseRepository(table_name)

    @staticmethod
    def create_document_repository() -> DocumentRepository:
        if os.getenv('TEST_LOCAL'):
            raise NotImplementedError("In-memory DocumentRepository is not implemented")

        return S3DocumentRepository()
