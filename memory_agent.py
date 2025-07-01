import asyncio
import json
import logging
import os

from typing import Dict, List, Optional, Any

from agent_memory_client import MemoryAPIClient, create_memory_client
from agent_memory_client.models import WorkingMemory
from langchain_tavily import TavilySearch


from langchain_openai import ChatOpenAI

from redis import Redis
from config import config

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_USER = "demo_user"



class MemoryAgent:
    def __init__(self):
        self.open_ai_key = config.openai_api_key
        self.llm_model = config.openai_model
        self.memory_server_url = config.memory_server_url
        self.temperature = config.openai_temperature
        
        self.client = self.get_memory_client()
     
        self._web_search_tool = TavilySearch(max_results=3)


    def run_sync(self, coro):
        try:
            return asyncio.run(coro)
        except RuntimeError as e:
            logger.error(f"Event loop error: {e}")
            raise

    def get_memory_client(self) -> MemoryAPIClient:
        """
        Get the MemoryAPIClient instance, creating it if it doesn't exist.
        """
        client = asyncio.run(self._get_memory_client_async())
        return client

    async def _get_memory_client_async(self) -> MemoryAPIClient:
        return await create_memory_client(
            base_url=self.memory_server_url,
            timeout=30.0,
            default_model_name=self.llm_model,
        )


    async def _get_working_memory_async(self, session_id: str, user_id: str) -> WorkingMemory:
        result = await self.client.get_working_memory(
            session_id=session_id,
            namespace=f"{user_id}",
            window_size=15,
        )
        return WorkingMemory(**result.model_dump())

    async def _add_memory(self, session_id: str, user_id: str, role: str, content: str):
        await self.client.append_messages_to_working_memory(
            session_id=session_id,
            messages=[{"role": role, "content": content}],
            namespace=f"{user_id}"
        )
            
    def add_memory(self, chat_id: str, message: str, role: str):
        """
        Add user message to memory for specific chat_id only.
        """
        try:
            self.run_sync(self._add_memory(
                session_id=chat_id,
                user_id=chat_id,
                role=role,
                content=message
            ))
            logger.debug(f"Added user message to chat_id {chat_id}")
        except Exception as e:
            logger.error(f"Error appending user message for chat_id {chat_id}: {e}")


    def get_context(self, chat_id: str, max_chars: int = 3000) -> str:
        """
        Get conversation history for a specific chat_id only.
        Returns formatted context string for GPT prompting.
        """
        try:
            # Use asyncio.run to handle event loop properly
            mem = self.run_sync(self._get_working_memory_async(session_id=chat_id, user_id=chat_id))
            # logger.debug(f"Retrieved memory for chat_id {chat_id}: {len(mem.messages) if mem.messages else 0} messages")
            
            # Format messages into context string
            if not mem.messages:
                return ""
            
            # Filter and format recent messages for this chat only
            context_messages = []
            char_count = 0
            
            # Reverse to get most recent first, then build context
            for msg in reversed(mem.messages[-10:]):  # Last 10 messages
                if msg.get("role") in ["user", "assistant"]:
                    formatted_msg = f"{msg['role'].title()}: {msg['content']}\n"
                    if char_count + len(formatted_msg) <= max_chars:
                        context_messages.insert(0, formatted_msg)
                        char_count += len(formatted_msg)
                    else:
                        break
            
            context = "".join(context_messages)
            if context:
                return context
            return ""
                
        except Exception as e:
            logger.error(f"Error getting enhanced context for chat_id {chat_id}: {e}")
            return ""
