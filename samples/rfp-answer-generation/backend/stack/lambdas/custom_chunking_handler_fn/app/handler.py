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

import boto3
import json
import logging
import os
import tempfile

from typing import TypedDict
from urllib.parse import urlparse

from .processor import BedrockKBProcessor

AWS_REGION = os.environ.get("AWS_REGION")
RFP_DATE_METADATA_ATTRIBUTE = os.environ.get(
    "RFP_DATE_METADATA_ATTRIBUTE", "lastModified"
)
MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")

console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
)
logger = logging.getLogger("answer-question")
logger.addHandler(console_handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

s3 = boto3.client("s3")


class KBIngestionEventInputFileFileLocation(TypedDict):
    type: str
    s3_location: dict


class KBIngestionEventInputFiles(TypedDict):
    originalFileLocation: KBIngestionEventInputFileFileLocation
    fileMetadata: dict
    contentBatches: list[dict]


class KBIngestionEvent(TypedDict):
    version: str
    knowledgeBaseId: dict
    dataSourceId: str
    ingestionJobId: str
    bucketName: str
    priorTask: str
    inputFiles: list[dict]


def handler(event: KBIngestionEvent, context):
    logger.debug(f"Event: {event}")

    input_files = event.get("inputFiles")
    output_bucket = event.get("bucketName")
    kb_id = event.get("knowledgeBaseId")
    ds_id = event.get("dataSourceId")
    ingestion_job_id = event.get("ingestionJobId")

    if not input_files:
        raise ValueError("Missing required input parameters")

    output_files = []
    file_processor = BedrockKBProcessor(model_id=MODEL_ID)

    for input_file in input_files:
        file_metadata: dict = input_file.get("fileMetadata", {})
        original_file_location: KBIngestionEventInputFileFileLocation = input_file.get(
            "originalFileLocation", {}
        )

        s3_uri: str = original_file_location.get("s3_location", {}).get("uri")

        if not s3_uri:
            raise ValueError("Missing uri in content batch")

        input_bucket: str = urlparse(s3_uri).netloc
        input_key: str = urlparse(s3_uri).path.lstrip("/")

        with tempfile.NamedTemporaryFile(
            suffix=f".{input_key.split(".")[-1]}"
        ) as doc_temp_file:
            s3.download_fileobj(input_bucket, input_key, doc_temp_file)
            doc_temp_file.seek(0)
            logger.info(f"Downloaded s3://{input_bucket}/{input_key}")

            file_date = file_metadata.get(RFP_DATE_METADATA_ATTRIBUTE, None)
            content = file_processor.process_file(doc_temp_file.name, file_date)

        kb_content = file_processor.as_knowledge_base_chunk(content)

        output_key = f"Output/{kb_id}/{ds_id}{ingestion_job_id}/{input_key}.json"

        s3.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=json.dumps({"fileContents": kb_content}),
        )

        output_file = {
            "originalFileLocation": original_file_location,
            "fileMetadata": file_metadata,
            "contentBatches": [{"key": output_key}],
        }
        output_files.append(output_file)

    result = {"outputFiles": output_files}
    return result
