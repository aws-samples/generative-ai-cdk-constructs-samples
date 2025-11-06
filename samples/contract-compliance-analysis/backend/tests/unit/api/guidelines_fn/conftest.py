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

# Setup paths for guidelines function testing
import sys
import os
import pytest
from moto import mock_aws
import boto3

# Add common layer and guidelines function source to Python path
common_layer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer'))
guidelines_fn_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'guidelines_fn'))
langchain_layer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'langchain_deps_layer'))

# Add paths to sys.path if not already there
for path in [guidelines_fn_path, common_layer_path, langchain_layer_path]:
    if path not in sys.path:
        sys.path.insert(0, path)

@pytest.fixture(scope="session", autouse=True)
def setup_aws_mocks():
    """Set up AWS mocks for the entire test session"""
    with mock_aws():
        # Set up mock AWS credentials
        # These are fake credentials required by the moto library for AWS service mocking.
        # They are never used for actual AWS authentication and have no security implications.
        # See: https://docs.getmoto.org/en/latest/docs/getting_started.html#how-do-i-avoid-tests-from-mutating-my-real-infrastructure
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'  # nosec B105
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'  # nosec B105
        os.environ['AWS_SESSION_TOKEN'] = 'testing'  # nosec B105
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

        # Create mock DynamoDB tables
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        # Create guidelines table
        try:
            dynamodb.create_table(
                TableName='test-guidelines-table',
                KeySchema=[
                    {'AttributeName': 'contract_type_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'clause_type_id', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'contract_type_id', 'AttributeType': 'S'},
                    {'AttributeName': 'clause_type_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
        except:
            pass

        # Create contract types table
        try:
            dynamodb.create_table(
                TableName='test-contract-types-table',
                KeySchema=[
                    {'AttributeName': 'contract_type_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'contract_type_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
        except:
            pass

        yield

@pytest.fixture(autouse=True)
def setup_env_vars():
    """Set up environment variables for each test"""
    os.environ['GUIDELINES_TABLE'] = 'test-guidelines-table'
    os.environ['CONTRACT_TYPES_TABLE'] = 'test-contract-types-table'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    yield

@pytest.fixture
def guidelines_module():
    """Fixture to provide the guidelines index module with proper isolation"""
    import importlib
    import importlib.util

    # Use a unique module name to avoid conflicts
    module_name = f"guidelines_fn_index_{id(pytest)}"

    # Remove from cache if exists
    if module_name in sys.modules:
        del sys.modules[module_name]

    # Load the module
    guidelines_index_path = os.path.join(guidelines_fn_path, 'index.py')
    spec = importlib.util.spec_from_file_location(module_name, guidelines_index_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    yield module

    # Cleanup
    if module_name in sys.modules:
        del sys.modules[module_name]