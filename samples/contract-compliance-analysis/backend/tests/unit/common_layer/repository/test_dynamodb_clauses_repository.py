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

from faker import Faker

from model import Clause, AdditionalChecks, LegislationCheck

# sut
from repository.dynamodb_clauses_repository import DynamoDBClausesRepository


def test_it_can_get_clauses(table_with_clauses, clauses_table_name, job_id, clauses):
  # given
  repo = DynamoDBClausesRepository(table_name=clauses_table_name)

  # when
  retrieved_clauses = repo.get_clauses(job_id=job_id)

  assert len(retrieved_clauses) == 3

  for retrieved_clause in retrieved_clauses:
    clause = next(c for c in clauses if c.clause_number == retrieved_clause.clause_number)
    assert clause.model_dump() == retrieved_clause.model_dump()

def test_it_can_get_unknown_clauses(clauses_table_with_unknown_clause_type, clauses_table_name, job_id):
  # given
  repo = DynamoDBClausesRepository(table_name=clauses_table_name)

  # when
  unknown_clauses: list[Clause] = repo.get_clauses(job_id=job_id)

  # then
  assert len(unknown_clauses) == 1
  assert unknown_clauses[0].job_id == job_id

def test_it_can_get_clause_with_additional_checks(table_with_clauses, clauses_table_name, job_id):
  # given
  repo = DynamoDBClausesRepository(table_name=clauses_table_name)

  # when
  retrieved_clauses = repo.get_clauses(job_id=job_id)

  # then
  assert retrieved_clauses[0].additional_checks is not None
  assert retrieved_clauses[0].additional_checks.legislation_check is not None

def test_it_can_get_clause_with_legislation_checks(clauses_table, clauses_for, faker: Faker):
  # given
  a_compliance_status = faker.boolean()
  an_analysis = faker.text()
  checks = AdditionalChecks(legislation_check=LegislationCheck(compliant=a_compliance_status, analysis=an_analysis))

  a_job_id = faker.uuid4()

  clauses = clauses_for(_job_id=a_job_id, _additional_checks=checks)
  for clause in clauses:
    clauses_table.put_item(Item=clause.model_dump())

  repo = DynamoDBClausesRepository(table_name=clauses_table.table_name)

  # when
  retrieved_clauses = repo.get_clauses(job_id=a_job_id)

  # then
  assert retrieved_clauses[0].additional_checks is not None
  assert retrieved_clauses[0].additional_checks.legislation_check is not None
  assert retrieved_clauses[0].additional_checks.legislation_check.compliant == a_compliance_status
  assert retrieved_clauses[0].additional_checks.legislation_check.analysis == an_analysis
