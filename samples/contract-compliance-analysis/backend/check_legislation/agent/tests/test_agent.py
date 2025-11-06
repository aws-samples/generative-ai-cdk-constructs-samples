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

"""
Basic tests for the legislation agent.
"""
from faker import Faker
import pytest
from unittest.mock import Mock

from repository import ClauseRepository
from agents import AgentArchitecture
from model import LegislationCheck, CheckedClause, AdditionalChecks
from schema import CheckLegislationRequest


@pytest.fixture
def clause_repository():
  return Mock(spec=ClauseRepository)


@pytest.fixture
def agent_architecture():
  return Mock(spec=AgentArchitecture)


def test_it_responds_with_check(clause_repository, agent_architecture, clause, faker: Faker, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "mock_value")

    # sut needs to be imported here for ENV monkeypatching to work
    from entrypoint import _invoke

    # given
    a_legislation_check = LegislationCheck(compliant=faker.boolean(), analysis=faker.sentence())
    clause_repository.get_clause.return_value = clause
    agent_architecture.analyze_clause.return_value = a_legislation_check

    request = CheckLegislationRequest.model_validate(
        {
            "JobId": clause.job_id,
            "ClauseNumber": clause.clause_number,
            "LegislationCheck": {"legislationId": faker.word()},
        }
    )

    # when
    response = _invoke(clause_repository, agent_architecture, request)

    # then
    assert response.Evaluation.Status == "OK"

    checked_clause = CheckedClause(job_id=clause.job_id, clause_number=clause.clause_number, text=clause.text, additional_checks=AdditionalChecks(legislation_check=a_legislation_check))

    clause_repository.update_legislation_checks.assert_called_with(checked_clause)
