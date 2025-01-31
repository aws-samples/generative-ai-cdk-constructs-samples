#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from pydantic import BaseModel

from amzn_code_expert_code_expert.pace_core_utils.types import create_typed_dict_from_model


class MyModel(BaseModel):
    foo: str
    bar: list[str]


def test_it_can_convert_model_to_dict():
    MyModelDict = create_typed_dict_from_model(MyModel)

    expected_keys = set(MyModel.__annotations__.keys())
    result_keys = set(MyModelDict.__annotations__.keys())
    assert expected_keys == result_keys
