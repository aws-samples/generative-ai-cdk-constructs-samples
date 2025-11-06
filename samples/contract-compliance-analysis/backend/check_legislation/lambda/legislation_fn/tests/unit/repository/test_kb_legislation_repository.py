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

"""
Unit tests for the refactored KBLegislationRepository with separate client classes.
"""
import pytest
from unittest.mock import Mock

from model import Legislation
from repository.kb_legislation_repository import KBLegislationRepository
from repository.opensearch_client import OpenSearchLegislationClient
from repository.bedrock_agent_client import BedrockAgentLegislationClient


class TestKBLegislationRepository:
    """Test suite for KBLegislationRepository."""

    @pytest.fixture
    def mock_opensearch_client(self):
        """Mock OpenSearch client."""
        return Mock(spec=OpenSearchLegislationClient)

    @pytest.fixture
    def mock_bedrock_agent_client(self):
        """Mock Bedrock Agent client."""
        return Mock(spec=BedrockAgentLegislationClient)

    @pytest.fixture
    def repository(self, mock_opensearch_client, mock_bedrock_agent_client):
        """Create repository instance with mocked clients."""
        return KBLegislationRepository(
            opensearch_client=mock_opensearch_client,
            bedrock_agent_client=mock_bedrock_agent_client,
        )

    @pytest.fixture
    def sample_legislation(self):
        """Sample legislation for testing."""
        return Legislation(
            id="test-law-id",
            subject_matter="Consumer Protection",
            name="Test Consumer Law",
            s3_key="legislation/test-law.pdf"
        )

    def test_init_with_clients(self, mock_opensearch_client, mock_bedrock_agent_client):
        """Test repository initialization with client instances."""
        repo = KBLegislationRepository(
            opensearch_client=mock_opensearch_client,
            bedrock_agent_client=mock_bedrock_agent_client,
        )

        assert repo.opensearch_client is mock_opensearch_client
        assert repo.bedrock_agent_client is mock_bedrock_agent_client

    def test_list_legislations_delegates_to_opensearch_client(self, repository, mock_opensearch_client):
        """Test that list_legislations delegates to OpenSearch client."""
        expected_legislations = [
            Legislation(id="law-1", subject_matter="Consumer Rights", name="Consumer Protection Act", s3_key="law1.pdf"),
            Legislation(id="law-2", subject_matter="Data Protection", name="Privacy Act", s3_key="law2.pdf"),
        ]
        mock_opensearch_client.list_legislations.return_value = expected_legislations

        result = repository.list_legislations()

        assert result == expected_legislations
        mock_opensearch_client.list_legislations.assert_called_once()

    def test_ingest_legislation_delegates_to_bedrock_agent_client(self, repository, mock_bedrock_agent_client, sample_legislation):
        """Test that ingest_legislation delegates to Bedrock Agent client."""
        expected_result = "test-law-id"
        mock_bedrock_agent_client.ingest_legislation.return_value = expected_result

        result = repository.ingest_legislation(sample_legislation)

        assert result == expected_result
        mock_bedrock_agent_client.ingest_legislation.assert_called_once_with(sample_legislation)


class TestOpenSearchLegislationClient:
    """Test suite for OpenSearchLegislationClient."""

    @pytest.fixture
    def mock_opensearch(self):
        """Mock OpenSearch instance."""
        return Mock()

    @pytest.fixture
    def client(self, mock_opensearch):
        """Create OpenSearch client with mocked OpenSearch."""
        client = OpenSearchLegislationClient(
            aoss_endpoint="https://test.us-east-1.aoss.amazonaws.com",
            index_name="test-index",
            metadata_field="metadata",
            region="us-east-1",
        )
        client._client = mock_opensearch
        return client

    def test_list_legislations_success(self, client, mock_opensearch):
        """Test successful listing of legislations."""
        mock_response = {
            "aggregations": {
                "laws": {
                    "buckets": [{
                        "key": "law-1",
                        "sample": {
                            "hits": {
                                "hits": [{
                                    "_source": {
                                        "law_name": "Consumer Protection Act",
                                        "subject_matter": "Consumer Rights",
                                        "source_uri": "s3://test-bucket/law1.pdf"
                                    }
                                }]
                            }
                        }
                    }]
                }
            }
        }
        mock_opensearch.search.return_value = mock_response

        result = client.list_legislations()

        assert len(result) == 1
        assert result[0].id == "law-1"
        assert result[0].name == "Consumer Protection Act"
        assert result[0].subject_matter == "Consumer Rights"
        assert result[0].s3_key == "law1.pdf"

    def test_s3_key_from_uri(self, client):
        """Test S3 key extraction from URI."""
        assert client._s3_key_from_uri("s3://bucket/path/file.pdf") == "path/file.pdf"
        assert client._s3_key_from_uri("http://example.com/file.pdf") is None
        assert client._s3_key_from_uri(None) is None


class TestBedrockAgentLegislationClient:
    """Test suite for BedrockAgentLegislationClient."""

    @pytest.fixture
    def mock_bedrock_agent(self):
        """Mock Bedrock Agent boto3 client."""
        return Mock()

    @pytest.fixture
    def client(self, mock_bedrock_agent):
        """Create Bedrock Agent client with mocked boto3 client."""
        client = BedrockAgentLegislationClient(
            kb_id="test-kb-id",
            data_source_id="test-data-source-id",
            bucket_name="test-bucket",
            region="us-east-1",
            wait_on_ingest=False,  # Don't wait for tests
        )
        client._client = mock_bedrock_agent
        return client

    @pytest.fixture
    def sample_legislation(self):
        """Sample legislation for testing."""
        return Legislation(
            id="test-law-id",
            subject_matter="Consumer Protection",
            name="Test Consumer Law",
            s3_key="legislation/test-law.pdf"
        )

    def test_ingest_legislation_success(self, client, mock_bedrock_agent, sample_legislation):
        """Test successful legislation ingestion."""
        mock_response = {"documentDetails": [{"status": "INDEXED"}]}
        mock_bedrock_agent.ingest_knowledge_base_documents.return_value = mock_response

        result = client.ingest_legislation(sample_legislation)

        assert result == "test-law-id"
        mock_bedrock_agent.ingest_knowledge_base_documents.assert_called_once()

    def test_ingest_legislation_missing_id(self, client):
        """Test ingestion fails with missing legislation ID."""
        legislation = Legislation(id="", subject_matter="test", name="Test Law", s3_key="test.pdf")

        with pytest.raises(ValueError, match="Legislation.id and .name are required"):
            client.ingest_legislation(legislation)

    def test_ingest_legislation_missing_s3_key(self, client):
        """Test ingestion fails with missing S3 key."""
        legislation = Legislation(id="test-id", subject_matter="test", name="Test Law", s3_key=None)

        with pytest.raises(ValueError, match="Legislation.s3_key is required for S3 ingestion"):
            client.ingest_legislation(legislation)

    def test_inline_attributes_conversion(self, client):
        """Test metadata to inline attributes conversion."""
        metadata = {
            "string_field": "test_value",
            "number_field": 42,
            "boolean_field": True,
            "list_field": ["item1", "item2"],
            "empty_string": "",
            "none_field": None,
        }

        result = client._inline_attributes(metadata)

        # Should skip empty/None values
        assert len(result) == 4

        # Check string field
        string_attr = next(attr for attr in result if attr["key"] == "string_field")
        assert string_attr["value"]["type"] == "STRING"
        assert string_attr["value"]["stringValue"] == "test_value"
