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


class NovaAdapter(ModelAdapter):
    """
    Convert from Converse API input to Amazon Nova API.
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
        nova_request = {
            "messages": messages,
        }

        if system:
            nova_request["system"] = system

        if inferenceConfig:
            nova_request["inferenceConfig"] = inferenceConfig

        if toolConfig:
            nova_request["toolConfig"] = toolConfig

        return nova_request

    @staticmethod
    def parse_model_response(response: dict) -> ModelResponse:
        if not isinstance(response, dict):
            raise AttributeError(f"Response is not a dict: {response}")
        return response
