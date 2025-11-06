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
from model import CheckedClause

from repository.dynamodb_clause_repository import DynamoDBClauseRepository

def test_it_updates_clauses_table(table_with_clause, clauses_table_name, clause, faker: Faker):
  # given
  repo = DynamoDBClauseRepository(table_name=clauses_table_name)

  # and a checked clause with additional checks
  additional_checks = {
    "legislation_check": {
      "compliant": faker.boolean(),
      "analysis": faker.sentence()
    }
  }

  checked_clause = CheckedClause.model_validate({
    "job_id": clause.job_id,
    "clause_number": clause.clause_number,
    "text": clause.text,
    "additional_checks": additional_checks,
  })

  # when
  repo.update_legislation_checks(checked_clause)

  # then, the table should have our check persisted
  response = table_with_clause.get_item(Key={
    "job_id": clause.job_id,
    "clause_number": clause.clause_number
  })

  assert "Item" in response
  assert response["Item"]["additional_checks"] == additional_checks