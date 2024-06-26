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

import logging
import tempfile
import re
import os
from difflib import Differ

import boto3

from langchain.text_splitter import TokenTextSplitter

from llm import invoke_llm
from util import get_prompt_vars_dict


logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

clauses_table_name = os.environ["CLAUSES_TABLE_NAME"]

PROMPT_VARS = os.environ.get('PROMPT_VARS', "")

s3_client = boto3.client("s3")
dynamodb_client = boto3.resource("dynamodb")
clauses_table = dynamodb_client.Table(clauses_table_name)
bedrock_client = boto3.client('bedrock-runtime')

CLAUSE_SEPARATOR = "|||||"

PROMPT_TEMPLATE = f"""Your task is to read through an excerpt of a contract and split it into individual clauses by inserting a
separator indicator between each clause.

A clause is a distinct section or provision within a contract that deals with a particular subject
matter or obligation.

Here are the steps to complete this task:

1. Read through the contract excerpt provided:

<contract_excerpt>
{{CONTRACT_EXCERPT}}
</contract_excerpt>

2. Identify the individual clauses within the contract excerpt. In some cases, clauses are separated by 
punctuation like periods, semicolons, or line breaks. In other cases, clauses are delineated by 
section headings or numbered/lettered paragraphs. Some clauses can contain sub-items or bullet 
points. The sub-items and bullet points must not be separated from their parent clause.

3. Insert a separator indicator (line break + "{CLAUSE_SEPARATOR}" + line break) between each identified
clause. Do not omit or modify any part of the original contract excerpt, apart from inserting the 
separator indicators.

4. Here is an example of how the output should look like with separator indicators inserted:

<example>
1. This is the first clause of the contract.
{CLAUSE_SEPARATOR}
Clause 2. This is the second clause; it covers a different subject matter. 
{CLAUSE_SEPARATOR}
3. This is the third clause. It contains some sub-items:
a. First sub-item;
b. Second sub-item;
c. Last sub-item.
{CLAUSE_SEPARATOR}
Clause 4. Subject matter of the fourth clause

4.1. This is a clause about the subject matter of the fourth clause.
{CLAUSE_SEPARATOR}
4.2. This is another clause about the same subject matter.
{CLAUSE_SEPARATOR}
Clause 5. Last subject matter

This is the last clause of the contract.
</example>

5. Once you have inserted the separator indicators between all clauses, output the resulting 
contract excerpt, with no introductory statements and no XML tags."""


class MalformedRequest(ValueError):
    pass


def split_chunks(text, chunk_size_in_tokens=3500):
    return TokenTextSplitter(chunk_size=chunk_size_in_tokens).split_text(text)


def separate_clauses(contract_excerpt):
    prompt_vars_dict = get_prompt_vars_dict(PROMPT_VARS)
    llm_response, model_usage, stop_reason = invoke_llm(
        prompt=PROMPT_TEMPLATE.format(CONTRACT_EXCERPT=contract_excerpt),
        model_id=prompt_vars_dict.get("claude_model_id", ''),
        temperature=0.0,
        max_new_tokens=4096,
        verbose=True
    )
    return llm_response


def parse_event(event):
    if "document_s3_path" in event and "ExecutionName" in event:
        document_s3_path = event["document_s3_path"]
        execution_name = event["ExecutionName"]
    else:
        raise MalformedRequest("Unknown event structure")

    logger.info(f"Got document_s3_path and execution_name from event: {document_s3_path} {execution_name}")

    match = re.match("s3://(.+?)/(.+)", document_s3_path)

    if match:
        bucket = match.group(1)
        key = match.group(2)

        return bucket, key, execution_name
    else:
        raise MalformedRequest(f"Invalid S3 URI: {document_s3_path}")


def handler(event, context):
    """Lambda to preprocess a contract document
    """
    logger.info("Received event %s", event)

    bucket, key, execution_name = parse_event(event)

    with tempfile.NamedTemporaryFile() as doc_temp_file:
        s3_client.download_fileobj(bucket, key, doc_temp_file)
        doc_temp_file.seek(0)
        logger.info(f"Downloaded s3://{bucket}/{key}")

        # If Word document, parse using langchain (unstructured)
        # If PDF, parse using langchain (unstructured)
        # If plain text, just reads the file
        # if key.lower().endswith(".docx"):
        #     loader = UnstructuredWordDocumentLoader(doc_temp_file.name)
        #     doc_text = loader.load()
        # elif key.lower().endswith(".pdf"):
        #     loader = UnstructuredPDFLoader(doc_temp_file.name)
        #     doc_text = loader.load()
        # else:
        contract = doc_temp_file.read().decode("utf-8")

        # Split text in chunks of less than 4000 tokens
        chunks = split_chunks(contract)
        # Separate each chunk, including separators between clauses
        separated_contract = "".join([
            separate_clauses(chunk) for chunk in chunks
        ])
        # Get the diff between the original contract and the separated contract
        diffs = list(Differ().compare(
            contract.splitlines(keepends=True),
            separated_contract.splitlines(keepends=True)
        ))
        # Merge the contracts, accepting only the inclusion of separators
        merged_contract = "".join([
            diff[2:] if diff.startswith("  ") or diff.startswith("- ") or diff.startswith(f"+ {CLAUSE_SEPARATOR}\n") else ""
            for diff in diffs
        ])
        # Get each individual clause and insert into table
        clauses = list(filter(None, [clause.strip() for clause in merged_contract.split(CLAUSE_SEPARATOR)]))
        for i, clause in enumerate(clauses):
            clauses_table.put_item(Item={
                'job_id': execution_name,
                'clause_number': i,
                'text': clause.strip(),
            })

    return {
        "JobId": execution_name,
        "ClauseNumbers": list(range(len(clauses))),
    }
