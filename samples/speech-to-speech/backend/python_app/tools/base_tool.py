#!/usr/bin/env python3
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

from abc import ABC, abstractmethod
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for all speech-to-speech tools."""

    def __init__(self, session_id: str):
        """Initialize the tool with session context.

        Args:
            session_id: Unique session identifier for logging
        """
        self.session_id = session_id
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{session_id}]")

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool name that matches the Nova Sonic tool configuration."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return a human-readable display name for logging."""
        pass

    @abstractmethod
    async def execute(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided content.

        Args:
            tool_use_content: Tool use content from Nova Sonic

        Returns:
            Dict containing the tool result
        """
        pass

    def _extract_content(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and parse content from tool use.

        Args:
            tool_use_content: Raw tool use content

        Returns:
            Parsed content as dictionary
        """
        import json

        if not isinstance(tool_use_content, dict):
            return {}

        content = tool_use_content.get("content")
        if not content:
            return {}

        try:
            if isinstance(content, str):
                return json.loads(content)
            return content if isinstance(content, dict) else {}
        except json.JSONDecodeError:
            self.logger.warning("Content is not valid JSON")
            return {}

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error result.

        Args:
            error_message: Error description

        Returns:
            Error result dictionary
        """
        return {"error": f"Tool '{self.display_name}' error: {error_message}"}

    def _create_success_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a standardized success result.

        Args:
            data: Result data

        Returns:
            Success result dictionary
        """
        return data
