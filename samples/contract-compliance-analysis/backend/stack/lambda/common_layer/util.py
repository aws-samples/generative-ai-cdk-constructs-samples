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

import re
from collections import defaultdict
from typing import List, Dict, Any

def extract_items_from_tagged_list(text: str, tag_name: str) -> List[str]:
    # Updated regex to handle tags with or without attributes
    # Matches: <tag>, <tag attr="value">, <tag attr1="val1" attr2="val2">, etc.
    opening_tag_pattern = f"<{tag_name}(?:\\s[^>]*)?>"  # <tag> or <tag attr="value">
    closing_tag = f"</{tag_name}>"

    # Use regex to find opening tags (with or without attributes) and their content
    regex = f"{opening_tag_pattern}(.*?){closing_tag}"

    items: List[str] = []
    for match in re.finditer(regex, text, re.DOTALL):
        finding = match.group(1).strip()

        # Find innermost nested opening tag, if any
        # To capture cases like where the model return something like:
        # alkjshdksajhdsakjd <tag> kjsdafkdjhf <tag> dsfkjsdfakjds </tag> dskjfhaksdjhfkdsjf

        # Find innermost nested opening tag, if any (now handling attributes)
        innermost_tag_pattern = f"<{tag_name}(?:\\s[^>]*)?>"
        innermost_match = None
        for match_obj in re.finditer(innermost_tag_pattern, finding):
            innermost_match = match_obj

        if innermost_match:
            finding = finding[innermost_match.end():].strip()

        if finding:
            items.append(finding)

    return items


def extract_first_item_from_tagged_list(text: str, tag_name: str) -> str:
    items = extract_items_from_tagged_list(text, tag_name)

    return items[0] if len(items) else ""


def extract_last_item_from_tagged_list(text: str, tag_name: str) -> str:
    items = extract_items_from_tagged_list(text, tag_name)

    return items[-1] if len(items) > 0 else ""


def extract_items_and_attributes_from_tagged_list(a_string: str, tag_name: str, attr_name: str) -> List[Dict[str, str]]:
    regex = f'<{tag_name}\\s*(?: {attr_name}="(.*?)")?\\s*>(.*?)</{tag_name}>'

    items: List[Dict[str, str]] = []
    for match in re.findall(regex, a_string, re.IGNORECASE | re.DOTALL):
        attr_value, tag_value = match
        items.append({tag_name: tag_value.strip(), attr_name: attr_value.strip()})

    return items


def replace_placeholders(prompt_template: str, inputs: Dict[str, Any]) -> str:
    return prompt_template.format_map(defaultdict(str, **inputs))