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

import os
import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks, NagSuppressions
from stack import BackendStack
from check_legislation import CheckLegislationStack

USAGE_METRIC = 'uksb-1tupboc45'
VERSION = '0.0.1'
SOLUTION_NAME = "contract-compliance-analysis"

app = cdk.App()

stack_name = os.environ.get('STACK_NAME', "MainBackendStack")

main_backend_stack = BackendStack(
    app, stack_name,
    description=f'({USAGE_METRIC})(tag:{SOLUTION_NAME})'
)

check_legislation_stack = CheckLegislationStack(
    app,
    "CheckLegislationStack",
    api_gw=main_backend_stack.apigw,
    clauses_table=main_backend_stack.clauses_table,
    jobs_table=main_backend_stack.jobs_table,
    event_bus=main_backend_stack.event_bus,
    main_stack_name=stack_name,
)

# Suppress cdk_nag warning for Custom Resource Lambda in CheckLegislationStack
NagSuppressions.add_stack_suppressions(
    check_legislation_stack,
    [
        {
            "id": "AwsSolutions-IAM4",
            "reason": "Custom Resource Lambda uses AWS managed policy for basic execution",
            "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
        }
    ]
)

cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
