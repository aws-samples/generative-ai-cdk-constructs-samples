#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from typing import Dict, Any

import pytest

from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.ConverseToBatch import ModelResponse
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.ConverseToBatch.AnthropicClaude import ClaudeAdapter


class TestAnthropicClaude:

    def test__convert_messages_2(self):
        """
        Test _convert_messages method with both text and image content in the message.
        """
        # Arrange
        messages = [
            {
                "role": "user",
                "content": [
                    {"text": "Here's an image:"},
                    {"image": {"format": "png", "source": {"bytes": "base64encodedpngdata"}}},
                ],
            }
        ]

        # Act
        result = ClaudeAdapter._convert_messages(messages)

        # Assert
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert len(result[0]["content"]) == 2
        assert result[0]["content"][0]["type"] == "text"
        assert result[0]["content"][0]["text"] == "Here's an image:"
        assert result[0]["content"][1]["type"] == "image"
        assert result[0]["content"][1]["source"]["type"] == "base64"
        assert result[0]["content"][1]["source"]["media_type"] == "image/png"
        assert result[0]["content"][1]["source"]["data"] == "base64encodedpngdata"

    def test__convert_messages_raises_value_error_for_unknown_content_type(self):
        """
        Test that _convert_messages raises a ValueError for unknown content type.
        """
        messages = [{"role": "user", "content": [{"unknown_type": "some content"}]}]

        with pytest.raises(ValueError) as exc_info:
            ClaudeAdapter._convert_messages(messages)

        assert str(exc_info.value) == "Unknown content type: {'unknown_type': 'some content'}"

    def test__extract_system_2(self):
        """
        Test _extract_system method when content doesn't contain 'text' key.
        This should raise a ValueError.
        """
        # Arrange
        system = [{"non_text_key": "Some content"}]

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            ClaudeAdapter._extract_system(system)

        assert str(exc_info.value) == "Unknown content type: {'non_text_key': 'Some content'}"

    def test__extract_system_empty_input(self):
        """
        Test _extract_system with an empty input list.
        """
        assert ClaudeAdapter._extract_system([]) == ""

    def test__extract_system_empty_text_content(self):
        """
        Test _extract_system with empty text content.
        """
        empty_text_system = [{"text": ""}]
        result = ClaudeAdapter._extract_system(empty_text_system)
        assert result == "", "Expected an empty string for empty text content"

    def test__extract_system_invalid_content_type(self):
        """
        Test _extract_system with an invalid content type.
        """
        invalid_system = [{"invalid_key": "some content"}]
        with pytest.raises(ValueError, match="Unknown content type:"):
            ClaudeAdapter._extract_system(invalid_system)

    def test__extract_system_mixed_valid_invalid_content(self):
        """
        Test _extract_system with a mix of valid and invalid content.
        """
        mixed_system = [{"text": "Valid content"}, {"invalid_key": "Invalid content"}]
        with pytest.raises(ValueError, match="Unknown content type:"):
            ClaudeAdapter._extract_system(mixed_system)

    def test__extract_system_non_list_input(self):
        """
        Test _extract_system with a non-list input.
        """
        with pytest.raises(ValueError):
            ClaudeAdapter._extract_system("not a list")

    def test__extract_system_with_empty_input(self):
        """
        Test _extract_system method with empty input.
        """
        # Arrange
        system = []

        # Act
        result = ClaudeAdapter._extract_system(system)

        # Assert
        assert result == ""

    def test__extract_system_with_mixed_content(self):
        """
        Test _extract_system method with mixed content, including both valid and invalid items.
        """
        # Arrange
        system = [{"text": "Valid instruction. "}, {"non_text_key": "Invalid content"}]

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            ClaudeAdapter._extract_system(system)

        assert str(exc_info.value) == "Unknown content type: {'non_text_key': 'Invalid content'}"

    def test__extract_system_with_valid_input(self):
        """
        Test _extract_system method with valid input containing 'text' key.
        """
        # Arrange
        system = [{"text": "System instruction 1. "}, {"text": "System instruction 2. "}]

        # Act
        result = ClaudeAdapter._extract_system(system)

        # Assert
        expected = "System instruction 1. System instruction 2. "
        assert result == expected

    def test__extract_tool_choice_2(self):
        """
        Test _extract_tool_choice when toolChoice is set to 'any'
        """
        # Arrange
        tool_config = {"toolChoice": {"any": True}}

        # Act
        result = ClaudeAdapter._extract_tool_choice(tool_config)

        # Assert
        assert result == {"type": "any"}

    def test__extract_tool_choice_3(self):
        """
        Test _extract_tool_choice when a specific tool is specified in the toolConfig.
        """
        tool_config = {"toolChoice": {"tool": {"name": "specific_tool"}}}
        expected_result = {"type": "tool", "name": "specific_tool"}
        result = ClaudeAdapter._extract_tool_choice(tool_config)
        assert result == expected_result, f"Expected {expected_result}, but got {result}"

    def test__extract_tool_choice_4(self):
        """
        Test _extract_tool_choice when an unknown tool choice is provided.
        """
        toolConfig = {"toolChoice": {"unknown": True}}

        with pytest.raises(ValueError) as exc_info:
            ClaudeAdapter._extract_tool_choice(toolConfig)

        assert str(exc_info.value) == f"Unknown tool choice: {toolConfig['toolChoice']}"

    def test__extract_tool_choice_any(self):
        """
        Test _extract_tool_choice when 'any' is specified in the toolConfig.
        """
        tool_config = {"toolChoice": {"any": True}}
        expected_result = {"type": "any"}
        result = ClaudeAdapter._extract_tool_choice(tool_config)
        assert result == expected_result, f"Expected {expected_result}, but got {result}"

    def test__extract_tool_choice_auto(self):
        """
        Test _extract_tool_choice when toolChoice is set to 'auto'
        """
        # Arrange
        tool_config = {"toolChoice": {"auto": True}}

        # Act
        result = ClaudeAdapter._extract_tool_choice(tool_config)

        # Assert
        assert result == {"type": "auto"}

    def test__extract_tool_choice_auto_2(self):
        """
        Test _extract_tool_choice when 'auto' is specified in the toolConfig.
        """
        tool_config = {"toolChoice": {"auto": True}}
        expected_result = {"type": "auto"}
        result = ClaudeAdapter._extract_tool_choice(tool_config)
        assert result == expected_result, f"Expected {expected_result}, but got {result}"

    def test__extract_tool_choice_specific_tool(self):
        """
        Test _extract_tool_choice when a specific tool is chosen
        """
        # Arrange
        tool_config = {"toolChoice": {"tool": {"name": "calculator"}}}

        # Act
        result = ClaudeAdapter._extract_tool_choice(tool_config)

        # Assert
        assert result == {"type": "tool", "name": "calculator"}

    def test__extract_tool_choice_tool_specified(self):
        """
        Test _extract_tool_choice when a specific tool is specified in the toolConfig.
        """
        tool_config = {"toolChoice": {"tool": {"name": "calculator"}}}
        expected_result = {"type": "tool", "name": "calculator"}
        result = ClaudeAdapter._extract_tool_choice(tool_config)
        assert result == expected_result, f"Expected {expected_result}, but got {result}"

    def test__extract_tool_choice_unknown(self):
        """
        Test _extract_tool_choice with an unknown tool choice
        """
        # Arrange
        tool_config = {"toolChoice": {"unknown": True}}

        # Act and Assert
        with pytest.raises(ValueError, match="Unknown tool choice:"):
            ClaudeAdapter._extract_tool_choice(tool_config)

    def test__extract_tool_choice_unknown_2(self):
        """
        Test _extract_tool_choice when an unknown tool choice is specified in the toolConfig.
        """
        tool_config = {"toolChoice": {"unknown": True}}
        with pytest.raises(ValueError) as exc_info:
            ClaudeAdapter._extract_tool_choice(tool_config)
        assert str(exc_info.value) == "Unknown tool choice: {'unknown': True}"

    def test_convert_messages_empty_input(self):
        """
        Test _convert_messages with an empty input list.
        """
        assert ClaudeAdapter._convert_messages([]) == []

    def test_convert_messages_invalid_content_type(self):
        """
        Test _convert_messages with an invalid content type in the message.
        """
        invalid_message = [{"role": "user", "content": [{"invalid_type": "Hello"}]}]
        with pytest.raises(ValueError, match="Unknown content type:"):
            ClaudeAdapter._convert_messages(invalid_message)

    def test_convert_messages_invalid_image_format(self):
        """
        Test _convert_messages with an invalid image format in the message.
        """
        invalid_message = [
            {
                "role": "user",
                "content": [{"image": {"format": "invalid_format", "source": {"bytes": "base64_encoded_image"}}}],
            }
        ]
        result = ClaudeAdapter._convert_messages(invalid_message)
        assert result[0]["content"][0]["source"]["media_type"] == "image/invalid_format"

    def test_convert_messages_invalid_role(self):
        """
        Test _convert_messages with an invalid role in the message.
        """
        invalid_message = [{"role": "invalid_role", "content": [{"text": "Hello"}]}]
        with pytest.raises(ValueError):
            ClaudeAdapter._convert_messages(invalid_message)

    def test_convert_messages_missing_content(self):
        """
        Test _convert_messages with a message missing the content field.
        """
        invalid_message = [{"role": "user"}]
        with pytest.raises(ValueError):
            ClaudeAdapter._convert_messages(invalid_message)

    def test_convert_messages_nested_content(self):
        """
        Test _convert_messages discards extra fields in content.
        """
        nested_message = [{"role": "user", "content": [{"text": "Hello", "nested": {"text": "Nested content"}}]}]
        expected_result = [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]
        result = ClaudeAdapter._convert_messages(nested_message)
        assert result == expected_result, f"Expected {expected_result}, but got {result}"

    def test_convert_messages_non_list_input(self):
        """
        Test _convert_messages with a non-list input.
        """
        with pytest.raises(ValueError):
            ClaudeAdapter._convert_messages("not a list")

    def test_convert_messages_with_image_content(self):
        """
        Test _convert_messages method with image content in the message.
        """
        # Arrange
        messages = [
            {"role": "user", "content": [{"image": {"format": "jpeg", "source": {"bytes": "base64encodedimagedata"}}}]}
        ]

        # Act
        result = ClaudeAdapter._convert_messages(messages)

        # Assert
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert len(result[0]["content"]) == 1
        assert result[0]["content"][0]["type"] == "image"
        assert result[0]["content"][0]["source"]["type"] == "base64"
        assert result[0]["content"][0]["source"]["media_type"] == "image/jpeg"
        assert result[0]["content"][0]["source"]["data"] == "base64encodedimagedata"

    def test_convert_messages_with_text_content(self):
        """
        Test _convert_messages method with text content in messages.
        """
        # Arrange
        messages = [
            {"role": "user", "content": [{"text": "Hello, how are you?"}]},
            {
                "role": "assistant",
                "content": [{"text": "I'm doing well, thank you for asking. How can I assist you today?"}],
            },
        ]

        # Act
        result = ClaudeAdapter._convert_messages(messages)

        # Assert
        expected_result = [
            {"role": "user", "content": [{"type": "text", "text": "Hello, how are you?"}]},
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'm doing well, thank you for asking. How can I assist you today?"}
                ],
            },
        ]
        assert result == expected_result, f"Expected {expected_result}, but got {result}"

    def test_extract_system_with_empty_input(self):
        """
        Test _extract_system method with an empty input.
        """
        # Arrange
        system = []

        # Act
        result = ClaudeAdapter._extract_system(system)

        # Assert
        assert result == ""

    def test_extract_system_with_invalid_content(self):
        """
        Test _extract_system method when content does not contain 'text' key.
        """
        # Arrange
        system = [{"invalid_key": "This should raise an error."}]

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            ClaudeAdapter._extract_system(system)

        assert str(exc_info.value) == "Unknown content type: {'invalid_key': 'This should raise an error.'}"

    def test_extract_system_with_mixed_content(self):
        """
        Test _extract_system method with a mix of valid and invalid content.
        """
        # Arrange
        system = [{"text": "Valid content."}, {"invalid_key": "Invalid content."}]

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            ClaudeAdapter._extract_system(system)

        assert str(exc_info.value) == "Unknown content type: {'invalid_key': 'Invalid content.'}"

    def test_extract_system_with_text_content(self):
        """
        Test _extract_system method when content contains 'text' key.
        """
        # Arrange
        system = [{"text": "This is the first system message."}, {"text": "This is the second system message."}]

        # Act
        result = ClaudeAdapter._extract_system(system)

        # Assert
        expected_output = "This is the first system message.This is the second system message."
        assert result == expected_output

    def test_extract_tool_choice_any(self):
        """
        Test _extract_tool_choice method when toolChoice is set to 'any'.
        """
        tool_config = {"toolChoice": {"any": True}}
        expected_result = {"type": "any"}
        result = ClaudeAdapter._extract_tool_choice(tool_config)
        assert result == expected_result

    def test_extract_tool_choice_auto(self):
        """
        Test _extract_tool_choice method when toolChoice is set to 'auto'.
        """
        tool_config = {"toolChoice": {"auto": True}}
        expected_result = {"type": "auto"}
        result = ClaudeAdapter._extract_tool_choice(tool_config)
        assert result == expected_result

    def test_extract_tool_choice_empty_input(self):
        """
        Test _extract_tool_choice with empty input
        """
        with pytest.raises(KeyError):
            ClaudeAdapter._extract_tool_choice({})

    def test_extract_tool_choice_empty_tool_choice(self):
        """
        Test _extract_tool_choice with empty toolChoice
        """
        with pytest.raises(ValueError):
            ClaudeAdapter._extract_tool_choice({"toolChoice": {}})

    def test_extract_tool_choice_incorrect_format(self):
        """
        Test _extract_tool_choice with incorrect input format
        """
        with pytest.raises(KeyError):
            ClaudeAdapter._extract_tool_choice({"wrongKey": {"auto": True}})

    def test_extract_tool_choice_incorrect_type(self):
        """
        Test _extract_tool_choice with incorrect input type
        """
        with pytest.raises(TypeError):
            ClaudeAdapter._extract_tool_choice("not a dict")

    def test_extract_tool_choice_invalid_input(self):
        """
        Test _extract_tool_choice with invalid input
        """
        with pytest.raises(ValueError):
            ClaudeAdapter._extract_tool_choice({"toolChoice": {"invalid": True}})

    def test_extract_tool_choice_missing_name(self):
        """
        Test _extract_tool_choice with missing name for tool type
        """
        with pytest.raises(ValueError):
            ClaudeAdapter._extract_tool_choice({"toolChoice": {"tool": {}}})

    def test_extract_tool_choice_multiple_keys(self):
        """
        Test _extract_tool_choice with multiple keys in toolChoice
        """
        with pytest.raises(ValueError):
            ClaudeAdapter._extract_tool_choice({"toolChoice": {"auto": True, "any": True}})

    def test_extract_tool_choice_specific_tool(self):
        """
        Test _extract_tool_choice method when a specific tool is chosen.
        """
        tool_config = {"toolChoice": {"tool": {"name": "specific_tool"}}}
        expected_result = {"type": "tool", "name": "specific_tool"}
        result = ClaudeAdapter._extract_tool_choice(tool_config)
        assert result == expected_result

    def test_extract_tool_choice_unknown(self):
        """
        Test _extract_tool_choice method when an unknown tool choice is provided.
        """
        tool_config = {"toolChoice": {"unknown": True}}
        with pytest.raises(ValueError) as excinfo:
            ClaudeAdapter._extract_tool_choice(tool_config)
        assert "Unknown tool choice:" in str(excinfo.value)

    def test_extract_tools_empty_input(self):
        """
        Test _extract_tools with an empty input.
        """
        empty_tool_config = {"tools": []}
        result = ClaudeAdapter._extract_tools(empty_tool_config)
        assert result == [], "Expected an empty list for empty input"

    def test_extract_tools_incorrect_input_type(self):
        """
        Test _extract_tools with incorrect input type.
        """
        incorrect_type_input = "Not a dictionary"
        with pytest.raises(TypeError):
            ClaudeAdapter._extract_tools(incorrect_type_input)

    def test_extract_tools_invalid_schema_format(self):
        """
        Test _extract_tools with invalid schema format.
        """
        invalid_schema_config = {
            "tools": [{"toolSpec": {"name": "test_tool", "inputSchema": {"Invalid schema format": "invalid schema"}}}]
        }
        with pytest.raises(KeyError):
            ClaudeAdapter._extract_tools(invalid_schema_config)

    def test_extract_tools_missing_required_fields(self):
        """
        Test _extract_tools with missing required fields in the input.
        """
        invalid_tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        # Missing 'name' field
                        "inputSchema": {"json": {}}
                    }
                }
            ]
        }
        with pytest.raises(KeyError):
            ClaudeAdapter._extract_tools(invalid_tool_config)

    def test_extract_tools_missing_tools_key(self):
        """
        Test _extract_tools with missing 'tools' key in the input.
        """
        missing_tools_config = {}
        with pytest.raises(KeyError):
            ClaudeAdapter._extract_tools(missing_tools_config)

    def test_extract_tools_multiple_tools(self):
        """
        Test _extract_tools with multiple tools in the input.
        """
        multiple_tools_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "tool1",
                        "description": "Tool 1 description",
                        "inputSchema": {"json": {"type": "object"}},
                    }
                },
                {"toolSpec": {"name": "tool2", "inputSchema": {"json": {"type": "string"}}}},
            ]
        }
        result = ClaudeAdapter._extract_tools(multiple_tools_config)
        assert len(result) == 2, "Expected two tools in the result"
        assert result[0]["name"] == "tool1"
        assert result[1]["name"] == "tool2"
        assert not result[1].get("description"), "Expected no description for tool2"

    def test_extract_tools_null_description(self):
        """
        Test _extract_tools with null description field.
        """
        null_description_config = {
            "tools": [{"toolSpec": {"name": "test_tool", "description": None, "inputSchema": {"json": {}}}}]
        }
        result = ClaudeAdapter._extract_tools(null_description_config)
        assert "description" not in result[0], "Expected no description for null description"

    def test_extract_tools_with_valid_input(self):
        """
        Test _extract_tools method with valid tool configuration input.
        """
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "Calculator",
                        "description": "Perform basic arithmetic operations",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": {
                                    "operation": {"type": "string"},
                                    "operands": {"type": "array", "items": {"type": "number"}},
                                },
                            }
                        },
                    }
                },
                {
                    "toolSpec": {
                        "name": "WeatherAPI",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": {"city": {"type": "string"}, "country": {"type": "string"}},
                            }
                        },
                    }
                },
            ]
        }

        expected_output = [
            {
                "name": "Calculator",
                "description": "Perform basic arithmetic operations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string"},
                        "operands": {"type": "array", "items": {"type": "number"}},
                    },
                },
            },
            {
                "name": "WeatherAPI",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}, "country": {"type": "string"}},
                },
            },
        ]

        result = ClaudeAdapter._extract_tools(tool_config)
        assert result == expected_output, f"Expected {expected_output}, but got {result}"

    def test_parse_model_response_3(self):
        """
        Test parse_model_response with unknown content type and end_turn stop reason
        """
        claude_response = {
            "role": "assistant",
            "content": [{"type": "unknown_type", "data": "some data"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        expected_response = {
            "output": {"message": {"role": "assistant", "content": []}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
        }

        result = ClaudeAdapter.parse_model_response(claude_response)
        assert result == expected_response

    def test_parse_model_response_4(self):
        """
        Test parse_model_response with text content and max_tokens stop reason
        """
        # Arrange
        claude_response = {
            "role": "assistant",
            "content": [{"type": "text", "text": "This is a sample text response."}],
            "stop_reason": "max_tokens",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        # Act
        result = ClaudeAdapter.parse_model_response(claude_response)

        # Assert
        assert result["output"]["message"]["role"] == "assistant"
        assert len(result["output"]["message"]["content"]) == 1
        assert result["output"]["message"]["content"][0]["text"] == "This is a sample text response."
        assert result["stopReason"] == "max_tokens"
        assert result["usage"]["inputTokens"] == 10
        assert result["usage"]["outputTokens"] == 20
        assert result["usage"]["totalTokens"] == 30

    def test_parse_model_response_empty_input(self):
        """
        Test parse_model_response with an empty input dictionary.
        """
        with pytest.raises(KeyError):
            ClaudeAdapter.parse_model_response({})

    def test_parse_model_response_incorrect_type(self):
        """
        Test parse_model_response with incorrect input type.
        """
        with pytest.raises(TypeError):
            ClaudeAdapter.parse_model_response("not a dictionary")

    def test_parse_model_response_invalid_content_type(self):
        """
        Test parse_model_response with an invalid content type.
        """
        invalid_input = {
            "role": "assistant",
            "content": [{"type": "invalid_type", "text": "Some text"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        result = ClaudeAdapter.parse_model_response(invalid_input)
        assert len(result["output"]["message"]["content"]) == 0

    def test_parse_model_response_invalid_input(self):
        """
        Test parse_model_response with invalid input missing required keys.
        """
        invalid_input = {"role": "assistant", "content": [], "usage": {"input_tokens": 10, "output_tokens": 20}}
        with pytest.raises(KeyError):
            ClaudeAdapter.parse_model_response(invalid_input)

    def test_parse_model_response_missing_tool_use_id(self):
        """
        Test parse_model_response with a tool_use content missing the 'id' field.
        """
        invalid_input = {
            "role": "assistant",
            "content": [{"type": "tool_use", "input": "Some input"}],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        with pytest.raises(KeyError):
            ClaudeAdapter.parse_model_response(invalid_input)

    def test_parse_model_response_negative_token_count(self):
        """
        Test parse_model_response with negative token counts.
        """
        invalid_input = {
            "role": "assistant",
            "content": [],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": -10, "output_tokens": -20},
        }
        result = ClaudeAdapter.parse_model_response(invalid_input)
        assert result["usage"]["totalTokens"] == -30

    def test_parse_model_response_text_content_stop_sequence(self):
        """
        Test parse_model_response with text content and stop_sequence stop reason
        """
        claude_response = {
            "role": "assistant",
            "content": [{"type": "text", "text": "This is a test response."}],
            "stop_reason": "stop_sequence",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        expected_response = {
            "output": {"message": {"role": "assistant", "content": [{"text": "This is a test response."}]}},
            "stopReason": "stop_sequence",
            "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
        }

        result = ClaudeAdapter.parse_model_response(claude_response)
        assert result == expected_response

    def test_parse_model_response_text_content_tool_use_stop_reason(self):
        """
        Test parse_model_response with text content and tool_use stop reason.
        """
        claude_response = {
            "role": "assistant",
            "content": [{"type": "text", "text": "Here's the information you requested."}],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        expected_response = {
            "output": {
                "message": {"role": "assistant", "content": [{"text": "Here's the information you requested."}]}
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
        }

        result = ClaudeAdapter.parse_model_response(claude_response)
        assert result == expected_response

    def test_parse_model_response_text_content_unknown_stop_reason(self):
        """
        Test parse_model_response with text content and an unknown stop reason.
        """
        claude_response = {
            "role": "assistant",
            "content": [{"type": "text", "text": "This is a test response."}],
            "stop_reason": "unknown_reason",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        expected_response = {
            "output": {"message": {"role": "assistant", "content": [{"text": "This is a test response."}]}},
            "stopReason": "unknown_reason",
            "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
        }

        result = ClaudeAdapter.parse_model_response(claude_response)
        assert result == expected_response

    def test_parse_model_response_tool_use_and_end_turn(self):
        """
        Test parse_model_response with tool use content and end_turn stop reason
        """
        claude_response = {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "calculator", "input": {"operation": "add", "numbers": [2, 3]}}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        expected_response: ModelResponse = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "calculator",
                                "name": "calculator",
                                "input": {"operation": "add", "numbers": [2, 3]},
                            }
                        }
                    ],
                }
            },
            "stopReason": "end_turn",
            "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
        }

        result = ClaudeAdapter.parse_model_response(claude_response)
        assert result == expected_response

    def test_parse_model_response_with_text_content_and_end_turn(self):
        """
        Test parse_model_response with text content and end_turn stop reason
        """
        claude_response = {
            "role": "assistant",
            "content": [{"type": "text", "text": "This is a test response."}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        expected_response = {
            "output": {"message": {"role": "assistant", "content": [{"text": "This is a test response."}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
        }

        result = ClaudeAdapter.parse_model_response(claude_response)
        assert result == expected_response

    def test_to_invoke_model_input_2(self):
        """
        Test to_invoke_model_input with system, toolConfig, and additionalModelRequestFields.
        """
        # Arrange
        model_id = "claude-v2"
        system = [{"text": "You are a helpful assistant."}]
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "calculator",
                        "description": "Perform mathematical calculations",
                        "inputSchema": {"json": '{"type": "object", "properties": {"expression": {"type": "string"}}}'},
                    }
                }
            ],
            "toolChoice": {"auto": True},
        }
        additional_fields = {"custom_field": "custom_value"}

        # Act and Assert
        with pytest.raises(ValueError, match="Messages are required for this model"):
            ClaudeAdapter.to_invoke_model_input(
                modelId=model_id,
                messages=None,
                system=system,
                toolConfig=tool_config,
                additionalModelRequestFields=additional_fields,
            )

    def test_to_invoke_model_input_3(self):
        """
        Test to_invoke_model_input with messages, toolConfig, and additionalModelRequestFields
        """
        # Arrange
        model_id = "anthropic.claude-v2"
        messages = [{"role": "user", "content": [{"text": "Hello, Claude!"}]}]
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "calculator",
                        "description": "Perform calculations",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": {
                                    "operation": {"type": "string"},
                                    "operands": {"type": "array", "items": {"type": "number"}},
                                },
                            }
                        },
                    }
                }
            ],
            "toolChoice": {"auto": True},
        }
        additional_fields = {"extra_field": "extra_value"}

        # Act
        result = ClaudeAdapter.to_invoke_model_input(
            modelId=model_id, messages=messages, toolConfig=tool_config, additionalModelRequestFields=additional_fields
        )

        # Assert
        assert isinstance(result, dict)
        assert result["anthropic_version"] == "bedrock-2023-05-31"
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"][0]["type"] == "text"
        assert result["messages"][0]["content"][0]["text"] == "Hello, Claude!"
        assert "tools" in result
        assert len(result["tools"]) == 1
        assert result["tools"][0]["name"] == "calculator"
        assert "tool_config" in result
        assert result["tool_config"]["type"] == "auto"
        assert "extra_field" in result
        assert result["extra_field"] == "extra_value"

    def test_to_invoke_model_input_additional_fields_override(self):
        """
        Test that additional model request fields override existing fields.
        """
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        additional_fields = {"anthropic_version": "custom-version"}

        result = ClaudeAdapter.to_invoke_model_input(
            modelId="test-model", messages=messages, additionalModelRequestFields=additional_fields
        )

        assert result["anthropic_version"] == "custom-version"

    def test_to_invoke_model_input_empty_messages(self):
        """
        Test that to_invoke_model_input raises a ValueError when messages are empty.
        """
        with pytest.raises(ValueError, match="Messages are required for this model"):
            ClaudeAdapter.to_invoke_model_input(modelId="test-model", messages=[])

    def test_to_invoke_model_input_invalid_inference_config(self):
        """
        Test that to_invoke_model_input handles invalid inference config gracefully.
        """
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        invalid_inference_config: Dict[str, Any] = {"invalid_key": "invalid_value"}

        result = ClaudeAdapter.to_invoke_model_input(
            modelId="test-model", messages=messages, inferenceConfig=invalid_inference_config
        )

        assert "max_tokens" not in result
        assert "temperature" not in result
        assert "top_p" not in result
        assert "stop_sequences" not in result
        assert "invalid_key" not in result

    def test_to_invoke_model_input_invalid_message_content(self):
        """
        Test that to_invoke_model_input raises a ValueError for invalid message content.
        """
        invalid_messages = [{"role": "user", "content": [{"invalid": "content"}]}]

        with pytest.raises(ValueError, match="Unknown content type:"):
            ClaudeAdapter.to_invoke_model_input(modelId="test-model", messages=invalid_messages)

    def test_to_invoke_model_input_invalid_system_content(self):
        """
        Test that to_invoke_model_input raises a ValueError for invalid system content.
        """
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        invalid_system = [{"invalid": "content"}]

        with pytest.raises(ValueError, match="Unknown content type:"):
            ClaudeAdapter.to_invoke_model_input(modelId="test-model", messages=messages, system=invalid_system)

    def test_to_invoke_model_input_invalid_tool_config(self):
        """
        Test that to_invoke_model_input raises a ValueError for invalid tool config.
        """
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        invalid_tool_config = {"toolChoice": {"invalid": True}}

        with pytest.raises(ValueError, match="Unknown tool choice:"):
            ClaudeAdapter.to_invoke_model_input(modelId="test-model", messages=messages, toolConfig=invalid_tool_config)

    def test_to_invoke_model_input_none_messages(self):
        """
        Test that to_invoke_model_input raises a ValueError when messages are None.
        """
        with pytest.raises(ValueError, match="Messages are required for this model"):
            ClaudeAdapter.to_invoke_model_input(modelId="test-model", messages=None)

    def test_to_invoke_model_input_with_all_parameters(self):
        """
        Test to_invoke_model_input method with all parameters provided.
        """
        model_id = "anthropic.claude-v2"
        messages = [
            {"role": "user", "content": [{"text": "Hello, Claude!"}]},
            {"role": "assistant", "content": [{"text": "Hello! How can I assist you today?"}]},
        ]
        system = [{"text": "You are a helpful AI assistant."}]
        inference_config = {"maxTokens": 100, "temperature": 0.7, "topP": 0.9, "stopSequences": ["User:"]}
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "calculator",
                        "description": "Perform basic calculations",
                        "inputSchema": {
                            "json": '{"type": "object", "properties": {"operation": {"type": "string"}, "numbers": {"type": "array", "items": {"type": "number"}}}}'
                        },
                    }
                }
            ],
            "toolChoice": {"auto": True},
        }
        additional_fields = {"stream": True}

        result = ClaudeAdapter.to_invoke_model_input(
            modelId=model_id,
            messages=messages,
            system=system,
            inferenceConfig=inference_config,
            toolConfig=tool_config,
            additionalModelRequestFields=additional_fields,
        )

        assert isinstance(result, dict)
        assert result["anthropic_version"] == "bedrock-2023-05-31"
        assert result["max_tokens"] == 100
        assert result["temperature"] == 0.7
        assert result["top_p"] == 0.9
        assert result["stop_sequences"] == ["User:"]
        assert len(result["messages"]) == 2
        assert result["system"] == "You are a helpful AI assistant."
        assert len(result["tools"]) == 1
        assert result["tool_config"] == {"type": "auto"}
        assert result["stream"] == True

    def test_to_invoke_model_input_with_messages_system_and_additional_fields(self):
        """
        Test to_invoke_model_input with messages, system, and additionalModelRequestFields.
        """
        # Arrange
        model_id = "claude-v2"
        messages = [
            {"role": "user", "content": [{"text": "Hello, Claude!"}]},
            {"role": "assistant", "content": [{"text": "Hello! How can I assist you today?"}]},
        ]
        system = [{"text": "You are a helpful AI assistant."}]
        additional_fields = {"stream": True, "custom_field": "test_value"}

        # Act
        result = ClaudeAdapter.to_invoke_model_input(
            modelId=model_id, messages=messages, system=system, additionalModelRequestFields=additional_fields
        )

        # Assert
        assert isinstance(result, dict)
        assert result["anthropic_version"] == "bedrock-2023-05-31"
        assert "messages" in result
        assert len(result["messages"]) == 2
        assert result["system"] == "You are a helpful AI assistant."
        assert result["stream"] == True
        assert result["custom_field"] == "test_value"
        assert "tools" not in result
        assert "tool_config" not in result

    def test_to_invoke_model_input_with_messages_system_and_tool_config(self):
        """
        Test to_invoke_model_input with messages, system, and toolConfig (including tools and toolChoice)
        """
        model_id = "anthropic.claude-v2"
        messages = [
            {"role": "user", "content": [{"text": "Hello, Claude!"}]},
            {"role": "assistant", "content": [{"text": "Hello! How can I help you today?"}]},
        ]
        system = [{"text": "You are a helpful AI assistant."}]
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "calculator",
                        "description": "Perform calculations",
                        "inputSchema": {"json": '{"type": "object", "properties": {"expression": {"type": "string"}}}'},
                    }
                }
            ],
            "toolChoice": {"auto": True},
        }

        result = ClaudeAdapter.to_invoke_model_input(
            modelId=model_id, messages=messages, system=system, toolConfig=tool_config
        )

        assert isinstance(result, dict)
        assert result["anthropic_version"] == "bedrock-2023-05-31"
        assert "messages" in result
        assert len(result["messages"]) == 2
        assert result["system"] == "You are a helpful AI assistant."
        assert "tools" in result
        assert len(result["tools"]) == 1
        assert result["tools"][0]["name"] == "calculator"
        assert "tool_config" in result
        assert result["tool_config"] == {"type": "auto"}

    def test_to_invoke_model_input_with_messages_system_tools_and_additional_fields(self):
        """
        Test to_invoke_model_input with messages, system, tools, and additional request fields.
        """
        modelId = "claude-v2"
        messages = [
            {"role": "user", "content": [{"text": "Hello, Claude!"}]},
            {"role": "assistant", "content": [{"text": "Hello! How can I assist you today?"}]},
        ]
        system = [{"text": "You are a helpful AI assistant."}]
        toolConfig = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "calculator",
                        "description": "Perform mathematical calculations",
                        "inputSchema": {"json": '{"type": "object", "properties": {"expression": {"type": "string"}}}'},
                    }
                }
            ]
        }
        additionalModelRequestFields = {"stream": False}

        expected_output = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hello, Claude!"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "Hello! How can I assist you today?"}]},
            ],
            "system": "You are a helpful AI assistant.",
            "tools": [
                {
                    "name": "calculator",
                    "description": "Perform mathematical calculations",
                    "input_schema": '{"type": "object", "properties": {"expression": {"type": "string"}}}',
                }
            ],
            "stream": False,
        }

        result = ClaudeAdapter.to_invoke_model_input(
            modelId=modelId,
            messages=messages,
            system=system,
            toolConfig=toolConfig,
            additionalModelRequestFields=additionalModelRequestFields,
        )

        assert result == expected_output

    def test_to_invoke_model_input_with_tool_choice_and_additional_fields(self):
        """
        Test to_invoke_model_input with messages, system, toolConfig (with toolChoice), and additionalModelRequestFields.
        """
        # Arrange
        model_id = "claude-v2"
        messages = [{"role": "user", "content": [{"text": "Hello, Claude!"}]}]
        system = [{"text": "You are a helpful AI assistant."}]
        tool_config = {"toolChoice": {"any": True}}
        additional_fields = {"custom_field": "custom_value"}

        # Act
        result = ClaudeAdapter.to_invoke_model_input(
            modelId=model_id,
            messages=messages,
            system=system,
            toolConfig=tool_config,
            additionalModelRequestFields=additional_fields,
        )

        # Assert
        assert isinstance(result, dict)
        assert result["anthropic_version"] == "bedrock-2023-05-31"
        assert result["messages"] == [{"role": "user", "content": [{"type": "text", "text": "Hello, Claude!"}]}]
        assert result["system"] == "You are a helpful AI assistant."
        assert result["tool_config"] == {"type": "any"}
        assert result["custom_field"] == "custom_value"
        assert "tools" not in result
