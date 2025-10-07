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
from stack.backend_eks_stack import BackendEKSStack
import os

USAGE_METRIC = 'uksb-1tupboc45'
SOLUTION_NAME = "Bedrock Nova Sonic Solution - EKS"

app = cdk.App()
BackendEKSStack(
    app, 
    "NovaSonicSolutionEKSBackendStack",
    description=f'({USAGE_METRIC})(tag: {SOLUTION_NAME})',
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION")
    )
)

# CDK Nag is temporarily disabled for EKS stack due to false positives
# from AWS-managed internal EKS resources (Lambda functions, IAM roles, etc.)
# These are not security issues but CDK Nag warnings for AWS's own EKS internals
# Re-enable when CDK Nag properly handles EKS internal resources
# cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
