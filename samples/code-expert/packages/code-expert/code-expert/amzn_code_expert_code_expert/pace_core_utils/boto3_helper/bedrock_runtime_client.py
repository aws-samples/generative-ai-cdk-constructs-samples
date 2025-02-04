# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

from typing import TYPE_CHECKING, Unpack

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.ConverseToBatch import InvokeModelInput
from amzn_code_expert_code_expert.pace_core_utils.exceptions import RateLimitError, RetryableError

if TYPE_CHECKING:
    # mypy_boto3_* is a test-dependency only and not available at runtime
    # It is also only ever used as type-hints, so we can import it during TYPE_CHECKING only
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient
    from mypy_boto3_bedrock_runtime.type_defs import ConverseResponseTypeDef


def handle_bedrock_errors(func):
    """
    Decorator to convert boto3 Bedrock errors into our exceptions.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if hasattr(e, "response"):
                if e.response["Error"]["Code"] == "ThrottlingException":
                    print(e.response["Error"]["Code"])
                    raise RateLimitError(e)
                elif e.response["Error"]["Code"] in (
                    "ModelTimeoutException",
                    "InternalServerException",
                    "ServiceUnavailableException",
                ):
                    print(e)
                    raise RetryableError(e)
                else:
                    raise e
            else:
                raise e

    return wrapper


def retry_bedrock_errors(func):
    """
    Decorator to retry function calls up to 10 times on RateLimitError and 3 times on RetryableError.
    """

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(10),
        wait=wait_random_exponential(multiplier=2, max=60, min=30),
        reraise=True,
    )
    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=2, max=60),
        reraise=True,
    )
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


@handle_bedrock_errors
def invoke_model_with_input(
    bedrock_runtime: "BedrockRuntimeClient", **input: Unpack[InvokeModelInput]
) -> "ConverseResponseTypeDef":
    """
    Invoke a model with the given input

    Args:
        bedrock_runtime: The Bedrock runtime client.
        input: The input schema for the model.


    Returns:
        The output of the model.

    Raises:
        ModelResponseError: If the model does not return a structured output with tool use.
    """
    return bedrock_runtime.converse(**input)


@retry_bedrock_errors
def invoke_model_with_input_retry(
    bedrock_runtime: "BedrockRuntimeClient", **input: Unpack[InvokeModelInput]
) -> "ConverseResponseTypeDef":
    """
    Invoke a model with the given input

    Args:
        bedrock_runtime: The Bedrock runtime client.
        input: The input schema for the model.


    Returns:
        The output of the model.

    Raises:
        ModelResponseError: If the model does not return a structured output with tool use.
    """
    return invoke_model_with_input(bedrock_runtime, **input)
