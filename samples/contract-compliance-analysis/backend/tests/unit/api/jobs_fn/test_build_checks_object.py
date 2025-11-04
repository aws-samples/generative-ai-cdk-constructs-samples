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
import sys
import os
from unittest.mock import MagicMock, patch

# Add paths for imports
jobs_fn_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'jobs_fn')
common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer')
if jobs_fn_path not in sys.path:
    sys.path.insert(0, jobs_fn_path)
if common_layer_path not in sys.path:
    sys.path.insert(0, common_layer_path)

from model import Job, Workflow
from datetime import datetime, timezone
import index


@pytest.fixture
def sample_job():
    """Create a sample job for testing"""
    return Job(
        id="test-job-id",
        document_s3_key="test.pdf",
        contract_type_id="service-agreement",
        guidelines_compliant=True,
        legislation_compliant=None,
        total_clause_types_by_risk={
            "high": {"quantity": 1, "threshold": 0},
            "medium": {"quantity": 0, "threshold": 1},
            "low": {"quantity": 0, "threshold": 3},
            "none": {"quantity": 0}
        },
        total_compliance_by_impact={
            "high": {"compliant": {"quantity": 0, "risk": "none"}, "missing": {"quantity": 1, "risk": "high"}, "non_compliant": {"quantity": 0, "risk": "high"}},
            "medium": {"compliant": {"quantity": 0, "risk": "none"}, "missing": {"quantity": 0, "risk": "high"}, "non_compliant": {"quantity": 0, "risk": "medium"}},
            "low": {"compliant": {"quantity": 0, "risk": "none"}, "missing": {"quantity": 0, "risk": "medium"}, "non_compliant": {"quantity": 0, "risk": "low"}}
        },
        unknown_total=0
    )


def test_build_checks_object_with_guidelines_only(sample_job):
    """Test building checks object with only guidelines check"""
    sample_job.legislation_check_execution_arn = None
    
    result = index.build_checks_object(sample_job, "SUCCEEDED")
    
    assert result["guidelines"]["compliant"] == True
    assert result["guidelines"]["processingStatus"] == "SUCCEEDED"
    assert "metrics" in result["guidelines"]
    assert result["guidelines"]["metrics"]["totalClauseTypesByRisk"]["high"]["quantity"] == 1
    assert result["guidelines"]["metrics"]["unknownTotal"] == 0
    assert result["legislation"] is None


def test_build_checks_object_with_legislation_check(sample_job):
    """Test building checks object with legislation check"""
    with patch.object(index, 'workflows_repository') as mock_workflows_repo:
        sample_job.legislation_check_execution_arn = "arn:aws:states:us-east-1:123456789012:execution:CheckLegislation:test-exec"
        sample_job.legislation_compliant = True
        
        mock_legislation_workflow = Workflow(
            id="test-exec",
            state_machine_id="arn:aws:states:us-east-1:123456789012:stateMachine:CheckLegislation",
            status="SUCCEEDED",
            start_date=datetime.now(timezone.utc)
        )
        
        result = index.build_checks_object(sample_job, "SUCCEEDED", mock_legislation_workflow)
        
        assert result["guidelines"]["compliant"] == True
        assert result["guidelines"]["processingStatus"] == "SUCCEEDED"
        assert result["legislation"] is not None
        assert result["legislation"]["compliant"] == True
        assert result["legislation"]["processingStatus"] == "SUCCEEDED"


def test_build_checks_object_with_null_legislation_workflow(sample_job):
    """Test building checks object when legislation workflow doesn't exist"""
    with patch.object(index, 'workflows_repository') as mock_workflows_repo:
        sample_job.legislation_check_execution_arn = "arn:aws:states:us-east-1:123456789012:execution:CheckLegislation:test-exec"
        sample_job.legislation_compliant = False
        
        mock_workflows_repo.get_state_machine_execution_details.return_value = None
        
        result = index.build_checks_object(sample_job, "SUCCEEDED")
        
        assert result["guidelines"]["compliant"] == True
        assert result["legislation"] is None


def test_build_checks_object_with_none_compliant_values(sample_job):
    """Test building checks object with None compliant values"""
    sample_job.guidelines_compliant = None
    sample_job.legislation_check_execution_arn = None
    
    result = index.build_checks_object(sample_job, "RUNNING")
    
    assert result["guidelines"]["compliant"] is None
    assert result["guidelines"]["processingStatus"] == "RUNNING"
    assert result["legislation"] is None
