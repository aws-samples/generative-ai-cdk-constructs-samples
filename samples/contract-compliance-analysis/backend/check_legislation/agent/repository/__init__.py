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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from check_legislation.agent.model import Clause, CheckedClause


class ClauseRepository(ABC):
    """Abstract repository interface for clause data access"""

    @abstractmethod
    def get_clause(self, job_id: str, clause_number: int):
        """Retrieve a clause by job_id and clause_number"""
        pass

    @abstractmethod
    def update_legislation_checks(self, checked_clause: "CheckedClause") -> None:
        """Update the legislation_checks field for a clause"""
        pass


class DocumentRepository(ABC):
    """Abstract repository interface for document data access"""

    @abstractmethod
    def get_document(self, uri: str) -> bytes:
        """Retrieve document bytes from the given URI"""
        pass
