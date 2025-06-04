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
import logging
from typing import Optional
from events.s2s_events import S2sEvent


class AudioProcessor:
    """Handles audio input processing and queuing for Nova Sonic streams."""

    def __init__(self, session_id: str):
        """Initialize the audio processor.

        Args:
            session_id: Unique session identifier for logging
        """
        self.session_id = session_id
        self.logger = logging.getLogger(f"AudioProcessor[{session_id}]")
        self.audio_input_queue = asyncio.Queue()
        self.is_active = False
        self.processing_task: Optional[asyncio.Task] = None

    async def start(self, bedrock_client, stream):
        """Start the audio processing loop.

        Args:
            bedrock_client: Bedrock client instance
            stream: Bedrock stream instance
        """
        if self.is_active:
            self.logger.warning("Audio processor already active")
            return

        self.is_active = True
        self.bedrock_client = bedrock_client
        self.stream = stream

        # Start the processing task
        self.processing_task = asyncio.create_task(self._process_audio_loop())
        self.logger.info("Audio processor started")

    async def stop(self):
        """Stop the audio processing loop."""
        if not self.is_active:
            return

        self.is_active = False

        # Cancel the processing task
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Audio processor stopped")

    async def queue_audio(self, prompt_name: str, content_name: str, audio_base64: str):
        """Queue audio data for processing.

        Args:
            prompt_name: Name of the prompt
            content_name: Name of the content
            audio_base64: Base64 encoded audio data
        """
        if not self.is_active:
            self.logger.warning(
                "Cannot queue audio - processor not active (check Bedrock stream initialization)"
            )
            return

        # Use put_nowait() like original code to avoid blocking/timing delays
        self.audio_input_queue.put_nowait(
            {
                "prompt_name": prompt_name,
                "content_name": content_name,
                "audio_bytes": audio_base64,
            }
        )

    async def _process_audio_loop(self):
        """Main audio processing loop."""
        self.logger.info("Starting audio input processing")

        while self.is_active:
            try:
                # Get audio data from the queue
                data = await self.audio_input_queue.get()

                # Extract data from the queue item
                prompt_name = data.get("prompt_name")
                content_name = data.get("content_name")
                audio_bytes = data.get("audio_bytes")

                if not audio_bytes or not prompt_name or not content_name:
                    self.logger.warning("Missing required audio data properties")
                    continue

                # Create the audio input event
                audio_event = S2sEvent.audio_input(
                    prompt_name, content_name, audio_bytes
                )

                # Send the event to Bedrock - match original timing by removing success check
                await self.bedrock_client.send_event(self.stream, audio_event)

            except asyncio.CancelledError:
                self.logger.info("Audio processing task cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error processing audio: {str(e)}", exc_info=True)

        self.logger.info("Audio processing loop ended")
