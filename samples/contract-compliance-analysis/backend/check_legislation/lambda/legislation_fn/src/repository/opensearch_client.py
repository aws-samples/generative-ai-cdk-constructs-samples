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
from typing import List, Optional, Dict, Any

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from model import Legislation


class OpenSearchLegislationClient:
    """OpenSearch client for legislation search operations."""

    def __init__(
        self,
        aoss_endpoint: str,
        index_name: str,
        metadata_field: str = "metadata",
        region: str = os.getenv("AWS_REGION") or boto3.Session().region_name or "us-east-1",
    ):
        self.aoss_endpoint = aoss_endpoint
        self.index_name = index_name
        self.metadata_field = metadata_field
        self.region = region
        self._client: Optional[OpenSearch] = None

    def list_legislations(self) -> List[Legislation]:
        """List distinct legislations by aggregating on law_id."""
        client = self._get_client()

        # Fields are at root level in Bedrock Knowledge Base index
        law_id_kw = "law_id.keyword"
        law_id_plain = "law_id"
        law_name_field = "law_name"
        subject_matter_field = "subject_matter"
        source_uri_field = "source_uri"

        aggs_body = {
            "size": 0,
            "query": {"match_all": {}},
            "aggs": {
                "laws": {
                    "terms": {"field": law_id_kw, "size": 1000},
                    "aggs": {
                        "sample": {
                            "top_hits": {
                                "size": 1,
                                "_source": {"includes": [law_name_field, subject_matter_field, source_uri_field]},
                            }
                        }
                    },
                }
            },
        }

        try:
            response = client.search(index=self.index_name, body=aggs_body)
        except Exception:
            # Fallback if .keyword not present
            aggs_body["aggs"]["laws"]["terms"]["field"] = law_id_plain
            response = client.search(index=self.index_name, body=aggs_body)

        return self._parse_response(response, law_name_field, subject_matter_field, source_uri_field)

    def _get_client(self) -> OpenSearch:
        """Get or create OpenSearch client."""
        if self._client:
            return self._client

        session = boto3.Session(region_name=self.region)
        creds = session.get_credentials().get_frozen_credentials()
        awsauth = AWS4Auth(creds.access_key, creds.secret_key, self.region, "aoss", session_token=creds.token)
        host = self.aoss_endpoint.replace("https://", "").replace("http://", "")

        self._client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=10,
            max_retries=2,
            retry_on_timeout=True,
        )
        return self._client

    def _parse_response(self, response: Dict[str, Any], law_name_field: str, subject_matter_field: str, source_uri_field: str) -> List[Legislation]:
        """Parse OpenSearch aggregation response."""
        buckets = response.get("aggregations", {}).get("laws", {}).get("buckets", [])
        items: List[Legislation] = []

        for bucket in buckets:
            law_id = str(bucket.get("key"))
            sample_hits = bucket.get("sample", {}).get("hits", {}).get("hits", [])

            law_name = law_id
            subject_matter = ""
            s3_key = None

            if sample_hits:
                src = sample_hits[0].get("_source", {}) or {}
                law_name = src.get(law_name_field, law_id) or law_id
                subject_matter = src.get(subject_matter_field, "") or ""
                s3_key = self._s3_key_from_uri(src.get(source_uri_field))

            items.append(Legislation(id=law_id, subject_matter=subject_matter, name=law_name, s3_key=s3_key))

        return items

    def _s3_key_from_uri(self, uri: Optional[str]) -> Optional[str]:
        """Extract S3 key from S3 URI."""
        if not uri or not uri.startswith("s3://"):
            return None
        from urllib.parse import urlparse
        p = urlparse(uri)
        return p.path.lstrip("/")
