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
from unittest.mock import patch, MagicMock
from aws_lambda_powertools.event_handler.exceptions import NotFoundError
import sys
import os

# Add the jobs function path to sys.path for imports
jobs_fn_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'jobs_fn')
common_layer_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer')
if jobs_fn_path not in sys.path:
    sys.path.insert(0, jobs_fn_path)
if common_layer_path not in sys.path:
    sys.path.insert(0, common_layer_path)


def test_get_job_raises_not_found_error_when_job_not_exists(jobs_table, jobs_index):
    """Test that get_job raises NotFoundError when job doesn't exist"""
    get_job = jobs_index.get_job

    # Mock the jobs_repository to return None (job not found)
    with patch.object(jobs_index, 'jobs_repository') as mock_jobs_repo:
        mock_jobs_repo.get_job.return_value = None

        with pytest.raises(NotFoundError):
            get_job("non-existent-job-id")
