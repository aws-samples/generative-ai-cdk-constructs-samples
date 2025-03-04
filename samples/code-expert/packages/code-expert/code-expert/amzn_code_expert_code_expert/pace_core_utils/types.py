#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from typing import TypedDict

from pydantic import BaseModel


def create_typed_dict_from_model[T: BaseModel](model: type[T]) -> TypedDict:
    fields = {name: field.annotation for name, field in model.model_fields.items()}
    return TypedDict(f"{model.__name__}Dict", fields)
