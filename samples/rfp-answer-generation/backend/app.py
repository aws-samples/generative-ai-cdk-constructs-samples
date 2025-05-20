#!/usr/bin/env python3

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

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from stack import IngestionStack, InferenceStack

USAGE_METRIC = 'uksb-1tupboc45'
VERSION = '0.0.1'
SOLUTION_NAME = "rfp-answer-generation"

app = cdk.App()

ingestion_stack = IngestionStack(
    app, 
    "RFPAnswers-IngestionStack",
    description=f'({USAGE_METRIC})(tag:{SOLUTION_NAME})')

inference_stack = InferenceStack(
    app,
    "RFPAnswers-InferenceStack",
    faq_knowledge_base_id=ingestion_stack.faq_knowledge_base.knowledge_base_id,
    docs_knowledge_base_id=ingestion_stack.supporting_doc_knowledge_base.knowledge_base_id,
)

cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
