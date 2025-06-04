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

from datetime import datetime, timezone, date
from typing import Dict, Any
from .base_tool import BaseTool


class DateTimeTool(BaseTool):
    """Tool for getting current date and time information."""

    @property
    def name(self) -> str:
        """Return the tool name that matches Nova Sonic configuration."""
        return "getDateAndTimeTool"

    @property
    def display_name(self) -> str:
        """Return human-readable display name."""
        return "Date and Time Tool"

    async def execute(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the date/time tool.

        Args:
            tool_use_content: Tool use content (not used for this tool)

        Returns:
            Dict containing current date and time information
        """
        try:
            self.logger.info("Processing date and time request")

            # Get current date and time
            current_date = date.today()
            current_time = datetime.now(timezone.utc).astimezone(
                tz=timezone(offset=datetime.now().astimezone().utcoffset())
            )

            # Build result
            result = {
                "date": current_date.isoformat(),
                "year": current_date.year,
                "month": current_date.month,
                "day": current_date.day,
                "dayOfWeek": current_date.strftime("%A"),
                "timezone": "PST",  # Can be made configurable if needed
                "formattedTime": current_time.strftime("%H:%M"),
            }

            self.logger.info(
                f"Date/time result: {result['date']} {result['formattedTime']}"
            )
            return self._create_success_result(result)

        except Exception as e:
            error_msg = f"Failed to get date/time: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return self._create_error_result(error_msg)
