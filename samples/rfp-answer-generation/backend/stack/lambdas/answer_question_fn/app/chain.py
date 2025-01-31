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

import logging
import os

from abc import ABC
from langchain_aws import ChatBedrock
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnablePassthrough
from langchain.prompts.prompt import PromptTemplate
from langchain.schema import format_document
from typing import Dict, Any, List

from .definitions import *
from .utils import get_bedrock_runtime, extract_first_item_from_tagged_list

BEDROCK_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

logger = logging.getLogger("QAChain")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


class PromptLoggingHandler(BaseCallbackHandler, ABC):
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> Any:
        formatted_prompts = "\n".join(prompts)
        logger.debug(f"Prompt:\n{formatted_prompts}")


model = ChatBedrock(
    model_id=BEDROCK_MODEL_ID,
    model_kwargs={
        "max_tokens": 10000,
        "temperature": 0.2,
        "top_p": 0.5,
        "top_k": 200,
        "stop_sequences": ["\n\nHuman:"],
    },
    client=get_bedrock_runtime(),
    callbacks=[PromptLoggingHandler()],
    verbose=True,
)


def faq_context_prompt_partial() -> PromptTemplate:
    return PromptTemplate.from_template(
        template="""<past-rfp-question>
    <question>{question}</question>
    <answer>{answer}</answer>
</past-rfp-question>"""
    )


def doc_context_prompt_partial() -> PromptTemplate:
    return PromptTemplate.from_template(
        template="""<documentation-fragment>
    <content>{page_content}</content>
</documentation-fragment>"""
    )


def format_faq_docs(faq_docs: list[str]) -> list[str]:
    return [
        format_document(document, faq_context_prompt_partial()) for document in faq_docs
    ]


def format_supporting_docs(supporting_docs: list[str]) -> list[str]:
    return [
        format_document(document, doc_context_prompt_partial())
        for document in supporting_docs
    ]


def format_context_for_prompt(context: dict):
    faq_xml_elements = format_faq_docs(context["faq"])
    faq_xml_docs = format_supporting_docs(context["docs"])

    return "\n".join(faq_xml_elements + faq_xml_docs)


class QuestionAnsweringChainFacade:
    def __init__(self, context_retriever):
        self.context_retriever = context_retriever
        self.qa_chain = None

    def _get_chain(self):
        if self.qa_chain is None:
            logger.info("Building QA Chain ...")

            retrieval_chain = RunnablePassthrough.assign(
                context=self.context_retriever.retrieve_documents_chain
            )

            prompt = PromptTemplate.from_template(QA_PROMPT_TEMPLATE)
            generation_chain = retrieval_chain.assign(
                llm_output=(
                    RunnablePassthrough.assign(
                        context=(lambda x: format_context_for_prompt(x["context"]))
                    )
                    | prompt  # Prompt is logged by PromptLoggingHandler
                    | model
                )
            ) | RunnablePassthrough.assign(
                answer=(
                    lambda x: extract_first_item_from_tagged_list(
                        x["llm_output"].content, "answer"
                    )
                )
            )

            self.qa_chain = generation_chain

        return self.qa_chain

    def answer_question(self, question: str):
        qa_chain = self._get_chain()

        return qa_chain.invoke(
            {
                "question": question,
                "other_definitions": ADDITIONAL_DEFINITIONS,
                "company_name": COMPANY_NAME,
                "language": LANGUAGE,
            }
        )
