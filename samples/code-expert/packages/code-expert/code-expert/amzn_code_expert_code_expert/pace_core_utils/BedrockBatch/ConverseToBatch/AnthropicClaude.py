#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from typing import Sequence, Union, Mapping, Any, TYPE_CHECKING

from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.ConverseToBatch import ModelAdapter, ModelResponse

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


class ClaudeAdapter(ModelAdapter):
    """
    Convert from Converse API input to Anthropic Messages API.
    """

    @staticmethod
    def to_invoke_model_input(
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
    ) -> dict:
        claude_request = {"anthropic_version": "bedrock-2023-05-31"}
        if inferenceConfig:
            if inferenceConfig.get("maxTokens"):
                claude_request["max_tokens"] = inferenceConfig["maxTokens"]
            if inferenceConfig.get("temperature"):
                claude_request["temperature"] = inferenceConfig["temperature"]
            if inferenceConfig.get("topP"):
                claude_request["top_p"] = inferenceConfig["topP"]
            if inferenceConfig.get("stopSequences"):
                claude_request["stop_sequences"] = inferenceConfig["stopSequences"]

        if messages:
            claude_messages = ClaudeAdapter._convert_messages(messages)
            claude_request["messages"] = claude_messages

        if not claude_request.get("messages"):
            raise ValueError("Messages are required for this model")

        if system:
            claude_system = ClaudeAdapter._extract_system(system)
            claude_request["system"] = claude_system

        if toolConfig:
            if toolConfig.get("tools"):
                claude_tools = ClaudeAdapter._extract_tools(toolConfig)
                claude_request["tools"] = claude_tools
            if toolConfig.get("toolChoice"):
                claude_tool_choice = ClaudeAdapter._extract_tool_choice(toolConfig)
                claude_request["tool_config"] = claude_tool_choice

        # Add any additional fields
        if additionalModelRequestFields:
            claude_request.update(additionalModelRequestFields)

        return claude_request

    @staticmethod
    def _extract_tool_choice(toolConfig):
        if len(toolConfig["toolChoice"]) != 1:
            raise ValueError(f"Only one tool choice is allowed: {toolConfig['toolChoice']}")
        if toolConfig["toolChoice"].get("auto"):
            claude_tool_choice = {"type": "auto"}
        elif toolConfig["toolChoice"].get("any"):
            claude_tool_choice = {"type": "any"}
        elif toolConfig["toolChoice"].get("tool"):
            claude_tool_choice = {
                "type": "tool",
                "name": toolConfig["toolChoice"]["tool"]["name"],
            }
        else:
            raise ValueError(f"Unknown tool choice: {toolConfig['toolChoice']}")
        return claude_tool_choice

    @staticmethod
    def _extract_tools(toolConfig):
        claude_tools = []
        for tool in toolConfig["tools"]:
            t = {
                "name": tool["toolSpec"]["name"],
                "input_schema": tool["toolSpec"]["inputSchema"]["json"],
            }

            if tool["toolSpec"].get("description"):
                t["description"] = tool["toolSpec"]["description"]

            claude_tools.append(t)
        return claude_tools

    @staticmethod
    def _extract_system(system):
        claude_system = ""
        for content in system:
            if "text" in content:
                claude_system += content["text"]
            else:
                raise ValueError(f"Unknown content type: {content}")
        return claude_system

    @staticmethod
    def _convert_messages(messages):
        claude_messages = []
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise ValueError(f"Invalid message format: {msg}")
            if msg["role"] not in ["user", "assistant"]:
                raise ValueError(f"Unknown role: {msg['role']}")
            claude_msg = {"role": msg["role"], "content": []}
            for content in msg["content"]:
                if "text" in content:
                    claude_msg["content"].append({"type": "text", "text": content["text"]})
                elif "image" in content:
                    claude_msg["content"].append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": f"image/{content['image']['format']}",
                                "data": content["image"]["source"]["bytes"],
                            },
                        }
                    )
                else:
                    raise ValueError(f"Unknown content type: {content}")
            claude_messages.append(claude_msg)
        return claude_messages

    @staticmethod
    def parse_model_response(claude_response: dict) -> ModelResponse:
        converse_response: ModelResponse = {
            "output": {"message": {"role": claude_response["role"], "content": []}},
            "stopReason": claude_response["stop_reason"],
            "usage": {
                "inputTokens": claude_response["usage"]["input_tokens"],
                "outputTokens": claude_response["usage"]["output_tokens"],
                "totalTokens": claude_response["usage"]["input_tokens"] + claude_response["usage"]["output_tokens"],
            },
        }

        # Process content
        for content_item in claude_response["content"]:
            if content_item["type"] == "text":
                converse_response["output"]["message"]["content"].append({"text": content_item["text"]})
            elif content_item["type"] == "tool_use":
                converse_response["output"]["message"]["content"].append(
                    {
                        "toolUse": {
                            "toolUseId": content_item["id"],
                            "name": content_item["id"],  # Assuming the tool name is the same as the ID
                            "input": content_item["input"],
                        }
                    }
                )

        # Set stopReason
        if claude_response["stop_reason"] == "end_turn":
            converse_response["stopReason"] = "end_turn"
        elif claude_response["stop_reason"] == "max_tokens":
            converse_response["stopReason"] = "max_tokens"
        elif claude_response["stop_reason"] == "stop_sequence":
            converse_response["stopReason"] = "stop_sequence"
        elif claude_response["stop_reason"] == "tool_use":
            converse_response["stopReason"] = "tool_use"

        return converse_response
