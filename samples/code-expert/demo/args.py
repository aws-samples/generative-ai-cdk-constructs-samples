#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import json
import sys


class Args:
    stepfunctions_arn = None
    s3_bucket = None
    rule_text_by_id = None

    def __init__(self):
        if len(sys.argv) < 4:
            raise ValueError(
                ('Invalid arguments. Expecting three arguments: ARN of the StepFunctions state machine, S3 '
                 'bucket name, and filepath of the rules JSON file.'))

        Args.stepfunctions_arn = sys.argv[1]
        Args.s3_bucket = sys.argv[2]
        Args.rule_text_by_id = {}

        with open(sys.argv[3], 'r') as json_file:
            for rule in json.loads(json_file.read())['rules']:
                Args.rule_text_by_id[str(rule['rule'])] = rule['ruleDesc']
