"""
Client for making GraphQL subscriptions over websocket

References:
  - Blog post: https://aws.amazon.com/blogs/mobile/appsync-websockets-python/  
  - Developer guide: https://docs.aws.amazon.com/appsync/latest/devguide/real-time-websocket-client.html
  - Performance notes: https://github.com/websocket-client/websocket-client  
"""
# Standard library imports
import sys
import json 
import logging
from enum import Enum
from uuid import uuid4
from base64 import b64encode
# Third party imports 
import websocket

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class WebSocketStatus(Enum):
    """
    Enumeration for websocket connection status
    """
    NOT_CONNECTED = 1
    SUBSCRIPTION_REGISTRATION_STARTED = 2 
    SUBSCRIPTION_REGISTERED = 3

class GraphQLSubscriptionClient:
    """Client for making GraphQL subscriptions over websocket"""

    def __init__(self, endpoint, auth_token):
        """
        Initialize the GraphQL websocket client
        
        Args:
          endpoint: URL of the GraphQL API endpoint  
          auth_token: Auth token to use in Authorization header
        """

        # WebSocket connection attributes
        self.websocket = None
        self.websocket_status = WebSocketStatus.NOT_CONNECTED

        # Configure WebSocket URL and headers
        self.websocket_url = endpoint.replace("https", "wss").replace("appsync-api", "appsync-realtime-api")        
        self.websocket_headers = {
            "Authorization": auth_token,
            "host": endpoint.replace("https://", "").replace("/graphql", "")
        }

        # Callbacks
        self.on_message_callback = None
        self.on_error_callback = None
        self.on_subscription_registered_callback = None

        # Subscription attributes
        self.subscribe_payload = None
        self.subscription_id = None

    def on_open(self, websocket):
        """Callback when websocket connection opens"""
        
        logging.info("[on_open] Websocket connected")
        
        # Send connection init message
        init_message = {"type": "connection_init"}
        websocket.send(json.dumps(init_message))

    def on_message(self, websocket, message):
        """Callback when receiving messages on websocket"""
        
        message = json.loads(message)
        message_type = message.get("type", "")
        
        logging.info(f"[on_message] Received {message_type} message: {message}")
        
        if message_type == "connection_ack":
            
            # Send subscription registration message
            register_message = {
                "id": self.subscription_id,
                "type": "start",
                "payload": {
                    "data": json.dumps(self.subscribe_payload),
                    "extensions": {"authorization": self.websocket_headers}
                }
            }
            # log register_message content
            logging.info(f"[on_message] Registering subscription {self.subscription_id}: {register_message}")
            websocket.send(json.dumps(register_message))
            
        elif message_type == "start_ack":
            self.websocket_status = WebSocketStatus.SUBSCRIPTION_REGISTERED
            if self.on_subscription_registered_callback:
                self.on_subscription_registered_callback()

        elif message_type == "data":
            if not self.on_message_callback:
                return

            payload = message.get("payload")
            if not payload:
                return
            
            data = payload.get("data")
            if data:
                self.on_message_callback(data, self)
                
        elif message_type == "error":
            logging.error(f"[on_message] Error: {message['payload']}")

    def on_error(self, websocket, error):
        """Callback when websocket connection closes with error"""
        
        logging.error(f"[on_error] Websocket error: {error}")
        
        if self.on_error_callback:
            self.on_error_callback(error)

    def on_close(self, websocket, close_code, close_message):
        """Callback when websocket connection closes"""
        
        logging.info(f"[on_close] Websocket closed with code {close_code}: {close_message}")
    
    def subscribe(self, query, operation_name, variables=None, 
                  on_message_callback=None, 
                  on_subscription_registered_callback = None,
                  on_error_callback=None,
                  resubscribe=False):
        """
        Register a subscription over websocket
        
        Args:
          query: GraphQL query string
          operation_name: Name of the operation  
          variables: Optional dict of GraphQL variables
          on_message_callback: Callback to invoke when receiving messages
          on_error_callback: Callback to invoke on errors
        """
        
        # Ignore request if already connected and resubscribe is False
        if self.websocket_status != WebSocketStatus.NOT_CONNECTED and not resubscribe:
            logging.info(f"[GraphQLSubscriptionClient::subscribe] Subscription {self.subscription_id} already exists")
            return
        
        # Close existing websocket connection if needed
        if self.websocket_status != WebSocketStatus.NOT_CONNECTED:
            logging.info("[subscribe] Subscription already exists, unsubscribing first")
            self.unsubscribe()
            
        # Configure callback functions
        self.on_message_callback = on_message_callback
        self.on_error_callback = on_error_callback
        self.on_subscription_registered_callback = on_subscription_registered_callback
        
        # Configure subscription payload
        self.subscribe_payload = {
            "query": query,
            "operationName": operation_name, 
            "variables": variables if variables else {}
        }
        
        # Generate unique ID for subscription
        self.subscription_id = str(uuid4())
        
        # Open websocket connection
        logging.info("[subscribe] Opening websocket...")
        websocket_url = f"{self.websocket_url}?header={b64encode(json.dumps(self.websocket_headers).encode('utf-8')).decode('utf-8')}&payload=e30="
        self.websocket = websocket.WebSocketApp(
            websocket_url,
            subprotocols=["graphql-ws"], 
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.websocket.run_forever()
        self.websocket_status = WebSocketStatus.SUBSCRIPTION_REGISTRATION_STARTED

    def unsubscribe(self):
        """Unsubscribe the websocket subscription"""
        
        if not self.websocket or self.websocket_status == WebSocketStatus.NOT_CONNECTED:
            logging.info("[unsubscribe] No active websocket connection")
            return
        
        try:
            # Send unsubscribe message
            deregister_message = {"type": "stop", "id": self.subscription_id}
            self.websocket.send(json.dumps(deregister_message))
            
            # Reset subscription state
            self.subscribe_payload = None
            self.subscription_id = None
            
            # Reset callbacks
            self.on_message_callback = None
            self.on_error_callback = None
            
            # Close websocket connection
            self.websocket.close()
            self.websocket = None
            self.websocket_status = WebSocketStatus.NOT_CONNECTED
            
        except Exception as error:
            logging.error(f"[unsubscribe] Error closing websocket: {error}")