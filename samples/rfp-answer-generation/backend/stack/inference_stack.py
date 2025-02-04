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

import os
import shutil

from aws_cdk import (
    aws_dynamodb as dynamodb,
    Stack,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


from .stack_constructs import (
    StepFunctionsConstruct,
    ServerAccessLogsBucketConstruct,
    BucketConstruct,
    TableConstruct,
    APIConstruct,
)

base_path = os.path.join(os.path.dirname(__file__), "lambdas")
shared_directory = os.path.join(os.path.dirname(__file__), "lambdas", "shared")


class InferenceStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        faq_knowledge_base_id: str,
        docs_knowledge_base_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.inference_logging_bucket = ServerAccessLogsBucketConstruct(
            self,
            "InferenceLoggingBucket",
        )

        self.inference_bucket = BucketConstruct(
            self,
            "InferenceBucket",
            server_access_logs_bucket=self.inference_logging_bucket,
        )

        # Question Set Processiong Job DynamoDB table
        self.jobs_table = TableConstruct(
            self,
            "JobsTable",
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
        )

        # Questions DynamoDB table
        self.questionnaire_table = TableConstruct(
            self,
            "QuestionnaireTable",
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="question_number", type=dynamodb.AttributeType.NUMBER
            ),
        )

        for file in os.listdir(shared_directory):
            shutil.copyfile(
                f"{shared_directory}/{file}",
                f"{base_path}/preprocess_fn/app/{file}",
            )

            shutil.copyfile(
                f"{shared_directory}/{file}",
                f"{base_path}/answer_question_fn/app/{file}",
            )

        self.sfn = StepFunctionsConstruct(
            self,
            "StepFunctionsConstruct",
            self.inference_bucket,
            self.jobs_table,
            self.questionnaire_table,
            faq_knowledge_base_id,
            docs_knowledge_base_id,
        )

        self.api = APIConstruct(
            self,
            "APIConstruct",
            self.region,
            self.inference_bucket,
            self.questionnaire_table,
            self.jobs_table,
            self.sfn.state_machine,
        )

        self.template_options.description='Description: (uksb-1tupboc43) (tag: rfp answer generation sample)'


        NagSuppressions.add_resource_suppressions_by_path(
            stack=self,
            path=f"/{Stack.of(self).stack_name}/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/Role/Resource",
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="CDK Bucket Notifications Handler uses the AWSLambdaBasicExecutionRole AWS Managed Policy. Managed by CDK.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="CDK Bucket Notifications Handler needs to support non-standardized object naming.",
                ),
            ],
            apply_to_children=True,
        )
