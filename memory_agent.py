import asyncio
import logging
from typing import Dict, List, Optional, Any

from agent_memory_client import MemoryAPIClient, create_memory_client
from agent_memory_client.models import WorkingMemory
from config import config

# Logging setup
logger = logging.getLogger("memory_agent")
logger.setLevel(logging.INFO)

DEFAULT_USER = "demo_user"


class MemoryAgent:
    def __init__(self):
        self.open_ai_key = config.openai_api_key
        self.llm_model = config.openai_model
        self.memory_server_url = config.memory_server_url

    async def _get_memory_client(self) -> MemoryAPIClient:
        return await create_memory_client(
            base_url=self.memory_server_url,
            timeout=30.0,
            default_model_name=self.llm_model,
        )

    def _run_async(self, coro):
        """
        Run async coroutine in a safe way, compatible with Flask and threaded environments.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # For running inside existing loop (e.g., Jupyter, ASGI servers) — not ideal here
                return asyncio.run_coroutine_threadsafe(coro, loop).result()
        except RuntimeError:
            # No loop, make one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def add_memory(self, chat_id: str, message: str, role: str):
        """
        Add user message to memory for specific chat_id.
        """
        try:
            async def _add():
                client = await self._get_memory_client()
                await client.append_messages_to_working_memory(
                    session_id=chat_id,
                    messages=[{"role": role, "content": message}],
                    namespace=chat_id,
                )
            self._run_async(_add())
            logger.debug(f"Added {role} message to chat_id {chat_id}")
        except Exception as e:
            logger.error(f"Error appending message to memory for chat_id {chat_id}: {e}")

    def get_context(self, chat_id: str, max_chars: int = 3000) -> str:
        """
        Retrieve recent messages for a given chat_id, trimmed to max_chars.
        Returns formatted prompt-ready string.
        """
        try:
            async def _get():
                client = await self._get_memory_client()
                result = await client.get_working_memory(
                    session_id=chat_id,
                    namespace=chat_id,
                    window_size=15,
                )
                return WorkingMemory(**result.model_dump())

            mem = self._run_async(_get())
            if not mem.messages:
                return ""

            context_messages = []
            char_count = 0
            for msg in reversed(mem.messages[-10:]):  # Limit to last 10
                if msg.get("role") in ["user", "assistant"]:
                    formatted = f"{msg['role'].title()}: {msg['content']}\n"
                    if char_count + len(formatted) <= max_chars:
                        context_messages.insert(0, formatted)
                        char_count += len(formatted)
                    else:
                        break

            return "".join(context_messages)
        except Exception as e:
            logger.error(f"Error getting context for chat_id {chat_id}: {e}")
            return ""
