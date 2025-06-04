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
import logging
from typing import Dict, Any, Optional, Callable, Awaitable


class MessageRouter:
    """Routes and processes WebSocket messages based on event types."""

    def __init__(self, session_id: str):
        """Initialize the message router.

        Args:
            session_id: Unique session identifier for logging
        """
        self.session_id = session_id
        self.logger = logging.getLogger(f"MessageRouter[{session_id}]")
        self.handlers: Dict[str, Callable] = {}
        self.frontend_system_prompt: Optional[str] = None

    def register_handler(
        self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """Register a handler for a specific event type.

        Args:
            event_type: Type of event to handle
            handler: Async function to handle the event
        """
        self.handlers[event_type] = handler
        self.logger.debug(f"Registered handler for event type: {event_type}")

    async def route_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Route a WebSocket message to the appropriate handler.

        Args:
            message: Raw WebSocket message

        Returns:
            Processed message data or None if consumed by handler
        """
        try:
            data = self._parse_message(message)
            if not data:
                return None

            event_type = self._extract_event_type(data)
            if not event_type:
                self.logger.warning("Message missing event type")
                return data

            # Handle system prompt capture
            if event_type == "textInput":
                await self._handle_system_prompt(data)
                return data  # Continue processing

            # Check for registered handler
            if event_type in self.handlers:
                await self.handlers[event_type](data)
                return None  # Message consumed by handler

            return data  # Return for default processing

        except Exception as e:
            self.logger.error(f"Error routing message: {str(e)}", exc_info=True)
            return None

    def get_system_prompt(self) -> Optional[str]:
        """Get the captured system prompt from frontend.

        Returns:
            System prompt string or None if not captured
        """
        return self.frontend_system_prompt

    def _parse_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse WebSocket message from JSON.

        Args:
            message: Raw message string

        Returns:
            Parsed message data or None if invalid
        """
        try:
            data = json.loads(message)

            # Handle nested body structure
            if "body" in data:
                data = json.loads(data["body"])

            return data

        except json.JSONDecodeError:
            self.logger.error("Invalid JSON received")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing message: {str(e)}")
            return None

    def _extract_event_type(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract event type from message data.

        Args:
            data: Parsed message data

        Returns:
            Event type string or None if not found
        """
        if not isinstance(data, dict) or "event" not in data:
            return None

        event = data["event"]
        if not isinstance(event, dict):
            return None

        # Get the first key as event type
        event_keys = list(event.keys())
        return event_keys[0] if event_keys else None

    async def _handle_system_prompt(self, data: Dict[str, Any]):
        """Handle system prompt capture from textInput events.

        Args:
            data: Message data containing textInput event
        """
        try:
            text_input = data.get("event", {}).get("textInput", {})
            content = text_input.get("content")

            if content:
                self.frontend_system_prompt = content
                self.logger.info(
                    f"Captured system prompt from frontend: {content[:100]}..."
                )

        except Exception as e:
            self.logger.error(f"Error handling system prompt: {str(e)}")
