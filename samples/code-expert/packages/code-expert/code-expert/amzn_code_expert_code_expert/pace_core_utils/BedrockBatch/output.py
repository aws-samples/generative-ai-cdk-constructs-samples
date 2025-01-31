#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import json
from io import BytesIO
from typing import Iterator, Dict, Any, TypedDict, NotRequired

from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch import BedrockBatchItem, BedrockBatchError
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.ConverseToBatch import ModelAdapter, ModelResponse


class BedrockBatchOutputRecord(TypedDict):
    record_id: str
    model_input: NotRequired[Dict[str, Any]]
    model_output: NotRequired[ModelResponse]
    error: NotRequired[BedrockBatchError]


class BedrockBatchOutputProcessor:
    def __init__(self, s3_client, model_id: str):
        self.s3_client = s3_client
        self.model_adapter = ModelAdapter.get_adapter(model_id)

    def process_output(self, bucket: str, key: str) -> Iterator[BedrockBatchOutputRecord]:
        """
        Process the output manifest file and yield each record's data.

        Args:
            bucket (str): S3 bucket name
            key (str): S3 object key

        Yields:
            BedrockBatchOutputRecord: A Pydantic model containing the record ID and
            either the parsed model output or an error.
        """
        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        manifest_content = response["Body"].read()

        yield from self.process_output_manifest(manifest_content)

    def process_output_manifest(self, manifest_content: bytes) -> Iterator[BedrockBatchOutputRecord]:
        for line in BytesIO(manifest_content).readlines():
            line = line.decode("utf-8").strip()
            if line:
                record = json.loads(line)
                yield self.process_record(record)

    def process_record(self, record: Dict[str, Any]) -> BedrockBatchOutputRecord:
        """
        Process a single record from the manifest file.

        Args:
            record (Dict[str, Any]): A dictionary representing a single record from the manifest

        Returns:
            BedrockBatchOutputRecord: A Pydantic model containing the record ID and
            either the parsed model output or an error.
        """
        try:
            batch_item = BedrockBatchItem(**record)

            if batch_item.get("error"):
                return BedrockBatchOutputRecord(
                    record_id=batch_item.get("recordId"),
                    model_input=batch_item.get("modelInput"),
                    error=batch_item.get("error"),
                )
            elif batch_item.get("modelOutput"):
                parsed_output = self.model_adapter.parse_model_response(batch_item.get("modelOutput"))
                return BedrockBatchOutputRecord(
                    record_id=batch_item.get("recordId"),
                    model_input=batch_item.get("modelInput"),
                    model_output=parsed_output,
                )
            else:
                error = BedrockBatchError(errorMessage="No model output or error found", errorCode=500)
                return BedrockBatchOutputRecord(
                    record_id=batch_item.get("recordId"), model_input=batch_item.get("modelInput"), error=error
                )
        except Exception as e:
            error = BedrockBatchError(errorMessage=f"Error processing record: {str(e)}", errorCode=500)
            return BedrockBatchOutputRecord(record_id=record.get("recordId", "unknown"), error=error)
