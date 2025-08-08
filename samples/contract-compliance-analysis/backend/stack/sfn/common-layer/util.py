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


def get_prompt_vars_dict(parameters_str):
    parameters_dict = {}
    if parameters_str:
        for param in parameters_str.split('%%'):
            if '=' in param:
                key, value = param.split('=', 1)
                parameters_dict[key] = value

    return parameters_dict


def extract_items_from_tagged_list(text, tag_name):
    regex = f"<{tag_name}>(.*?)</{tag_name}>"

    items = []
    for match in re.finditer(regex, text, re.IGNORECASE | re.DOTALL):
        items.append(match.group(1).strip())

    return items


def extract_first_item_from_tagged_list(text, tag_name):
    items = extract_items_from_tagged_list(text, tag_name)

    return items[0] if len(items) else ""


def extract_items_and_attributes_from_tagged_list(a_string, tag_name, attr_name):
    regex = f'<{tag_name}\\s*(?: {attr_name}="(.*?)")?\\s*>(.*?)</{tag_name}>'

    items = []
    for match in re.findall(regex, a_string, re.IGNORECASE | re.DOTALL):
        attr_value, tag_value = match
        items.append(
            {tag_name: tag_value.strip(), attr_name: attr_value.strip()}
        )

    return items
