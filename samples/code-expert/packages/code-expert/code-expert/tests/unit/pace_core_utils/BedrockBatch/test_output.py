#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from unittest.mock import Mock, MagicMock

from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.output import BedrockBatchOutputProcessor


def test_process_record_with_model_output():
    processor = BedrockBatchOutputProcessor(Mock(), "anthropic.claude.test")
    record = {
        "recordId": "1",
        "modelInput": {
            "messages": [{"role": "user", "content": "Hello, Claude!"}],
            "max_tokens": 100,
            "temperature": 0.7,
        },
        "modelOutput": {
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello! How can I assist you today?"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 4, "output_tokens": 8},
        },
    }
    result = processor.process_record(record)
    assert result.get("record_id") == "1"
    assert result.get("model_output") is not None
    assert result.get("model_output", {}).get("output", {}).get("message", {}).get("role") == "assistant"
    assert (
        result.get("model_output", {}).get("output", {}).get("message", {}).get("content", [{}])[0].get("text")
        == "Hello! How can I assist you today?"
    )
    assert result.get("model_output", {}).get("stopReason") == "end_turn"
    assert result.get("model_output", {}).get("usage", {}).get("inputTokens") == 4
    assert result.get("model_output", {}).get("usage", {}).get("outputTokens") == 8
    assert result.get("error") is None


def test_process_record_with_error():
    processor = BedrockBatchOutputProcessor(Mock(), "anthropic.claude.test")
    record = {
        "recordId": "2",
        "modelInput": {
            "messages": [{"role": "user", "content": "Hello, Claude!"}],
            "max_tokens": 100,
            "temperature": 0.7,
        },
        "error": {"errorMessage": "Some error", "errorCode": 400},
    }
    result = processor.process_record(record)
    assert result.get("record_id") == "2"
    assert result.get("model_output") is None
    assert result.get("error") is not None
    assert result.get("error", {}).get("errorMessage") == "Some error"
    assert result.get("error", {}).get("errorCode") == 400


def test_process_output():
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {
        "Body": MagicMock(
            read=lambda: b"""
            {"recordId": "1", "modelInput": {"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 100}, "modelOutput": {"role": "assistant", "content": [{"type": "text", "text": "Hi there!"}], "stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 3}}}
            {"recordId": "2", "modelInput": {"messages": [{"role": "user", "content": "Error test"}], "max_tokens": 100}, "error": {"errorMessage": "Some error", "errorCode": 400}}
        """
        )
    }

    processor = BedrockBatchOutputProcessor(mock_s3, "anthropic.claude.test")
    results = list(processor.process_output("test-bucket", "test-key"))

    assert len(results) == 2
    assert results[0].get("record_id") == "1"
    assert results[0].get("model_output") is not None
    assert (
        results[0].get("model_output", {}).get("output", {}).get("message", {}).get("content", [{}])[0].get("text")
        == "Hi there!"
    )
    assert results[1].get("record_id") == "2"
    assert results[1].get("error") is not None
    assert results[1].get("error", {}).get("errorMessage") == "Some error"


def test_process_record_invalid_input():
    processor = BedrockBatchOutputProcessor(Mock(), "anthropic.claude.test")
    record = {
        "recordId": "3",
        "modelInput": {"messages": [{"role": "user", "content": "Invalid test"}], "max_tokens": 100},
        # Missing both modelOutput and error
    }
    result = processor.process_record(record)
    assert result.get("record_id") == "3"
    assert result.get("model_output") is None
    assert result.get("error") is not None
    assert result.get("error", {}).get("errorMessage") == "No model output or error found"
    assert result.get("error", {}).get("errorCode") == 500
