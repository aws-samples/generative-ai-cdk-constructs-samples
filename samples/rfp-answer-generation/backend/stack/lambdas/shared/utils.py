#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import boto3
import re

from botocore.config import Config


def get_bedrock_runtime():
    return boto3.client(
        "bedrock-runtime",
        config=Config(
            connect_timeout=900,
            read_timeout=900,
            retries={
                "max_attempts": 30,
                "mode": "adaptive",
            },
        ),
    )


def extract_items_from_tagged_list(text: str, tag_name: str) -> list[str]:
    regex = rf"<{tag_name}[\s0-9]*?>(.*?)</{tag_name}[\s0-9]*?>"

    items = []
    for match in re.finditer(regex, text, re.DOTALL):
        items.append(match.group(1).strip())

    return items


def extract_first_item_from_tagged_list(text: str, tag_name: str) -> str:
    items = extract_items_from_tagged_list(text, tag_name)

    return items[0] if len(items) > 0 else text
