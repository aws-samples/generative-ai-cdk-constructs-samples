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

import csv
from pathlib import Path
from repository import ClauseRepository
from model import Clause, CheckedClause, AdditionalChecks


class InMemoryClauseRepository(ClauseRepository):  # type: ignore[misc]
    """In-memory implementation for local development"""

    def __init__(self) -> None:
        # Load test data from CSV file
        self.clauses = {}
        csv_path = Path(__file__).parent.parent / "evals" / "test_cases.csv"

        with open(csv_path, 'r', encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row['job_id'], int(row['clause_number']))
                self.clauses[key] = Clause(
                    job_id=row['job_id'],
                    clause_number=int(row['clause_number']),
                    text=row['text']
                )

        self.additional_checks: dict[tuple[str, int], AdditionalChecks] = {}

    def get_clause(self, job_id: str, clause_number: int) -> Clause:
        key = (job_id, clause_number)
        if key not in self.clauses:
            raise ValueError(f"Clause not found for job_id={job_id}, clause_number={clause_number}")
        return self.clauses[key]

    def update_legislation_checks(self, checked_clause: CheckedClause) -> None:
        """Update the additional_checks field for a clause"""
        key = (checked_clause.job_id, checked_clause.clause_number)
        self.additional_checks[key] = checked_clause.additional_checks
        print(f"Updated additional_checks for clause {key}: {self.additional_checks[key]}")

