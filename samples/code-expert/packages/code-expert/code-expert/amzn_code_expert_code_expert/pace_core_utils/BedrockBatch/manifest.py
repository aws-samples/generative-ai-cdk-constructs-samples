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
import random
import string
import tempfile
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Sequence, Union, Mapping, Any, Iterator, IO

from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch import BedrockBatchItem
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.ConverseToBatch import ModelAdapter

MIN_BATCH_SIZE = 100

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime.type_defs import (
        MessageTypeDef,
        MessageOutputTypeDef,
        SystemContentBlockTypeDef,
        InferenceConfigurationTypeDef,
        ToolConfigurationTypeDef,
        GuardrailConfigurationTypeDef,
        PromptVariableValuesTypeDef,
        PerformanceConfigurationTypeDef,
    )
    from mypy_boto3_s3 import S3Client

MAX_MANIFEST_BYTES = 1 * 1000 * 1000 * 1000  # 1GiB to provide a buffer
PAD_PREFIX = "DISCARD"


@dataclass
class ManifestState:
    manifest_file: IO[bytes]
    manifest_bytes: int = 0
    manifest_records: int = 0
    temp_records: list = field(default_factory=list)
    current_record: Optional[str] = None
    should_write: bool = False

    def should_write_manifest(self) -> bool:
        return self.should_write or self.manifest_bytes >= MAX_MANIFEST_BYTES

    def has_records(self) -> bool:
        return self.manifest_records > 0

    def close(self):
        if self.manifest_file:
            self.manifest_file.close()


