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

from langchain_aws import ChatBedrock
from langchain_aws.retrievers import AmazonKnowledgeBasesRetriever
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain.prompts.prompt import PromptTemplate
from operator import itemgetter
from str2bool import str2bool

from .definitions import QUESTION_EXTRACTION_PROMPT
from .utils import get_bedrock_runtime, extract_items_from_tagged_list

AWS_REGION = os.getenv("AWS_REGION", default="us-east-1")

BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
DOC_KNOWLEDGE_BASE_ID = os.getenv("DOC_KNOWLEDGE_BASE_ID")
FAQ_KNOWLEDGE_BASE_ID = os.getenv("FAQ_KNOWLEDGE_BASE_ID")

USE_QUESTION_BREAKDOWN = str2bool(os.getenv("USE_QUESTION_BREAKDOWN", default="True"))

model = ChatBedrock(
    model_id=BEDROCK_MODEL_ID,
    model_kwargs={"temperature": 0.0, "stop_sequences": ["\n\nHuman:"]},
    client=get_bedrock_runtime(),
    verbose=True,
)


class ContextRetriever:
    def __init__(self):
        self.bedrock_docs_kb_retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=DOC_KNOWLEDGE_BASE_ID,
            retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 4}},
        )

        self.bedrock_faq_kb_retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=FAQ_KNOWLEDGE_BASE_ID,
            retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 4}},
        )

    def unique_documents(self, documents_for_subqueries: list):
        docs = {}

        for subquery in documents_for_subqueries:
            for document in subquery:
                data = document.metadata["source_metadata"]
                document.metadata = document.metadata["source_metadata"]
                if data["x-amz-bedrock-kb-chunk-id"] not in docs:
                    docs[data["x-amz-bedrock-kb-chunk-id"]] = document

        return list(docs.values())

    def parse_questions(self, llm_output):
        return extract_items_from_tagged_list(llm_output.content, "subquestion")

    def retrieve_documents_chain(self, param):
        extract_subquestions_chain = RunnablePassthrough()

        faq_retriever_chain = RunnableLambda(
            lambda query: self.unique_documents(
                [self.bedrock_faq_kb_retriever.invoke(q) for q in query]
            )
        )

        docs_retriever_chain = RunnableLambda(
            lambda query: self.unique_documents(
                [self.bedrock_docs_kb_retriever.invoke(q) for q in query]
            )
        )

        if USE_QUESTION_BREAKDOWN:
            prompt = PromptTemplate.from_template(QUESTION_EXTRACTION_PROMPT)

            extract_subquestions_chain = RunnablePassthrough.assign(
                sub_questions=itemgetter("question")
                | prompt
                | model
                | self.parse_questions
            ) | RunnablePassthrough.assign(
                question=(lambda x: [x["question"]] + x["sub_questions"])
            )

        return (
            extract_subquestions_chain
            | itemgetter("question")
            | RunnableParallel(faq=faq_retriever_chain, docs=docs_retriever_chain)
        )
