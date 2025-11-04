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
Application Properties Manager for Lambda functions using AWS Lambda Powertools Parameters.
Provides hierarchical parameter lookup with function-specific overrides.
"""

import os
from typing import Optional
from aws_lambda_powertools.utilities.parameters import get_parameter
from aws_lambda_powertools.utilities.parameters.exceptions import (
    GetParameterError,
    TransformParameterError,
)
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

# Initialize Powertools logger with shared service name
logger = Logger(service="contract-compliance-analysis")

class AppPropertiesManager:
    """Manages application properties retrieval from AWS Systems Manager Parameter Store."""

    def __init__(self, cache_ttl: int = 30):
        """
        Initialize AppPropertiesManager.

        Args:
            cache_ttl: Cache TTL in seconds (default: 30 seconds)
        """
        self.cache_ttl = cache_ttl

    # Helper to decide when it's *specifically* a "not found" case
    @staticmethod
    def _param_not_found(exc: BaseException) -> bool:
        cause = getattr(exc, "__cause__", None)
        if isinstance(cause, ClientError):
            code = cause.response.get("Error", {}).get("Code")
            return code in ("ParameterNotFound", "ParameterVersionNotFound")
        msg = str(exc)
        return ("ParameterNotFound" in msg) or ("ParameterVersionNotFound" in msg)

    def get_parameter(self, parameter_name: str, task_name: Optional[str] = None,
                      default: Optional[str] = None) -> str:
        """
        Get configuration parameter with simplified hierarchical fallback.

        Simplified priority order (no contract type overrides):
        1. /ContractAnalysis/{task_name}/{parameter_name} (if task_name provided)
        2. /ContractAnalysis/{parameter_name}
        3. default value

        Args:
            parameter_name: Parameter name in PascalCase (e.g., 'LanguageModelId')
            task_name: Optional task name for overrides
            default: Optional default value if parameter not found

        Returns:
            Parameter value as string

        Raises:
            ValueError: If parameter is not found and no default provided
        """

        logger.info(f"Getting parameter: {parameter_name}", extra={
            "parameter_name": parameter_name,
            "task_name": task_name,
            "has_default": default is not None
        })

        # Try task-specific parameter first (only if task_name provided)
        if task_name:
            param_path = f'/ContractAnalysis/{task_name}/{parameter_name}'
            logger.debug(f"Trying task-specific parameter: {param_path}")
            try:
                value = get_parameter(param_path, max_age=self.cache_ttl)
                logger.info(f"Found task-specific parameter: {param_path}")
                return value
            except (GetParameterError, TransformParameterError) as e:
                if self._param_not_found(e):
                    logger.info(f"Task-specific parameter not found: {param_path}")
                else:
                    logger.exception(f"Error fetching task-specific parameter: {param_path}")
                    raise

        # Try global parameter
        param_path = f'/ContractAnalysis/{parameter_name}'
        logger.debug(f"Trying global parameter: {param_path}")
        try:
            value = get_parameter(param_path, max_age=self.cache_ttl)
            logger.info(f"Found global parameter: {param_path}")
            return value
        except (GetParameterError, TransformParameterError) as e:
            if self._param_not_found(e):
                logger.info(f"Global parameter not found: {param_path}")
            else:
                logger.exception(f"Error fetching global parameter: {param_path}")
                raise

        # Finally use caller-provided default
        if default is not None:
            logger.info(f"Using caller-provided default for parameter: {parameter_name}")
            return default

        logger.error(f"Parameter not found: {parameter_name}")
        raise ValueError(f"Parameter '{parameter_name}' not found in Parameter Store")