class BedrockBatchInputProcessor:
    def __init__(self, s3: "S3Client", model_id: str, bucket: str, prefix: str):
        self.s3 = s3
        self.bucket = bucket
        self.prefix = prefix
        self.model_id = model_id
        self.queue: list[BedrockBatchItem] = []
        self.model_adapter: ModelAdapter = ModelAdapter.get_adapter(model_id)

    def add_record(
        self,
        record_id: str,
        modelId: str,
        messages: Sequence[Union["MessageTypeDef", "MessageOutputTypeDef"]] = None,
        system: Sequence["SystemContentBlockTypeDef"] = None,
        inferenceConfig: "InferenceConfigurationTypeDef" = None,
        toolConfig: "ToolConfigurationTypeDef" = None,
        guardrailConfig: "GuardrailConfigurationTypeDef" = None,
        additionalModelRequestFields: Mapping[str, Any] = None,
        promptVariables: Mapping[str, "PromptVariableValuesTypeDef"] = None,
        additionalModelResponseFieldPaths: Sequence[str] = None,
        requestMetadata: Mapping[str, str] = None,
        performanceConfig: "PerformanceConfigurationTypeDef" = None,
    ):
        model_input = self.model_adapter.to_invoke_model_input(
            modelId=modelId,
            messages=messages,
            system=system,
            inferenceConfig=inferenceConfig,
            toolConfig=toolConfig,
            guardrailConfig=guardrailConfig,
            additionalModelRequestFields=additionalModelRequestFields,
            promptVariables=promptVariables,
            additionalModelResponseFieldPaths=additionalModelResponseFieldPaths,
            requestMetadata=requestMetadata,
            performanceConfig=performanceConfig,
        )
        self.queue.append(BedrockBatchItem(recordId=record_id, modelInput=model_input))

    @staticmethod
    def _initialize_manifest_state() -> ManifestState:
        #  amazonq-ignore-next-line
        return ManifestState(manifest_file=tempfile.TemporaryFile("w+b"))

    def _process_record(self, state: ManifestState) -> ManifestState:
        record = self.queue.pop(0)
        state.temp_records.append(record)

        json_record = json.dumps({k: v for k, v in record.items() if k != "modelOutput"}) + "\n"
        record_size = len(json_record.encode("utf-8"))

        # Check if adding this record would exceed the size limit
        if state.manifest_bytes + record_size >= MAX_MANIFEST_BYTES:
            # Save the record for the next manifest
            state.current_record = json_record
            state.should_write = True
            return state

        return self._add_record_to_manifest(state, json_record)

    def _create_new_manifest_state(self, current_record: str) -> ManifestState:
        new_state = self._initialize_manifest_state()
        return self._add_record_to_manifest(new_state, current_record)

    def _write_manifest(self, state: ManifestState) -> str:
        if state.manifest_records == 0:
            raise ValueError("Manifest is too big, but has 0 records")

        if state.manifest_records < MIN_BATCH_SIZE:
            state.manifest_file.write(self._pad_manifest(MIN_BATCH_SIZE - state.manifest_records).encode("utf-8"))

        key = self._put_manifest(state.manifest_file)
        state.manifest_file.close()
        return key

    @staticmethod
    def _add_record_to_manifest(state: ManifestState, record: str) -> ManifestState:
        """
        Adds a record to the manifest state and updates the tracking metrics.
        Assumes the record has already been size-checked and will fit.

        Args:
            state: Current manifest state
            record: JSON record to add

        Returns:
            Updated manifest state
        """
        if not record:
            raise ValueError("Record cannot be empty")
        state.manifest_file.write(record.encode("utf-8"))
        state.manifest_bytes += len(record.encode("utf-8"))
        state.manifest_records += 1
        return state

    def prepare_manifests(self) -> Iterator[str]:
        """
        Put the records from the queue into JSONL manifest files in S3 and return the list of keys.

        Each manifest file can be up to 1GB in size with a minimum of 100 records. If there are fewer than 100 records
        for a manifest, it will be padded with small requests.

        Returns:
            Iterator[str]: yield keys for the manifest files in S3.
        """
        if not self.queue:
            raise ValueError("No records to process")

        manifest_state = self._initialize_manifest_state()

        try:
            while self.queue:
                manifest_state = self._process_record(manifest_state)

                # If we've hit the size limit, write the current manifest
                if manifest_state.should_write_manifest():
                    if manifest_state.has_records():
                        yield self._write_manifest(manifest_state)
                        # Start new manifest with the saved record
                        manifest_state = self._create_new_manifest_state(manifest_state.current_record)
                    else:
                        # This shouldn't happen, but if it does, we need to handle it
                        raise ValueError("Manifest is too big, but has 0 records")

            # Handle the final manifest
            if manifest_state.has_records():
                yield self._write_manifest(manifest_state)
        except Exception as e:
            self.queue.extend(manifest_state.temp_records)
            raise e
        finally:
            manifest_state.close()

    def _put_manifest(self, manifest_file: IO) -> str:
        """
        Put the manifest file in S3 and return the key.

        Args:
            manifest_file: File like object

        Returns:
            str: S3 key
        """
        manifest_name = uuid.uuid4().hex + ".jsonl"
        manifest_key = f"{self.prefix}/{manifest_name}"

        manifest_file.flush()
        manifest_file.seek(0)
        self.s3.put_object(
            Bucket=self.bucket,
            Key=manifest_key,
            Body=manifest_file,
        )
        manifest_file.close()
        return manifest_key

    def _pad_manifest(self, count: int) -> str:
        """
        Pad the manifest with small requests.

        Args:
            count: How many requests to add

        Returns:
            str: The JSONL records to write to the manifest.
        """
        if count < 1:
            raise ValueError("Count must be at least 1")
        if count > MIN_BATCH_SIZE - 1:
            raise ValueError(f"Count must be less than {MIN_BATCH_SIZE - 1}")
        pad_records = []
        for i in range(count):
            record = BedrockBatchItem(
                recordId=f"{PAD_PREFIX}{i}",
                modelInput=self.model_adapter.to_invoke_model_input(
                    modelId=self.model_id,
                    messages=[
                        {"role": "user", "content": [{"type": "text", "text": "Respond OK"}]},
                    ],
                    inferenceConfig={"maxTokens": 1, "temperature": 0},
                ),
            )
            json_record = json.dumps({k: v for k, v in record.items() if k != "modelOutput"}) + "\n"
            pad_records.append(json_record)
        return "".join(pad_records)


def random_record_id() -> str:
    """
    Create a random 11 character alphanumeric string to use as a record ID.

    Returns:
        str: A random 11 character alphanumeric string.
    """

    return "".join(random.choices(string.ascii_letters + string.digits, k=11))
