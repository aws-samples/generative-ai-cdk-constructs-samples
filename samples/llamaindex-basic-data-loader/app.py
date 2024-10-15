#!/usr/bin/env python3
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

import os

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks, NagSuppressions

from bin.llamaindex_basic_data_loader_stack import LlamaindexBasicDataLoaderStack


app = cdk.App()
llamaindex_basic_data_loader_stack = LlamaindexBasicDataLoaderStack(app, "LlamaindexBasicDataLoaderStack",
)
NagSuppressions.add_stack_suppressions(llamaindex_basic_data_loader_stack, [
    {"id": "AwsSolutions-IAM5", "reason": "Wildcard allowed for S3 access"},
])
cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
