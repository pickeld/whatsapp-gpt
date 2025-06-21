from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain.schema import BaseMessage
from typing import List
from utiles.logger import Logger


logger = Logger(__name__)

class MemoryManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        logger.info(f"Initializing MemoryManager with Redis URL: {redis_url}")
        self.redis_url = redis_url
        self._cache = {}  # Optional performance cache

    def get(self, chat_id: str) -> ConversationBufferMemory:
        """
        Retrieve or initialize persistent memory for a specific chat_id using Redis.
        """
        if chat_id not in self._cache:
            history = RedisChatMessageHistory(session_id=chat_id, url=self.redis_url)
            memory = ConversationBufferMemory(chat_memory=history, return_messages=True)
            self._cache[chat_id] = memory
        return self._cache[chat_id]

    def get_history(self, chat_id: str) -> List[BaseMessage]:
        """
        Return message history for a given chat_id.
        """
        return self.get(chat_id).chat_memory.messages

    def append_user(self, chat_id: str, message: str):
        """
        Append a user message to memory.
        """ 
        self.get(chat_id).chat_memory.add_user_message(message)

    def append_ai(self, chat_id: str, message: str):
        """
        Append an AI message to memory.
        """
        self.get(chat_id).chat_memory.add_ai_message(message)

    def clear(self, chat_id: str):
        """
        Clear memory for a specific chat_id.
        """
        if chat_id in self._cache:
            self._cache[chat_id].chat_memory.clear()

    def sessions(self) -> List[str]:
        """
        List all cached sessions (note: Redis keys not scanned here).
        """
        return list(self._cache.keys())
