"""
Memory module for AgentCore demo agent
Handles memory storage and retrieval using default short-term memory (STM)
Useget s list_events API for immediate retrieval without async processing delays
"""

import logging
import boto3
from datetime import datetime
from typing import List, Dict, Any, Optional
from bedrock_agentcore.memory import MemoryClient

logger = logging.getLogger(__name__)


class AgentMemory:
    """
    Memory manager using default short-term memory strategy.
    Uses list_events API for immediate conversation history retrieval.
    Pattern matches the proven aws-asl-metahuman project.
    """
    
    def __init__(self, memory_id: str, region_name: str = 'us-west-2'):
        """
        Initialize memory client
        
        Args:
            memory_id: Memory resource ID from CloudFormation
            region_name: AWS region
        """
        self.memory_id = memory_id
        self.region_name = region_name
        self.client = MemoryClient(region_name=region_name)
        self.bedrock_client = boto3.client('bedrock-agentcore', region_name=region_name)
        print(f"Memory Client initialized for ID: {memory_id}")
    
    def retrieve_relevant_memories(
        self, 
        actor_id: str,
        session_id: str,
        query: str,
        top_k: int = 10
    ) -> str:
        """
        Retrieve recent conversation history from short-term memory.
        Uses list_events API for immediate access to stored events.
        
        Args:
            actor_id: User identifier
            session_id: Session identifier
            query: Search query (not used in STM retrieval, kept for compatibility)
            top_k: Maximum number of events to retrieve
            
        Returns:
            Formatted conversation context string
        """
        try:
            print(f"[MEMORY RETRIEVE] Retrieving conversation history...")
            print(f"[MEMORY RETRIEVE] Actor: {actor_id}, Session: {session_id}")
            
            # Use boto3 bedrock-agentcore client to list events
            response = self.bedrock_client.list_events(
                memoryId=self.memory_id,
                actorId=actor_id,
                sessionId=session_id,
                maxResults=top_k
            )
            
            events = response.get('events', [])
            if not events:
                print(f"[MEMORY RETRIEVE] No conversation history found")
                return ""
            
            # Parse events and build context
            context_lines = []
            for event in events:
                # Each event contains messages in the payload
                payload = event.get('payload', [])
                for item in payload:
                    if 'conversational' in item:
                        conversational = item['conversational']
                        role = conversational.get('role', '').upper()
                        content_obj = conversational.get('content', {})
                        text = content_obj.get('text', '')
                        
                        if text and role:
                            # Format as "USER: message" or "ASSISTANT: message"
                            context_lines.append(f"{role}: {text}")
            
            if not context_lines:
                print(f"[MEMORY RETRIEVE] No conversational content found in events")
                return ""
            
            # Reverse to get chronological order (oldest first)
            context_lines.reverse()
            
            print(f"[MEMORY RETRIEVE] Retrieved {len(events)} events with {len(context_lines)} messages")
            print(f"[MEMORY] Context preview: {context_lines[0][:100] if context_lines else 'empty'}...")
            
            # Format as context for the agent
            context = "\n\nPrevious conversation:\n" + "\n".join(context_lines)
            return context
            
        except Exception as e:
            print(f"[MEMORY RETRIEVE] Error retrieving conversation history: {str(e)}")
            import traceback
            traceback.print_exc()
            return ""
    
    def store_conversation(
        self,
        actor_id: str,
        session_id: str,
        user_message: str,
        assistant_message: str
    ) -> Optional[str]:
        """
        Store conversation in short-term memory for immediate retrieval.
        Events are stored as raw conversation history.
        
        Args:
            actor_id: User identifier
            session_id: Session identifier
            user_message: User's message
            assistant_message: Assistant's response
            
        Returns:
            Event ID if successful, None otherwise
        """
        try:
            print(f"[MEMORY STORE] Saving conversation to memory...")
            print(f"[MEMORY STORE] Actor: {actor_id}, Session: {session_id}")
            
            event = self.client.create_event(
                memory_id=self.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    (user_message, "USER"),
                    (assistant_message, "ASSISTANT")
                ],
                event_timestamp=datetime.utcnow()
            )
            
            event_id = event.get('eventId', 'unknown')
            print(f"[MEMORY STORE] Event stored with ID: {event_id}")
            
            return event_id
            
        except Exception as e:
            print(f"[MEMORY STORE] Error storing conversation: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
