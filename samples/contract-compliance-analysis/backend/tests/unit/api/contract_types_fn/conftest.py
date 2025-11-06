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
import importlib.util

# Import helper to ensure we get the correct index module
def get_contract_types_index_module():
    """Get the contract_types function index module, ensuring it's the correct one"""
    import importlib.util
    import sys

    # Clear any cached contract_types index module to avoid conflicts
    modules_to_clear = [k for k in sys.modules.keys() if k.startswith('contract_types_index') or (k == 'index' and 'contract_types_fn' in str(sys.modules.get(k, '')))]
    for module in modules_to_clear:
        del sys.modules[module]

    # Import the contract_types index module specifically
    contract_types_index_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'contract_types_fn', 'index.py')
    spec = importlib.util.spec_from_file_location("contract_types_index", contract_types_index_path)
    contract_types_index = importlib.util.module_from_spec(spec)

    # Add necessary paths to sys.path temporarily
    common_layer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer'))
    contract_types_fn_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'contract_types_fn'))

    original_path = sys.path.copy()
    try:
        sys.path.insert(0, contract_types_fn_path)
        sys.path.insert(0, common_layer_path)
        spec.loader.exec_module(contract_types_index)
    finally:
        sys.path[:] = original_path

    return contract_types_index

@pytest.fixture
def contract_types_index():
    """Fixture to provide the contract_types index module"""
    return get_contract_types_index_module()

# Note: We don't modify sys.path globally to avoid conflicts with other test files
# All imports are handled within the fixture function
# All tests should use the contract_types_index fixture instead

@pytest.fixture
def contract_types_models():
    """Fixture to provide contract types models with proper path setup"""
    import sys
    contract_types_fn_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'api', 'contract_types_fn'))
    common_layer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'stack', 'lambda', 'common_layer'))

    original_path = sys.path.copy()
    try:
        sys.path.insert(0, contract_types_fn_path)
        sys.path.insert(0, common_layer_path)
        from model import ContractType, ImportJob
        from schema import ContractTypeRequest, ImportContractTypeRequest

        # Return as a namespace object for easy access
        class Models:
            pass

        models = Models()
        models.ContractType = ContractType
        models.ImportJob = ImportJob
        models.ContractTypeRequest = ContractTypeRequest
        models.ImportContractTypeRequest = ImportContractTypeRequest

        return models
    finally:
        sys.path[:] = original_path