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

import os
import time
from typing import Optional, Dict, Any, List

import boto3

from model import Legislation


class BedrockAgentLegislationClient:
    """Bedrock Agent client for legislation ingestion operations."""

    TERMINAL_SUCCESS = {"INDEXED", "PARTIALLY_INDEXED", "METADATA_PARTIALLY_INDEXED"}
    TERMINAL_FAILURE = {"FAILED", "METADATA_UPDATE_FAILED", "IGNORED", "NOT_FOUND"}

    def __init__(
        self,
        kb_id: str,
        data_source_id: str,
        bucket_name: str,
        region: str = os.getenv("AWS_REGION") or boto3.Session().region_name or "us-east-1",
        wait_on_ingest: bool = True,
        poll_interval: float = 5.0,
        timeout_seconds: float = 1800.0,
        logger: Optional[Any] = None,
    ):
        self.kb_id = kb_id
        self.data_source_id = data_source_id
        self.bucket_name = bucket_name
        self.region = region
        self.wait_on_ingest = wait_on_ingest
        self.poll_interval = poll_interval
        self.timeout_seconds = timeout_seconds
        self.logger = logger
        self._client = None

    def ingest_legislation(self, legislation: Legislation) -> str:
        """Ingest legislation document into Knowledge Base."""
        if not legislation.id or not legislation.name:
            raise ValueError("Legislation.id and .name are required")
        if not legislation.s3_key:
            raise ValueError("Legislation.s3_key is required for S3 ingestion")

        client = self._get_client()
        s3_uri = f"s3://{self.bucket_name}/{legislation.s3_key}"

        metadata = {
            "subject_matter": legislation.subject_matter,
            "law_id": legislation.id,
            "law_name": legislation.name,
            "source_uri": s3_uri,
        }

        response = client.ingest_knowledge_base_documents(
            knowledgeBaseId=self.kb_id,
            dataSourceId=self.data_source_id,
            documents=[{
                "content": {
                    "dataSourceType": "CUSTOM",
                    "custom": {
                        "customDocumentIdentifier": {"id": f"{legislation.subject_matter}-{legislation.id}"},
                        "s3Location": {"uri": s3_uri},
                        "sourceType": "S3_LOCATION",
                    },
                },
                "metadata": {
                    "type": "IN_LINE_ATTRIBUTE",
                    "inlineAttributes": self._inline_attributes(metadata),
                },
            }],
        )

        if self.logger:
            self.logger.info({"ingest_submitted": response.get("documentDetails", [])})

        if not self.wait_on_ingest:
            return legislation.id

        # Poll until complete
        identifier = {"dataSourceType": "CUSTOM", "custom": {"id": f"{legislation.subject_matter}-{legislation.id}"}}
        code = self._poll_until_complete(client, [identifier])
        if code != 0:
            raise RuntimeError(f"Ingestion failed for law_id={legislation.id}")

        return legislation.id

    def _get_client(self):
        """Get or create Bedrock Agent client."""
        if self._client:
            return self._client
        self._client = boto3.client("bedrock-agent", region_name=self.region)
        return self._client

    def _inline_attributes(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert metadata dict to KB inline attributes format."""
        attrs: List[Dict[str, Any]] = []

        for key, value in metadata.items():
            if value is None or (isinstance(value, str) and value.strip() == ""):
                continue
            if isinstance(value, (list, tuple)) and len(value) == 0:
                continue

            if isinstance(value, bool):
                attrs.append({"key": key, "value": {"type": "BOOLEAN", "booleanValue": value}})
            elif isinstance(value, (int, float)):
                attrs.append({"key": key, "value": {"type": "NUMBER", "numberValue": float(value)}})
            elif isinstance(value, (list, tuple)):
                attrs.append({"key": key, "value": {"type": "STRING_LIST", "stringListValue": [str(x) for x in value]}})
            else:
                attrs.append({"key": key, "value": {"type": "STRING", "stringValue": str(value)}})

        return attrs

    def _poll_until_complete(self, client, identifiers: List[Dict[str, Any]]) -> int:
        """Poll until ingestion completes."""
        deadline = time.time() + self.timeout_seconds
        last: Dict[str, str] = {}

        while True:
            response = client.get_knowledge_base_documents(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                documentIdentifiers=identifiers,
            )

            details = response.get("documentDetails", [])
            all_done, any_fail, any_succ = True, False, False

            for detail in details:
                ident = detail.get("identifier", {})
                status = (detail.get("status") or "").upper()
                reason = detail.get("statusReason") or ""
                ident_str = str(ident)

                if last.get(ident_str) != status:
                    if self.logger:
                        self.logger.info({"kb_doc_status": status, "identifier": ident, "reason": reason})
                    last[ident_str] = status

                if status in self.TERMINAL_FAILURE:
                    any_fail = True
                elif status in self.TERMINAL_SUCCESS:
                    any_succ = True
                else:
                    all_done = False

            if all_done:
                return 0 if (any_succ and not any_fail) else 2

            if time.time() > deadline:
                if self.logger:
                    self.logger.error("Timed out waiting for indexing")
                return 2

            time.sleep(self.poll_interval)
