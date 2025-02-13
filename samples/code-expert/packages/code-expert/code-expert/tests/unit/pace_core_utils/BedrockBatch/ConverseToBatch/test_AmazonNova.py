#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import pytest

from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.ConverseToBatch.AmazonNova import NovaAdapter


class TestAmazonNova:

    def test_parse_model_response_returns_input_dict(self):
        """
        Test that parse_model_response returns the input dictionary as is.
        """
        # Arrange
        input_response = {"message": "Test message", "status": "success", "data": {"key1": "value1", "key2": "value2"}}

        # Act
        result = NovaAdapter.parse_model_response(input_response)

        # Assert
        assert result == input_response
        assert result is input_response

    def test_parse_model_response_with_empty_input(self):
        """
        Test parse_model_response with an empty dictionary input.
        """
        empty_response = {}
        result = NovaAdapter.parse_model_response(empty_response)
        assert result == {}, "Expected an empty dictionary to be returned"

    def test_parse_model_response_with_incorrect_type(self):
        """
        Test parse_model_response with an incorrect input type (list instead of dict).
        """
        incorrect_type_input = []
        with pytest.raises(AttributeError):
            NovaAdapter.parse_model_response(incorrect_type_input)

    def test_parse_model_response_with_invalid_keys(self):
        """
        Test parse_model_response with invalid keys in the input dictionary.
        """
        invalid_response = {"invalid_key": "invalid_value"}
        result = NovaAdapter.parse_model_response(invalid_response)
        assert result == {"invalid_key": "invalid_value"}, "Expected the input dictionary to be returned as-is"

    def test_parse_model_response_with_large_input(self):
        """
        Test parse_model_response with a large input dictionary to check for any size-related issues.
        """
        large_input = {str(i): i for i in range(10000)}
        result = NovaAdapter.parse_model_response(large_input)
        assert result == large_input, "Expected the large input dictionary to be returned as-is"

    def test_parse_model_response_with_nested_structure(self):
        """
        Test parse_model_response with a nested dictionary structure.
        """
        nested_input = {"outer": {"inner": {"value": 42}}}
        result = NovaAdapter.parse_model_response(nested_input)
        assert result == nested_input, "Expected the nested input dictionary to be returned as-is"

    def test_parse_model_response_with_none_input(self):
        """
        Test parse_model_response with None input, which is an invalid input type.
        """
        with pytest.raises(AttributeError):
            NovaAdapter.parse_model_response(None)

    def test_to_invoke_model_input_2(self):
        """
        Test to_invoke_model_input with inferenceConfig and toolConfig, without system
        """
        # Arrange
        model_id = "test_model"
        messages = [{"role": "user", "content": "Hello"}]
        inference_config = {"temperature": 0.7, "top_p": 0.9}
        tool_config = {"tool_choice": "auto"}

        # Act
        result = NovaAdapter.to_invoke_model_input(
            modelId=model_id, messages=messages, inferenceConfig=inference_config, toolConfig=tool_config
        )

        # Assert
        assert isinstance(result, dict)
        assert "messages" in result
        assert result["messages"] == messages
        assert "inferenceConfig" in result
        assert result["inferenceConfig"] == inference_config
        assert "toolConfig" in result
        assert result["toolConfig"] == tool_config
        assert "system" not in result

    def test_to_invoke_model_input_empty_messages(self):
        """
        Test that the method handles empty messages input correctly.
        """
        result = NovaAdapter.to_invoke_model_input(modelId="test_model", messages=[])
        assert result == {"messages": []}

    def test_to_invoke_model_input_missing_required_parameter(self):
        """
        Test that the method raises an error when a required parameter (modelId) is missing.
        """
        with pytest.raises(TypeError):
            NovaAdapter.to_invoke_model_input()

    def test_to_invoke_model_input_unused_parameters(self):
        """
        Test that the method ignores unused parameters.
        """
        result = NovaAdapter.to_invoke_model_input(
            modelId="test_model",
            messages=[],
            guardrailConfig={},
            additionalModelRequestFields={},
            promptVariables={},
            additionalModelResponseFieldPaths=[],
            requestMetadata={},
            performanceConfig={},
        )
        assert result == {"messages": []}

    def test_to_invoke_model_input_with_optional_parameters(self):
        """
        Test to_invoke_model_input method with system, inferenceConfig, and toolConfig parameters.
        """
        # Arrange
        model_id = "test_model"
        messages = [{"role": "user", "content": "Hello"}]
        system = [{"content": "You are a helpful assistant."}]
        inference_config = {"temperature": 0.7, "top_p": 0.9}
        tool_config = {"tool_choice": "auto"}

        # Act
        result = NovaAdapter.to_invoke_model_input(
            modelId=model_id, messages=messages, system=system, inferenceConfig=inference_config, toolConfig=tool_config
        )

        # Assert
        assert isinstance(result, dict)
        assert result["messages"] == messages
        assert result["system"] == system
        assert result["inferenceConfig"] == inference_config
        assert result["toolConfig"] == tool_config

    def test_to_invoke_model_input_with_system_and_inference_config(self):
        """
        Test to_invoke_model_input with system and inferenceConfig provided, but without toolConfig.
        """
        # Arrange
        model_id = "test_model"
        messages = [{"role": "user", "content": "Hello"}]
        system = [{"content": "You are a helpful assistant."}]
        inference_config = {"temperature": 0.7, "top_p": 0.9}

        # Act
        result = NovaAdapter.to_invoke_model_input(
            modelId=model_id, messages=messages, system=system, inferenceConfig=inference_config
        )

        # Assert
        assert isinstance(result, dict)
        assert "messages" in result
        assert result["messages"] == messages
        assert "system" in result
        assert result["system"] == system
        assert "inferenceConfig" in result
        assert result["inferenceConfig"] == inference_config
        assert "toolConfig" not in result

    def test_to_invoke_model_input_with_system_and_toolconfig(self):
        """
        Test to_invoke_model_input with system and toolConfig parameters.
        """
        # Arrange
        model_id = "test_model"
        messages = [{"role": "user", "content": "Hello"}]
        system = [{"content": "You are a helpful assistant."}]
        tool_config = {"enabled": True}

        # Act
        result = NovaAdapter.to_invoke_model_input(
            modelId=model_id, messages=messages, system=system, toolConfig=tool_config
        )

        # Assert
        assert isinstance(result, dict)
        assert "messages" in result
        assert result["messages"] == messages
        assert "system" in result
        assert result["system"] == system
        assert "toolConfig" in result
        assert result["toolConfig"] == tool_config
        assert "inferenceConfig" not in result
