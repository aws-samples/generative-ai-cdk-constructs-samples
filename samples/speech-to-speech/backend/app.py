#!/usr/bin/env python3
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

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks
from stack import BackendStack
import os

USAGE_METRIC = 'uksb-1tupboc45'
SOLUTION_NAME = "Bedrock Nova Sonic 2 Solution"

app = cdk.App()
BackendStack(
    app, 
    "NovaSonicSolutionBackendStack",
    description=f'({USAGE_METRIC})(tag: {SOLUTION_NAME})',
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION")
    )
)

cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
