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

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class Legislation(BaseModel):
    id: str
    subject_matter: str
    name: str
    s3_key: Optional[str] = Field(None, alias="s3Key")
    #  Note: In the future we might want to support things like dates and jurisdiction levels (Federal, State, etc.)

    model_config = ConfigDict(
        populate_by_name=True,  # allow both 's3_key' and 's3Key' on input, makes testing easier
        extra="forbid",
        validate_assignment=True,
    )
