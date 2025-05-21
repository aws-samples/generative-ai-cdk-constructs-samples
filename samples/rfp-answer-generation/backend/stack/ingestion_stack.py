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
    aws_iam as iam,
    aws_lambda as lambda_,
    CfnOutput,
    Duration,
    Stack,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression

from .constants.prompts import SUPPORTING_DOCUMENT_PARSING_PROMPT
from .stack_constructs import (
    BucketConstruct,
    PythonFunctionConstruct,
    ServerAccessLogsBucketConstruct,
)

from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    opensearchserverless as aoss,
    opensearch_vectorindex as os_vectorstore,
)

base_path = os.path.join(os.path.dirname(__file__), "lambdas")
shared_directory = os.path.join(os.path.dirname(__file__), "lambdas", "shared")


class IngestionStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.vector_db = aoss.VectorCollection(self, "VectorStore")

        self.logging_bucket = ServerAccessLogsBucketConstruct(
            self,
            "LoggingBucket",
        )

        self.supporting_doc_bucket = BucketConstruct(
            self,
            "SupportingDocumentsBucket",
            server_access_logs_bucket=self.logging_bucket,
        )

        self.faq_custom_transformation_bucket = BucketConstruct(
            self,
            "FAQCustomTransformationBucket",
            server_access_logs_bucket=self.logging_bucket,
        )

        self.faq_bucket = BucketConstruct(
            self,
            "FAQBucket",
            server_access_logs_bucket=self.logging_bucket,
        )

        CfnOutput(
            self,
            "IngestionBucketFAQ",
            value=self.faq_bucket.bucket_name,
        )

        CfnOutput(
            self,
            "IngestionBucketSupportingDocs",
            value=self.supporting_doc_bucket.bucket_name,
        )

        for file in os.listdir(shared_directory):
            shutil.copyfile(
                f"{shared_directory}/{file}",
                f"{base_path}/custom_chunking_handler_fn/app/{file}",
            )

        ##############################################
        # FAQs
        ##############################################

        self.faq_index = os_vectorstore.VectorIndex(
            self,
            "FAQIndex",
            collection=self.vector_db,
            index_name=f"faq_index",
            vector_field="vector",
            vector_dimensions=1024,
            mappings=[
                os_vectorstore.MetadataManagementFieldProps(
                    mapping_field="answer", data_type="text", filterable=False
                ),
                os_vectorstore.MetadataManagementFieldProps(
                    mapping_field="question", data_type="text", filterable=False
                ),
                os_vectorstore.MetadataManagementFieldProps(
                    mapping_field="topic", data_type="keyword", filterable=True
                ),
                os_vectorstore.MetadataManagementFieldProps(
                    mapping_field="source", data_type="keyword", filterable=True
                ),
                os_vectorstore.MetadataManagementFieldProps(
                    mapping_field="date", data_type="date", filterable=False
                ),
            ],
        )

        self.faq_index.node.add_dependency(self.vector_db)

        self.faq_knowledge_base = bedrock.KnowledgeBase(
            self,
            "FAQKnowledgeBase",
            embeddings_model=bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_1024,
            index_name=self.faq_index.index_name,
            vector_store=self.vector_db,
            vector_index=self.faq_index,
            vector_field=self.faq_index.vector_field,
        )

        self.faq_custom_transformation_function = PythonFunctionConstruct(
            self,
            "FAQCustomTransformationFn",
            entry=os.path.join(
                os.path.dirname(__file__), "lambdas", "custom_chunking_handler_fn"
            ),
            index="app/handler.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            memory_size=1024,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(15),
            environment={
                "LOG_LEVEL": "INFO",
            },
        )

        self.faq_custom_transformation_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
                ],
            )
        )

        self.faq_bucket.grant_read_write(self.faq_custom_transformation_function.role)

        self.faq_custom_transformation_bucket.grant_read_write(
            self.faq_custom_transformation_function.role
        )

        self.faq_custom_transformation_bucket.grant_read_write(
            self.faq_knowledge_base.role
        )

        self.faq_data_source = bedrock.S3DataSource(
            self,
            "FAQDataSource",
            bucket=self.faq_bucket,
            # inclusion_prefixes=[".csv", ".xlsx"],
            knowledge_base=self.faq_knowledge_base,
            data_source_name="faq_data_source",
            chunking_strategy=bedrock.ChunkingStrategy.NONE,
            custom_transformation=bedrock.CustomTransformation.lambda_(
                lambda_function=self.faq_custom_transformation_function,
                s3_bucket_uri=f"s3://{self.faq_custom_transformation_bucket.bucket_name}/",
            ),
        )

        ##############################################
        # Supporting Documents
        ##############################################

        self.doc_index = os_vectorstore.VectorIndex(
            self,
            "SupportingDocumentsIndex",
            collection=self.vector_db,
            index_name=f"doc_index",
            vector_field="vector",
            vector_dimensions=1024,
            mappings=[
                os_vectorstore.MetadataManagementFieldProps(
                    mapping_field="chunk", data_type="text", filterable=False
                ),
                os_vectorstore.MetadataManagementFieldProps(
                    mapping_field="chunk_type", data_type="keyword", filterable=True
                ),
                os_vectorstore.MetadataManagementFieldProps(
                    mapping_field="source", data_type="keyword", filterable=True
                ),
                os_vectorstore.MetadataManagementFieldProps(
                    mapping_field="date", data_type="date", filterable=False
                ),
            ],
        )

        self.doc_index.node.add_dependency(self.vector_db)

        self.supporting_doc_knowledge_base = bedrock.KnowledgeBase(
            self,
            "SupportingDocumentsKnowledgeBase",
            embeddings_model=bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_1024,
            vector_store=self.vector_db,
            vector_index=self.doc_index,
            index_name=self.doc_index.index_name,
            vector_field=self.doc_index.vector_field,
        )

        self.supporting_doc_data_source = bedrock.S3DataSource(
            self,
            "SupportingDocumentsDataSource",
            bucket=self.supporting_doc_bucket,
            inclusion_prefixes=[".pdf"],
            knowledge_base=self.supporting_doc_knowledge_base,
            data_source_name="supporting_docs_data_source",
            chunking_strategy=bedrock.ChunkingStrategy.FIXED_SIZE,
            parsing_strategy=bedrock.ParsingStategy.foundation_model(
                parsing_model=bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V1_0.as_i_model(
                    self
                ),
                parsing_prompt=SUPPORTING_DOCUMENT_PARSING_PROMPT,
            ),
        )

        self.template_options.description='Description: (uksb-1tupboc43) (tag:rfp-answer-generation)'


        NagSuppressions.add_resource_suppressions(
            construct=self.faq_custom_transformation_function.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Custom transformation needs to support non-standardized object naming.",
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack=Stack.of(self),
            path=f"/{Stack.of(self).stack_name}/OpenSearchIndexCRProvider/CustomResourcesFunction",
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="OpenSearch Custom Resource is managed by Generative AI CDK Constructs library.",
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack=Stack.of(self),
            path=f"/{Stack.of(self).stack_name}/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole",
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="CDK CustomResource LogRetention Lambda uses the AWSLambdaBasicExecutionRole AWS Managed Policy. Managed by CDK.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="CDK CustomResource LogRetention Lambda uses the AWSLambdaBasicExecutionRole AWS Managed Policy. Managed by CDK.",
                ),
            ],
            apply_to_children=True,
        )
