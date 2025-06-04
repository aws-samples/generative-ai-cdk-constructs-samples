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
import warnings
import argparse
import os
from aiohttp import web, WSMsgType
from aiohttp.web_ws import WebSocketResponse

from core.websocket_handler import WebSocketHandler

# Configure logging
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(
    level=LOGLEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings("ignore")

# Global settings
DEBUG = False

# Log AWS environment information for debugging
AWS_REGION = os.environ.get(
    "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
)


class WebSocketAioHttpAdapter:
    """Adapter to make aiohttp WebSocket work with our WebSocketHandler."""

    def __init__(self, ws):
        self.ws = ws
        self.path = "/interact-s2s"  # Default path for Nova Sonic

    async def send(self, message):
        """Send message to WebSocket."""
        if isinstance(message, str):
            await self.ws.send_str(message)
        else:
            await self.ws.send_bytes(message)

    async def recv(self):
        """Receive message from WebSocket."""
        msg = await self.ws.receive()
        if msg.type == WSMsgType.TEXT:
            return msg.data
        elif msg.type == WSMsgType.BINARY:
            return msg.data
        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
            raise ConnectionError("WebSocket connection closed")
        return None

    async def close(self, code=1000, reason=""):
        """Close WebSocket connection."""
        await self.ws.close(code=code, message=reason.encode())

    def __aiter__(self):
        """Make this async iterable for 'async for' loops."""
        return self

    async def __anext__(self):
        """Async iterator protocol."""
        try:
            message = await self.recv()
            if message is None:
                raise StopAsyncIteration
            return message
        except ConnectionError:
            raise StopAsyncIteration


async def health_check(request):
    """Health check endpoint for load balancer - matches Java implementation."""
    return web.Response(text="OK", status=200)


async def websocket_handler(request):
    """Handle WebSocket connections on /interact-s2s path."""
    logger.info("New WebSocket connection request received")

    ws = WebSocketResponse()
    await ws.prepare(request)

    # Create adapter for our WebSocket handler
    ws_adapter = WebSocketAioHttpAdapter(ws)

    try:
        # Use our existing WebSocket handler
        handler = WebSocketHandler()
        await handler.handle_connection(ws_adapter)
    except Exception as e:
        logger.error(f"WebSocket handler error: {str(e)}", exc_info=True)
    finally:
        if not ws.closed:
            await ws.close()

    return ws


async def create_app():
    """Create aiohttp application with both HTTP and WebSocket endpoints."""
    app = web.Application()

    # Add health check endpoints (matching Java pattern)
    app.router.add_get("/health", health_check)
    app.router.add_get("/", health_check)  # Root path for simple checks

    # Add WebSocket endpoint
    app.router.add_get("/interact-s2s", websocket_handler)

    return app


async def main(host, port):
    """Main function to run unified HTTP/WebSocket server on single port."""
    logger.info(f"Starting Nova Sonic server (HTTP + WebSocket) on {host}:{port}")

    try:
        # Create unified application
        app = await create_app()

        # Create and start server
        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, host, port)
        await site.start()

        logger.info(f"Server started successfully on http://{host}:{port}")
        logger.info(f"Health check available at: http://{host}:{port}/health")
        logger.info(f"WebSocket endpoint available at: ws://{host}:{port}/interact-s2s")

        # Keep the server running forever
        await asyncio.Future()

    except Exception as ex:
        logger.error(f"Failed to start server: {str(ex)}", exc_info=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nova Sonic Python Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    if args.debug:
        DEBUG = True
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug mode enabled")

    host = str(os.getenv("HOST", "0.0.0.0"))
    port = int(os.getenv("PORT", "8080"))  # Single port for everything

    if not host or not port:
        logger.error(f"HOST and PORT are required. Received HOST: {host}, PORT: {port}")
    else:
        try:
            logger.info(f"Starting server with HOST: {host}, PORT: {port}")
            asyncio.run(main(host, port))
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {str(e)}", exc_info=True)
