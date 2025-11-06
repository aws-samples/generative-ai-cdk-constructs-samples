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
from unittest.mock import Mock
from repository.sfn_workflows_repository import StepFunctionsWorkflowsRepository
from schema import StartWorkflowRequest


def test_start_execution_raises_assertion_error_on_bad_response():
    """Test that start_execution raises AssertionError on bad HTTP response"""
    mock_client = Mock()
    mock_client.start_execution.return_value = {
        'ResponseMetadata': {'HTTPStatusCode': 400}
    }

    repository = StepFunctionsWorkflowsRepository("test-arn", mock_client)
    workflow_input = StartWorkflowRequest(
        document_s3_path="test.pdf",
        contract_type_id="service-agreement",
        additional_checks=None
    )

    with pytest.raises(AssertionError):
        repository.start_execution(workflow_input)


def test_get_state_machine_execution_details_returns_none_on_exception():
    """Test that get_state_machine_execution_details returns None on exception"""
    mock_client = Mock()
    mock_client.describe_execution.side_effect = Exception("Test error")

    repository = StepFunctionsWorkflowsRepository("test-arn", mock_client)

    result = repository.get_state_machine_execution_details("test-execution-id")
    assert result is None
