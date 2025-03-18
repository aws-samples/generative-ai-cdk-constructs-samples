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


#!/usr/bin/env python3
import os
import aws_cdk as cdk
import yaml
from yaml.loader import SafeLoader
from cdk_nag import AwsSolutionsChecks

from infra.capsule_stack import CapsuleStack

with open(os.path.join(os.path.dirname(__file__), "config.yml"), encoding="utf-8") as f:
    stack_config = yaml.load(f, Loader=SafeLoader)

app = cdk.App()
env = cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION"))

CapsuleStack(scope=app, construct_id=stack_config["stack_name"], config=stack_config, env=env)
cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
