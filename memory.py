from typing import List
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain.schema import BaseMessage, Document
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client.http.models import VectorParams, Distance, Filter, FieldCondition, MatchValue
from utiles.logger import Logger
from config import config
import qdrant_client
import uuid, hashlib

logger = Logger(__name__)


class MemoryManager:
    def __init__(self, redis_url: str = "redis://localhost:6379", qdrant_url: str = "http://localhost:6333"):
        logger.info(f"Initializing MemoryManager with Redis for short-term memory")
        self.redis_url = redis_url
        self.qdrant_collection_name = config.qdrant_collection_name
        self.embedding_model = config.embedding_model
        self._short_term_memory_cache = {}

        # Long-term memory (Qdrant)
        self.long_term_memory_enabled = qdrant_url is not None
        if self.long_term_memory_enabled:
            logger.info("Initializing MemoryManager with Qdrant for long-term memory")
            self.qdrant_client = qdrant_client.QdrantClient(url=qdrant_url)
            self._init_long_term_memory()
            self.vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.qdrant_collection_name,
                embedding=HuggingFaceEmbeddings(model_name=self.embedding_model)
            )

    def _init_long_term_memory(self):
        if self.qdrant_collection_name not in {col.name for col in self.qdrant_client.get_collections().collections}:
            self.qdrant_client.create_collection(
                collection_name=self.qdrant_collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

    # Short-term memory retrieval
    def get_short_term_memory(self, chat_id: str, msgs: bool = False) -> ConversationBufferMemory:
        if chat_id not in self._short_term_memory_cache:
            history = RedisChatMessageHistory(session_id=chat_id, url=self.redis_url)
            memory = ConversationBufferMemory(chat_memory=history, return_messages=True)
            self._short_term_memory_cache[chat_id] = memory
        if msgs:
            return self._short_term_memory_cache[chat_id].chat_memory.messages
        return self._short_term_memory_cache[chat_id]

    def append_user_message(self, chat_id: str, message: str):
        self.get_short_term_memory(chat_id).chat_memory.add_user_message(message)
        if self.long_term_memory_enabled:
            self._save_to_long_term_memory(chat_id, message, role="user")

    def append_ai_message(self, chat_id: str, message: str):
        self.get_short_term_memory(chat_id).chat_memory.add_ai_message(message)
        if self.long_term_memory_enabled:
            self._save_to_long_term_memory(chat_id, message, role="ai")

    def clear_short_term_memory(self, chat_id: str):
        if chat_id in self._short_term_memory_cache:
            self._short_term_memory_cache[chat_id].chat_memory.clear()

    def list_active_sessions(self) -> List[str]:
        return list(self._short_term_memory_cache.keys())

    def get_recent_short_term_history(self, chat_id: str, max_chars: int = 3500, exclude_prefixes: List[str] = None) -> List[BaseMessage]:
        messages = self.get_short_term_memory(chat_id, msgs=True)
        buffer = []
        total_chars = 0
        exclude_prefixes = exclude_prefixes or []

        for msg in reversed(messages):
            if not hasattr(msg, 'content') or not isinstance(msg.content, str):
                continue
            if any(msg.content.strip().startswith(p) for p in exclude_prefixes):
                continue

            msg_len = len(msg.content)
            if total_chars + msg_len > max_chars:
                break
            buffer.append(msg)
            total_chars += msg_len

        return buffer

    # Long-term memory storage
    def _save_to_long_term_memory(self, chat_id: str, message: str, role="user"):
        digest = hashlib.sha1(message.encode()).hexdigest()
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{chat_id}-{role}-{digest}"))

        doc = Document(
            page_content=message,
            metadata={"chat_id": chat_id, "role": role}
        )
        logger.debug(f"Storing to long-term: [{role}] {message}")
        self.vector_store.add_documents([doc], ids=[point_id])

    def retrieve_from_long_term_memory(self, query: str, chat_id: str, k: int = 5) -> List[str]:
        if not self.long_term_memory_enabled:
            logger.warning("Long-term memory (Qdrant) not initialized — semantic retrieval skipped.")
            return []

        try:
            meta_filter = Filter(
                must=[
                    FieldCondition(
                        key="metadata.chat_id",
                        match=MatchValue(value=chat_id)
                    )
                ]
            )
            docs = self.vector_store.similarity_search(query, k=k, filter=meta_filter)
            return [doc.page_content for doc in docs]
        except Exception as e:
            logger.error(f"Long-term memory retrieval failed: {e}")
            return []
