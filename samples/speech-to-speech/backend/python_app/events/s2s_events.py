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
import logging

# Configure logging
logger = logging.getLogger(__name__)


class S2sEvent:
    # Default configuration values
    DEFAULT_INFER_CONFIG = {"maxTokens": 1024, "topP": 0.95, "temperature": 0.7}
    # Fallback system prompt - now accepts from frontend like Java backend
    DEFAULT_SYSTEM_PROMPT = (
        "You are a friendly assistant. The user and you will engage in a spoken dialog "
        "exchanging the transcripts of a natural real-time conversation. Keep your responses short, "
        "generally two or three sentences for chatty scenarios."
    )

    DEFAULT_AUDIO_INPUT_CONFIG = {
        "mediaType": "audio/lpcm",
        "sampleRateHertz": 16000,
        "sampleSizeBits": 16,
        "channelCount": 1,
        "audioType": "SPEECH",
        "encoding": "base64",
    }
    DEFAULT_AUDIO_OUTPUT_CONFIG = {
        "mediaType": "audio/lpcm",
        "sampleRateHertz": 24000,
        "sampleSizeBits": 16,
        "channelCount": 1,
        "voiceId": "amy",
        "encoding": "base64",
        "audioType": "SPEECH",
    }
    DEFAULT_TOOL_CONFIG = {
        "tools": [
            {
                "toolSpec": {
                    "name": "getDateAndTimeTool",
                    "description": "Get information about the current date and time",
                    "inputSchema": {
                        "json": """{
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "type": "object",
                            "properties": {},
                            "required": []
                        }"""
                    },
                }
            },
            {
                "toolSpec": {
                    "name": "getWeatherTool",
                    "description": "Get weather information for a specific location",
                    "inputSchema": {
                        "json": """{
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "type": "object",
                            "properties": {
                                "latitude": {
                                    "type": "number",
                                    "description": "Latitude coordinate of the location"
                                },
                                "longitude": {
                                    "type": "number",
                                    "description": "Longitude coordinate of the location"
                                }
                            },
                            "required": ["latitude", "longitude"]
                        }"""
                    },
                }
            },
        ]
    }

    @staticmethod
    def session_start(inference_config=DEFAULT_INFER_CONFIG):
        return {"event": {"sessionStart": {"inferenceConfiguration": inference_config}}}

    @staticmethod
    def prompt_start(
        prompt_name,
        audio_output_config=DEFAULT_AUDIO_OUTPUT_CONFIG,
        tool_config=DEFAULT_TOOL_CONFIG,
    ):
        return {
            "event": {
                "promptStart": {
                    "promptName": prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": audio_output_config,
                    "toolUseOutputConfiguration": {"mediaType": "application/json"},
                    "toolConfiguration": tool_config,
                }
            }
        }

    @staticmethod
    def content_start_text(prompt_name, content_name):
        return {
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "type": "TEXT",
                    "interactive": True,
                    "role": "SYSTEM",
                    "textInputConfiguration": {"mediaType": "text/plain"},
                }
            }
        }

    @staticmethod
    def text_input(prompt_name, content_name, system_prompt):
        """Create a text input event with the provided system prompt.

        Note: System prompt now comes from frontend (like Java backend) rather than hardcoded default.
        """
        return {
            "event": {
                "textInput": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": system_prompt,
                }
            }
        }

    @staticmethod
    def content_end(prompt_name, content_name):
        return {
            "event": {
                "contentEnd": {"promptName": prompt_name, "contentName": content_name}
            }
        }

    @staticmethod
    def content_start_audio(
        prompt_name, content_name, audio_input_config=DEFAULT_AUDIO_INPUT_CONFIG
    ):
        return {
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "type": "AUDIO",
                    "interactive": True,
                    "audioInputConfiguration": audio_input_config,
                }
            }
        }

    @staticmethod
    def audio_input(prompt_name, content_name, content):
        return {
            "event": {
                "audioInput": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": content,
                }
            }
        }

    @staticmethod
    def content_start_tool(prompt_name, content_name, tool_use_id):
        return {
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "interactive": False,
                    "type": "TOOL",
                    "role": "TOOL",
                    "toolResultInputConfiguration": {
                        "toolUseId": tool_use_id,
                        "type": "TEXT",
                        "textInputConfiguration": {"mediaType": "text/plain"},
                    },
                }
            }
        }

    @staticmethod
    def text_input_tool(prompt_name, content_name, content):
        return {
            "event": {
                "toolResult": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": content,
                    # "role": "TOOL"
                }
            }
        }

    @staticmethod
    def prompt_end(prompt_name):
        return {"event": {"promptEnd": {"promptName": prompt_name}}}

    @staticmethod
    def session_end():
        return {"event": {"sessionEnd": {}}}
