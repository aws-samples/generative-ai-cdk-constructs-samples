#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import os

import jinja2


def get_prompt_templates() -> jinja2.Environment:
    return jinja2.Environment(  # nosec B701 - template output is not used on a website
        loader=jinja2.FileSystemLoader(
            os.path.join(os.path.dirname(__file__), "prompts"),
        ),
        autoescape=jinja2.select_autoescape(),
    )
