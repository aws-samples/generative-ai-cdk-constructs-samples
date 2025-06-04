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

import json
import urllib.request
from typing import Dict, Any
from .base_tool import BaseTool


class WeatherTool(BaseTool):
    """Tool for getting weather information for specific locations."""

    @property
    def name(self) -> str:
        """Return the tool name that matches Nova Sonic configuration."""
        return "getWeatherTool"

    @property
    def display_name(self) -> str:
        """Return human-readable display name."""
        return "Weather Tool"

    async def execute(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the weather tool.

        Args:
            tool_use_content: Tool use content containing latitude and longitude

        Returns:
            Dict containing weather data or error information
        """
        try:
            self.logger.info("Processing weather request")

            # Extract and validate coordinates
            query_json = self._extract_content(tool_use_content)
            latitude = query_json.get("latitude")
            longitude = query_json.get("longitude")

            # Convert to float if they're strings
            if isinstance(latitude, str):
                latitude = float(latitude)
            if isinstance(longitude, str):
                longitude = float(longitude)

            if latitude is None or longitude is None:
                raise ValueError("Missing latitude or longitude parameters")

            # Validate coordinate ranges
            if not (-90 <= latitude <= 90):
                raise ValueError(
                    f"Invalid latitude: {latitude}. Must be between -90 and 90"
                )
            if not (-180 <= longitude <= 180):
                raise ValueError(
                    f"Invalid longitude: {longitude}. Must be between -180 and 180"
                )

            # Fetch weather data
            weather_data = await self._fetch_weather_data(latitude, longitude)
            result = {"weather_data": weather_data}

            self.logger.info(
                f"Weather data retrieved for lat:{latitude}, lon:{longitude}"
            )
            return self._create_success_result(result)

        except ValueError as e:
            error_msg = f"Invalid parameters: {str(e)}"
            self.logger.error(error_msg)
            return self._create_error_result(error_msg)
        except Exception as e:
            error_msg = f"Failed to fetch weather data: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return self._create_error_result(error_msg)

    async def _fetch_weather_data(
        self, latitude: float, longitude: float
    ) -> Dict[str, Any]:
        """Fetch weather data from Open-Meteo API.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            Weather data dictionary

        Raises:
            Exception: If weather data cannot be fetched
        """
        self.logger.info(f"Fetching weather for lat:{latitude}, lon:{longitude}")
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"

        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data
        except urllib.error.URLError as e:
            raise Exception(f"Network error accessing weather API: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid response from weather API: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error fetching weather data: {str(e)}")
