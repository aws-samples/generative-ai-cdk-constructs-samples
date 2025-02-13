#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from abc import ABC, abstractmethod
from typing import Sequence, Mapping, Any, Union, TYPE_CHECKING, TypedDict, NotRequired


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
        TokenUsageTypeDef,
        ConverseOutputTypeDef,
    )
    from mypy_boto3_bedrock_runtime.literals import StopReasonType


class InvokeModelInput(TypedDict):
    modelId: str
    messages: Sequence[Union["MessageTypeDef", "MessageOutputTypeDef"]]
    system: NotRequired[Sequence["SystemContentBlockTypeDef"]]
    inferenceConfig: NotRequired["InferenceConfigurationTypeDef"]
    toolConfig: NotRequired["ToolConfigurationTypeDef"]
    guardrailConfig: NotRequired["GuardrailConfigurationTypeDef"]
    additionalModelRequestFields: NotRequired[Mapping[str, Any]]
    promptVariables: NotRequired[Mapping[str, "PromptVariableValuesTypeDef"]]
    additionalModelResponseFieldPaths: NotRequired[Sequence[str]]
    requestMetadata: NotRequired[Mapping[str, str]]
    performanceConfig: NotRequired["PerformanceConfigurationTypeDef"]


class ModelResponse(TypedDict):
    output: "ConverseOutputTypeDef"
    stopReason: "StopReasonType"
    usage: "TokenUsageTypeDef"


class ModelAdapter(ABC):
    """
    Bedrock Batch Inference uses the API for each model. The ModelAdapter classes convert from the Converse API input
    into the API for each model.
    """

    @staticmethod
    def get_adapter(model_id: str):
        if "anthropic.claude" in model_id:
            from .AnthropicClaude import ClaudeAdapter

            return ClaudeAdapter
        elif "amazon.nova" in model_id:
            from .AmazonNova import NovaAdapter

            return NovaAdapter
        else:
            raise ValueError(f"Unknown model: {model_id}")

    @staticmethod
    @abstractmethod
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
        pass

    @staticmethod
    @abstractmethod
    def parse_model_response(response: dict) -> ModelResponse:
        pass
