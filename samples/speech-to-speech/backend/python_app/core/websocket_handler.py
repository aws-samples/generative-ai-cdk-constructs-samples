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

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional

from clients.bedrock_client import BedrockInteractClient
from clients.cognito_validator import CognitoTokenValidator
from events.s2s_events import S2sEvent
from .audio_processor import AudioProcessor
from .message_router import MessageRouter
from tools.datetime_tool import DateTimeTool
from tools.weather_tool import WeatherTool
from tools.base_tool import BaseTool


class WebSocketHandler:
    """Main WebSocket handler using refactored architecture."""

    def __init__(self, model_id="amazon.nova-sonic-v1:0", region="us-east-1"):
        """Initialize the WebSocket handler.

        Args:
            model_id (str): Bedrock model ID to use
            region (str): AWS region for Bedrock
        """
        self.session_id = str(uuid.uuid4())[:8]
        self.logger = logging.getLogger(f"WebSocketHandler[{self.session_id}]")

        # Create clients
        self.bedrock_client = BedrockInteractClient(model_id=model_id, region=region)
        self.token_validator = CognitoTokenValidator()

        # Create core components
        self.audio_processor = AudioProcessor(self.session_id)
        self.message_router = MessageRouter(self.session_id)

        # Initialize tools
        self.tools: Dict[str, BaseTool] = {
            "getDateAndTimeTool": DateTimeTool(self.session_id),
            "getdateandtimetool": DateTimeTool(self.session_id),  # Case variations
            "getWeatherTool": WeatherTool(self.session_id),
            "getweathertool": WeatherTool(self.session_id),  # Case variations
        }

        # Initialize state
        self.stream = None
        self.is_authenticated = False
        self.is_active = False
        self.response_task: Optional[asyncio.Task] = None

        # Barge-in support - track user interruption
        self.barge_in = False
        self.audio_output_queue = asyncio.Queue()  # For tracking audio output

        # Session information
        self.prompt_name = None
        self.content_name = None
        self.audio_content_name = None
        self.tool_use_content = ""
        self.tool_use_id = ""
        self.tool_name = ""

        self.logger.info("WebSocket handler initialized")

    async def handle_connection(self, websocket):
        """Main handler for a WebSocket connection.

        Args:
            websocket: WebSocket connection to handle
        """
        try:
            # Authenticate first
            if not await self._authenticate(websocket):
                return

            # Initialize Bedrock stream
            try:
                self.stream = await self.bedrock_client.create_stream()
                self.is_active = True
                self.logger.info("Bedrock stream created successfully")
            except Exception as e:
                error_msg = str(e)
                if (
                    "ExpiredTokenException" in error_msg
                    or "InvalidTokenException" in error_msg
                ):
                    self.logger.error(f"AWS credential error: {error_msg}")
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "error",
                                "message": "AWS credential issue - please check ECS task role permissions",
                            }
                        )
                    )
                else:
                    self.logger.error(f"Failed to create Bedrock stream: {error_msg}")
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "error",
                                "message": "Failed to initialize Bedrock service",
                            }
                        )
                    )
                return

            # Start audio processor
            await self.audio_processor.start(self.bedrock_client, self.stream)

            # Register message handlers
            self._register_message_handlers()

            # Start response processing task AFTER setup is complete 
            self.response_task = asyncio.create_task(self._process_responses(websocket))

            # Main message processing loop
            async for message in websocket:
                await self._handle_message(websocket, message)

        except Exception as e:
            self.logger.error(f"WebSocket handler error: {str(e)}", exc_info=True)
        finally:
            await self._cleanup()

    async def _authenticate(self, websocket) -> bool:
        """Handle WebSocket authentication.

        Args:
            websocket: WebSocket connection

        Returns:
            True if authenticated successfully, False otherwise
        """
        auth_attempt_count = 0
        while auth_attempt_count < 3 and not self.is_authenticated:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(message)

                if "type" in data and data["type"] == "authorization":
                    token = data.get("token", "")
                    token = token[7:] if token.startswith("Bearer ") else token
                    self.is_authenticated = await self.token_validator.validate_token(
                        token
                    )

                    if self.is_authenticated:
                        self.logger.info("Authentication successful")
                        await websocket.send(
                            json.dumps({"type": "authorization", "status": "success"})
                        )
                        return True
                    else:
                        self.logger.warning("Authentication failed")
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "authorization",
                                    "status": "error",
                                    "message": "Invalid token",
                                }
                            )
                        )
                else:
                    self.logger.warning(
                        f"Expected authorization message, got: {data.get('type', 'unknown')}"
                    )
                    await websocket.send(
                        json.dumps(
                            {"type": "error", "message": "Authentication required"}
                        )
                    )

                auth_attempt_count += 1

            except asyncio.TimeoutError:
                self.logger.warning("Authentication timeout")
                await websocket.send(
                    json.dumps({"type": "error", "message": "Authentication timeout"})
                )
                return False
            except Exception as e:
                self.logger.error(f"Error during authentication: {str(e)}")
                return False

        if not self.is_authenticated:
            self.logger.error(
                f"Authentication failed after {auth_attempt_count} attempts"
            )
            await websocket.send(
                json.dumps({"type": "error", "message": "Authentication failed"})
            )
            return False

        return True

    def _register_message_handlers(self):
        """Register message handlers with the message router."""
        self.message_router.register_handler("audioInput", self._handle_audio_input)
        self.message_router.register_handler("sessionEnd", self._handle_session_end)

    async def _handle_message(self, websocket, message):
        """Handle a WebSocket message using the message router.

        Args:
            websocket: WebSocket connection
            message: Message received from the client
        """
        try:
            # Route message through message router
            data = await self.message_router.route_message(message)

            if data is None:
                # Message was consumed by a handler
                return

            # Extract event type for session tracking
            event_type = (
                list(data.get("event", {}).keys())[0] if "event" in data else None
            )

            # Event sequence tracking (reduced verbosity)
            if event_type:
                if event_type == "sessionStart":
                    self.logger.info("Session started")
                elif event_type == "promptStart":
                    self.prompt_name = data["event"]["promptStart"]["promptName"]
                    self.logger.debug("Prompt started")
                elif event_type == "contentStart":
                    content_type = data["event"]["contentStart"].get("type")
                    role = data["event"]["contentStart"].get("role", "UNSPECIFIED")
                    content_name = data["event"]["contentStart"].get("contentName")
                    
                    # Only log at debug level for routine content
                    self.logger.debug(f"Content start: type={content_type}, role={role}")
                    
                    # Validate first content block has SYSTEM role
                    if not hasattr(self, '_first_content_received'):
                        self._first_content_received = True
                        if role != "SYSTEM":
                            self.logger.error(f"First content block must have SYSTEM role, received {role}")
                            await websocket.send(json.dumps({
                                "type": "error",
                                "message": f"First content block must have SYSTEM role, received {role}"
                            }))
                    
                    # Store audio content name
                    if content_type == "AUDIO":
                        self.audio_content_name = content_name
                        if role != "USER":
                            self.logger.warning(f"Audio content should have USER role, received {role}")
                            
                elif event_type == "sessionEnd":
                    self.logger.info("Session ended")
                # Other events logged at debug level only
                elif event_type in ["textInput", "contentEnd", "promptEnd"]:
                    self.logger.debug(f"Event: {event_type}")

            # Send event to Bedrock
            await self.bedrock_client.send_event(self.stream, data)

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}", exc_info=True)

    async def _handle_audio_input(self, data: Dict[str, Any]):
        """Handle audio input events.

        Args:
            data: Audio input event data
        """
        try:
            audio_input = data["event"]["audioInput"]
            prompt_name = audio_input["promptName"]
            content_name = audio_input["contentName"]
            audio_base64 = audio_input["content"]

            # Queue audio for processing
            await self.audio_processor.queue_audio(
                prompt_name, content_name, audio_base64
            )

        except Exception as e:
            self.logger.error(f"Error handling audio input: {str(e)}", exc_info=True)

    async def _handle_session_end(self, data: Dict[str, Any]):
        """Handle session end events.

        Args:
            data: Session end event data
        """
        self.logger.info("Session end event received")
        await self._cleanup()

    async def _process_responses(self, websocket):
        """Process responses from Bedrock and send to WebSocket.

        Args:
            websocket: WebSocket connection to send responses to
        """
        self.logger.info("Starting response processing")
        while self.is_active:
            try:
                # Get next response from the stream
                try:
                    output = await self.stream.await_output()
                    result = await output[1].receive()
                except Exception as e:
                    # Check if this is an expired token exception
                    error_msg = str(e)
                    if "ExpiredToken" in error_msg:
                        self.logger.warning(f"Token expired during stream processing: {error_msg}")
                        
                        # Try to refresh credentials and recreate the stream
                        if await self.bedrock_client.refresh_credentials_immediately():
                            self.logger.info("Successfully refreshed credentials, recreating stream...")
                            
                            # Recreate the stream
                            try:
                                # Close old stream if it exists
                                if self.stream:
                                    try:
                                        await self.bedrock_client.close_stream(self.stream)
                                    except:
                                        pass
                                
                                # Create new stream
                                self.stream = await self.bedrock_client.create_stream()
                                self.logger.info("Stream recreated successfully after token refresh")
                                
                                # Restart audio processor with new stream
                                await self.audio_processor.stop()
                                await self.audio_processor.start(self.bedrock_client, self.stream)
                                
                                # Send notification to client
                                await websocket.send(json.dumps({
                                    "type": "notification",
                                    "message": "Connection refreshed due to credential expiration"
                                }))
                                
                                # Continue processing
                                continue
                            except Exception as e2:
                                self.logger.error(f"Failed to recreate stream after token refresh: {str(e2)}")
                    
                    # If we get here, either it wasn't a token error or refresh failed
                    raise
                
                if result.value and result.value.bytes_:
                    response_data = result.value.bytes_.decode("utf-8")
                    json_data = json.loads(response_data)

                    event_name = None
                    if "event" in json_data:
                        event_name = list(json_data["event"].keys())[0]

                        # Handle barge-in detection - check for interrupt signal in textOutput
                        if event_name == "textOutput":
                            text_content = json_data["event"]["textOutput"].get(
                                "content", ""
                            )
                            # Check if there is a barge-in signal from Nova Sonic
                            if '{ "interrupted" : true }' in text_content:
                                self.logger.info(
                                    "Barge-in detected. Stopping audio output."
                                )
                                self.barge_in = True
                                # Clear any queued audio output
                                await self._clear_audio_output_queue()

                        # Handle tool use detection
                        elif event_name == "toolUse":
                            self.tool_use_content = json_data["event"]["toolUse"]
                            self.tool_name = json_data["event"]["toolUse"]["toolName"]
                            self.tool_use_id = json_data["event"]["toolUse"][
                                "toolUseId"
                            ]
                            self.logger.info(f"Tool use detected: {self.tool_name}")

                        # Process tool use when content ends
                        elif (
                            event_name == "contentEnd"
                            and json_data["event"][event_name].get("type") == "TOOL"
                        ):
                            await self._handle_tool_use(
                                json_data["event"]["contentEnd"].get("promptName")
                            )

                        # Handle audio output - track it for barge-in clearing
                        elif event_name == "audioOutput":
                            audio_content = json_data["event"]["audioOutput"].get(
                                "content", ""
                            )
                            if audio_content:
                                # Add to our output queue for potential clearing on barge-in
                                try:
                                    self.audio_output_queue.put_nowait(audio_content)
                                except asyncio.QueueFull:
                                    # Queue is full, that's ok - just continue
                                    pass

                    # Send response to WebSocket
                    try:
                        event = json.dumps(json_data)
                        await websocket.send(event)
                    except Exception as e:
                        self.logger.error(f"Error sending to WebSocket: {str(e)}")
                        break

            except json.JSONDecodeError as ex:
                self.logger.error(f"JSON decode error: {str(ex)}")
            except StopAsyncIteration:
                self.logger.info("Stream ended")
                break
            except asyncio.CancelledError:
                self.logger.info("Response task cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error processing response: {str(e)}", exc_info=True)
                break

        # Clean up if we exit the loop
        await self._cleanup()

    async def _clear_audio_output_queue(self):
        """Clear the audio output queue when barge-in is detected."""
        cleared_count = 0
        while not self.audio_output_queue.empty():
            try:
                self.audio_output_queue.get_nowait()
                cleared_count += 1
            except asyncio.QueueEmpty:
                break

        if cleared_count > 0:
            self.logger.info(
                f"Cleared {cleared_count} audio output items due to barge-in"
            )

        # Reset barge-in flag after clearing
        self.barge_in = False

    async def _handle_tool_use(self, prompt_name: str):
        """Handle a tool use request using the tool architecture.

        Args:
            prompt_name: Name of the prompt
        """
        try:
            self.logger.info(f"Processing tool use for {self.tool_name}")

            # Find the appropriate tool
            tool = self.tools.get(self.tool_name.lower()) or self.tools.get(
                self.tool_name
            )

            if tool:
                # Execute the tool
                tool_result = await tool.execute(self.tool_use_content)
            else:
                self.logger.warning(f"No handler for tool: {self.tool_name}")
                tool_result = {"result": f"Tool '{self.tool_name}' not supported"}

            # Send tool result to Bedrock
            await self._send_tool_result(prompt_name, tool_result)

        except Exception as e:
            self.logger.error(f"Error handling tool use: {str(e)}", exc_info=True)
            # Send error result
            error_result = {"error": f"Tool execution failed: {str(e)}"}
            await self._send_tool_result(prompt_name, error_result)

    async def _send_tool_result(self, prompt_name: str, tool_result: Dict[str, Any]):
        """Send tool result back to Bedrock.

        Args:
            prompt_name: Name of the prompt
            tool_result: Result from tool execution
        """
        try:
            # Send tool start event
            tool_content = str(uuid.uuid4())
            tool_start_event = S2sEvent.content_start_tool(
                prompt_name, tool_content, self.tool_use_id
            )
            await self.bedrock_client.send_event(self.stream, tool_start_event)

            # Send tool result event
            if isinstance(tool_result, dict):
                content_json_string = json.dumps(tool_result)
            else:
                content_json_string = str(tool_result)

            tool_result_event = S2sEvent.text_input_tool(
                prompt_name, tool_content, content_json_string
            )
            await self.bedrock_client.send_event(self.stream, tool_result_event)

            # Send tool content end event
            tool_content_end_event = S2sEvent.content_end(prompt_name, tool_content)
            await self.bedrock_client.send_event(self.stream, tool_content_end_event)

        except Exception as e:
            self.logger.error(f"Error sending tool result: {str(e)}", exc_info=True)

    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up resources")
        if not self.is_active:
            return

        self.is_active = False

        # Stop audio processor
        await self.audio_processor.stop()

        # Close Bedrock stream
        if self.stream:
            await self.bedrock_client.close_stream(self.stream)

        # Cancel response task
        if self.response_task and not self.response_task.done():
            self.response_task.cancel()
            try:
                await self.response_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Cleanup complete")
