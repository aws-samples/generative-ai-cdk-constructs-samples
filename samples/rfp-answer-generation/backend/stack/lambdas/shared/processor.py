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

import numpy as np
import pandas as pd

from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypedDict

from .utils import extract_items_from_tagged_list, get_bedrock_runtime

PROMPT_TEMPLATE = """
You have received a previously answered Request For Proposal (RFP) document. Your task is to extract, ipsis literis, ALL of the questions and answers from every sheet in the document. Provide your answer enclosed by <rfp></rfp> tags.

<document>
{input_sheet}
</document>

Follow these steps:

1. Examine the document carefully.

2. If any of the cells of the spreadsheet specifies a date when the RFP was answered, provide the date under <date></date> tags.

3. If the document contains instructions from the requester, do not extract them.

4. Identify each group of questions in the RFP and the topic name for the group. The document format can very, and the topic can be specified in a column beside the question or in a single cell before a group of questions. Identify the topic name with <topic_name></topic_name> tags.

5. Identify each question and its answer.

6. Under the <topic></topic> tags, enclose the question in <question></question> tags.

7. Under the <topic></topic> tags, enclose the answer in <answer></answer> tags.

Output Example:
<rfp>
<topic>
<topic_name>Company Information</topic_name>
<question>Company Name</question>
<answer>Oktank LDTA</answer>
</topic>
</rfp>
"""


class RFPChunk(TypedDict):
    question: str
    answer: str
    topic: str
    date: str


class KnowledgeBaseChunk(TypedDict):
    contentType: str
    contentMetadata: RFPChunk
    contentBody: str


class BedrockKBProcessor:
    def __init__(
        self,
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        separator=",",
    ):
        self.model_id: str = model_id
        self.separator: str = separator

        self.bedrock_client = get_bedrock_runtime()

    def process_file(self, filename: str, file_date: str) -> list[RFPChunk]:
        rfp_chunks: list[RFPChunk] = []
        data: list[str] = self.__extract_data_concurrent(filename)

        for chunk in data:
            topics: list[str] = extract_items_from_tagged_list(chunk, "topic")

            for topic in topics:
                topic_name: list[str] = extract_items_from_tagged_list(
                    topic, "topic_name"
                )
                questions: list[str] = extract_items_from_tagged_list(topic, "question")
                answers: list[str] = extract_items_from_tagged_list(topic, "answer")

                extracted_qa = [
                    {
                        "question": q,
                        "answer": a,
                        "topic": topic_name[0],
                        "date": file_date,
                    }
                    for q, a in zip(questions, answers)
                    if a
                ]

                print(f"Extracted: {len(extracted_qa)} QA pairs.")

                rfp_chunks += extracted_qa

        return rfp_chunks

    def as_knowledge_base_chunk(
        self, chunks: list[RFPChunk]
    ) -> list[KnowledgeBaseChunk]:
        return [
            {
                "contentType": "TEXT",
                "contentMetadata": chunk,
                "contentBody": f"Q: {chunk['question']}\nA: {chunk['answer']}",
            }
            for chunk in chunks
        ]

    def __extract_data(self, section: pd.DataFrame) -> list[str]:
        input_sheet = section.to_markdown(index=False)

        message = {
            "role": "user",
            "content": [
                {"text": PROMPT_TEMPLATE.replace("{input_sheet}", input_sheet)}
            ],
        }

        response = self.bedrock_client.converse(
            modelId=self.model_id,
            messages=[message],
            inferenceConfig={
                "temperature": 0.0,
                "topP": 0.2,
            },
            additionalModelRequestFields={
                "top_k": 200,
            },
        )

        return response["output"]["message"]["content"][0]["text"]

    def __extract_data_concurrent(self, filename):
        sections = self.__load_file_in_sections(filename)
        data: list[str] = []

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(
                    self.__extract_data,
                    section,
                )
                for section in sections
            ]
            return [r.result() for r in as_completed(futures)]

    def __load_file_in_sections(self, filename: str) -> list[pd.DataFrame]:
        print(filename)
        extension: str = filename.split(".")[-1].upper()
        print(f"File extension: {extension}")
        sections: list[pd.DataFrame] = []

        if extension == "XLSX":
            print("Loaded XLSX")
            sheets_dict = pd.read_excel(
                filename, sheet_name=None, header=None, engine="openpyxl"
            )

            for _, sheet in sheets_dict.items():
                sections += np.split(sheet, sheet[sheet.isnull().all(1)].index)

        else:
            print("Loaded CSV")
            sheet = pd.read_csv(filename, header=None, sep=self.separator)
            sections += np.split(sheet, sheet[sheet.isnull().all(1)].index)

        print(f"Loaded {len(sections)} sheets")

        return sections
