# src/services/conversation_history.py
"""
Conversation History Service with Redis Caching and RAG Integration

This service provides:
1. Redis-based conversation caching for fast recent history retrieval
2. Intelligent conversation context filtering
3. RAG integration with Qdrant for long-term storage and retrieval
4. Chunked conversation storage for memory efficiency
5. Clear conversation commands
"""

import json
import hashlib
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import redis.asyncio as redis
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
import re

from config.config import config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class ConversationMessage:
    """Represents a single conversation message"""

    user_id: str
    username: str
    message: str
    response: str
    timestamp: datetime
    intent: Optional[str] = None
    context_score: float = 0.0  # Relevance score for context filtering

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMessage":
        """Create from dictionary, handling both 'bot_response' and 'response' keys for backward compatibility"""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        # Handle both 'bot_response' and 'response' keys
        if "bot_response" in data:
            data["response"] = data.pop("bot_response")
        elif "response" not in data and "bot_respons" in data:
            # Handle typo 'bot_respons' if present
            data["response"] = data.pop("bot_respons")
        elif "response" not in data:
            data["response"] = ""
        return cls(**data)


class ConversationHistoryService:
    """Manages conversation history with Redis caching and RAG integration"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.qdrant_client: Optional[QdrantClient] = None
        self.embedding_model = None
        self.redis_url = None
        self.collection_name = "conversation_history"

        # Configuration
        self.max_redis_messages = 50  # Recent messages in Redis
        self.max_context_messages = 10  # Messages to include in context
        self.context_relevance_threshold = (
            0.3  # Minimum similarity for context inclusion
        )
        self.redis_ttl = 7 * 24 * 3600  # 7 days TTL for Redis messages

    async def initialize(self):
        """Initialize Redis and Qdrant connections"""
        try:
            # Avoid tokenizer multiprocessing which can leak semaphores on macOS
            import os

            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

            # Initialize Redis
            self.redis_url = getattr(config, "redis_url", None)
            if self.redis_url:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Redis connection established")
            else:
                logger.warning(
                    "Redis URL not configured, conversation history will be limited"
                )

            # Initialize Qdrant
            if config.qdrant_api_url:
                self.qdrant_client = QdrantClient(
                    url=config.qdrant_api_url, api_key=config.qdrant_api_key
                )
                await self._ensure_qdrant_collection()
                logger.info("Qdrant connection established")
            else:
                logger.warning("Qdrant not configured, RAG features will be limited")

            # Initialize embedding model for semantic similarity
            try:
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize conversation history service: {e}")

    async def _ensure_qdrant_collection(self):
        """Ensure the conversation history collection exists in Qdrant"""
        try:
            collections = await asyncio.to_thread(self.qdrant_client.get_collections)
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                await asyncio.to_thread(
                    self.qdrant_client.create_collection,
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=384, distance=models.Distance.COSINE
                    ),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")

    def _get_redis_key(self, user_id: str) -> str:
        """Get Redis hash key for user conversation history"""
        return f"conversation_history:user:{user_id}"

    def _get_message_id(self, user_id: str, timestamp: datetime) -> str:
        """Generate unique message ID as UUID"""
        # Create deterministic UUID from user_id and timestamp
        content = f"{user_id}:{timestamp.isoformat()}"
        namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "conversation.bot")
        return str(uuid.uuid5(namespace, content))

    async def add_conversation(
        self,
        user_id: str,
        username: str,
        user_message: str,
        bot_response: str,
        intent: Optional[str] = None,
        message_id: Optional[str] = None,
    ):
        """Add a new conversation to both Redis cache and Qdrant"""
        try:
            timestamp = datetime.now(timezone.utc)
            if message_id is None:
                message_id = self._get_message_id(user_id, timestamp)

            message = ConversationMessage(
                user_id=user_id,
                username=username,
                message=user_message,
                response=bot_response,
                timestamp=timestamp,
                intent=intent,
            )

            # Store in Redis for fast recent access
            await self._store_in_redis(message, message_id)

            # Store in Qdrant for long-term RAG retrieval
            await self._store_in_qdrant(message, message_id)

            logger.info(f"Stored conversation for user {username}")

        except Exception as e:
            logger.error(f"Failed to add conversation: {e}")

    async def _store_in_redis(self, message: ConversationMessage, message_id: str):
        """Store message in Redis hash with TTL"""
        if not self.redis_client:
            logger.warning("Redis client is not initialized!")
            return

        try:
            redis_key = self._get_redis_key(message.user_id)
            message_data = json.dumps(message.to_dict(), default=str)
            logger.info(f"[DEBUG] Redis URL: {self.redis_url}")
            logger.info(
                f"[DEBUG] Storing to Redis hash: {redis_key} field: {message_id}"
            )
            logger.info(f"[DEBUG] Message data: {message_data}")

            # Store in Redis hash
            await self.redis_client.hset(redis_key, message_id, message_data)
            # Set TTL on the hash key
            await self.redis_client.expire(redis_key, self.redis_ttl)
            logger.info(f"[DEBUG] Set TTL {self.redis_ttl} on key {redis_key}")

            # Optionally trim old messages (if hash grows too large)
            fields = await self.redis_client.hkeys(redis_key)
            if len(fields) > self.max_redis_messages:
                # Sort by timestamp in value, remove oldest
                all_msgs = await self.redis_client.hgetall(redis_key)
                # Parse and sort by timestamp
                sorted_fields = sorted(
                    all_msgs.items(), key=lambda item: json.loads(item[1])["timestamp"]
                )
                for field, _ in sorted_fields[: -self.max_redis_messages]:
                    await self.redis_client.hdel(redis_key, field)

        except Exception as e:
            logger.error(f"Failed to store in Redis: {e}")

    async def _store_in_qdrant(self, message: ConversationMessage, message_id: str):
        """Store message in Qdrant for semantic search"""
        if not self.qdrant_client or not self.embedding_model:
            return

        try:
            # Create combined text for embedding
            combined_text = f"User: {message.message}\nBot: {message.response}"

            # Generate embedding
            embedding = await asyncio.to_thread(
                lambda: self.embedding_model.encode(
                    combined_text,
                    show_progress_bar=False,
                )
            )

            # Use the provided message_id for Qdrant point ID
            payload = message.to_dict()
            payload["combined_text"] = combined_text

            await asyncio.to_thread(
                self.qdrant_client.upsert,
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=message_id, vector=embedding.tolist(), payload=payload
                    )
                ],
            )

        except Exception as e:
            logger.error(f"Failed to store in Qdrant: {e}")

    async def get_conversation_context(
        self, user_id: str, current_message: str, include_semantic: bool = True
    ) -> List[ConversationMessage]:
        """
        Get intelligent conversation context combining recent cache and semantic search

        Args:
            user_id: User identifier
            current_message: Current user message for semantic filtering
            include_semantic: Whether to include semantically similar past conversations
        """
        try:
            context_messages = []

            # 1. Get recent messages from Redis cache
            recent_messages = await self._get_recent_from_redis(user_id, limit=20)

            # 2. Filter recent messages for relevance
            if recent_messages and self.embedding_model:
                filtered_recent = await self._filter_by_relevance(
                    recent_messages,
                    current_message,
                    max_messages=self.max_context_messages // 2,
                )
                context_messages.extend(filtered_recent)
            else:
                # Fallback: use most recent messages without filtering
                context_messages.extend(
                    recent_messages[: self.max_context_messages // 2]
                )

            # 3. Get semantically similar conversations from Qdrant (if enabled)
            if include_semantic and len(context_messages) < self.max_context_messages:
                remaining_slots = self.max_context_messages - len(context_messages)
                semantic_messages = await self._get_semantic_context(
                    user_id,
                    current_message,
                    limit=remaining_slots,
                    exclude_recent_ids=[
                        m.timestamp.isoformat() for m in context_messages
                    ],
                )
                context_messages.extend(semantic_messages)

            # Sort by timestamp for chronological context
            context_messages.sort(key=lambda m: m.timestamp)

            logger.info(
                f"Retrieved {len(context_messages)} context messages for user {user_id}"
            )
            return context_messages

        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return []

    async def _get_recent_from_redis(
        self, user_id: str, limit: int = 20
    ) -> List[ConversationMessage]:
        """Get recent messages from Redis hash cache, sorted by timestamp desc"""
        if not self.redis_client:
            return []

        try:
            redis_key = self._get_redis_key(user_id)
            all_msgs = await self.redis_client.hgetall(redis_key)
            # all_msgs: dict of {message_id: json_str}
            parsed_msgs = []
            for msg_json in all_msgs.values():
                try:
                    message_dict = json.loads(
                        msg_json.decode() if isinstance(msg_json, bytes) else msg_json
                    )
                    parsed_msgs.append(ConversationMessage.from_dict(message_dict))
                except Exception as e:
                    logger.warning(f"Failed to parse message from Redis: {e}")
                    continue
            # Sort by timestamp descending (most recent first)
            parsed_msgs.sort(key=lambda m: m.timestamp, reverse=True)
            return parsed_msgs[:limit]

        except Exception as e:
            logger.error(f"Failed to get recent messages from Redis: {e}")
            return []

    async def _filter_by_relevance(
        self,
        messages: List[ConversationMessage],
        current_message: str,
        max_messages: int = 5,
    ) -> List[ConversationMessage]:
        """Filter messages by semantic relevance to current message"""
        if not self.embedding_model or not messages:
            return messages[:max_messages]

        try:
            # Get embedding for current message
            current_embedding = await asyncio.to_thread(
                lambda: self.embedding_model.encode(
                    current_message,
                    show_progress_bar=False,
                )
            )

            # Calculate relevance scores
            for message in messages:
                combined_text = f"{message.message} {message.response}"
                msg_embedding = await asyncio.to_thread(
                    lambda: self.embedding_model.encode(
                        combined_text,
                        show_progress_bar=False,
                    )
                )

                # Calculate cosine similarity
                similarity = self._cosine_similarity(current_embedding, msg_embedding)
                message.context_score = similarity

            # Filter by threshold and sort by relevance
            relevant_messages = [
                msg
                for msg in messages
                if msg.context_score >= self.context_relevance_threshold
            ]
            relevant_messages.sort(key=lambda m: m.context_score, reverse=True)

            return relevant_messages[:max_messages]

        except Exception as e:
            logger.error(f"Failed to filter messages by relevance: {e}")
            return messages[:max_messages]

    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np

            return float(
                np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            )
        except:
            return 0.0

    async def _get_semantic_context(
        self,
        user_id: str,
        current_message: str,
        limit: int = 5,
        exclude_recent_ids: List[str] = None,
    ) -> List[ConversationMessage]:
        """Get semantically similar conversations from Qdrant"""
        if not self.qdrant_client or not self.embedding_model:
            return []

        try:
            # Generate embedding for current message
            query_embedding = await asyncio.to_thread(
                lambda: self.embedding_model.encode(
                    current_message,
                    show_progress_bar=False,
                )
            )

            # Search Qdrant for similar conversations
            search_results = await asyncio.to_thread(
                self.qdrant_client.search,
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id", match=models.MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=limit * 2,  # Get more results to filter out recent ones
                score_threshold=self.context_relevance_threshold,
            )

            # Convert to ConversationMessage objects
            messages = []
            exclude_recent_ids = exclude_recent_ids or []

            for result in search_results:
                payload = result.payload
                if payload.get("timestamp") not in exclude_recent_ids:
                    try:
                        # Remove combined_text before creating ConversationMessage
                        payload_copy = payload.copy()
                        payload_copy.pop("combined_text", None)  # Remove if exists

                        message = ConversationMessage.from_dict(payload_copy)
                        message.context_score = result.score
                        messages.append(message)
                    except Exception as e:
                        logger.warning(f"Failed to parse Qdrant result: {e}")
                        continue

                if len(messages) >= limit:
                    break

            return messages

        except Exception as e:
            logger.error(f"Failed to get semantic context from Qdrant: {e}")
            return []

    async def clear_conversation_history(self, user_id: str):
        """Clear all conversation history for a user"""
        try:
            # Clear from Redis
            if self.redis_client:
                redis_key = self._get_redis_key(user_id)
                await self.redis_client.delete(redis_key)
                logger.info(f"Cleared Redis conversation history for user {user_id}")

            # Clear from Qdrant
            if self.qdrant_client:
                await asyncio.to_thread(
                    self.qdrant_client.delete,
                    collection_name=self.collection_name,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="user_id",
                                    match=models.MatchValue(value=user_id),
                                )
                            ]
                        )
                    ),
                )
                logger.info(f"Cleared Qdrant conversation history for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to clear conversation history: {e}")
            raise

    async def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Get conversation statistics for a user"""
        try:
            summary = {
                "user_id": user_id,
                "recent_messages_count": 0,
                "total_messages_count": 0,
                "last_conversation": None,
                "most_common_intents": [],
            }

            # Count recent messages from Redis
            if self.redis_client:
                redis_key = self._get_redis_key(user_id)
                summary["recent_messages_count"] = await self.redis_client.llen(
                    redis_key
                )

                # Get last conversation
                recent_data = await self.redis_client.lrange(redis_key, 0, 0)
                if recent_data:
                    try:
                        last_msg_dict = json.loads(recent_data[0].decode())
                        summary["last_conversation"] = last_msg_dict.get("timestamp")
                    except:
                        pass

            # Count total messages from Qdrant
            if self.qdrant_client:
                try:
                    count_result = await asyncio.to_thread(
                        self.qdrant_client.count,
                        collection_name=self.collection_name,
                        count_filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="user_id",
                                    match=models.MatchValue(value=user_id),
                                )
                            ]
                        ),
                    )
                    summary["total_messages_count"] = count_result.count
                except Exception as e:
                    logger.warning(f"Could not get total message count: {e}")

            return summary

        except Exception as e:
            logger.error(f"Failed to get conversation summary: {e}")
            return {"error": str(e)}

    def format_context_for_ai(self, context_messages: List[ConversationMessage]) -> str:
        """Format conversation context for AI prompt inclusion"""
        if not context_messages:
            return ""

        context_lines = ["### Recent Conversation History:"]
        for msg in context_messages[-10:]:  # Last 10 for context
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            context_lines.append(f"[{timestamp}] User: {msg.message}")
            context_lines.append(f"[{timestamp}] Bot: {msg.response}")
            context_lines.append("")  # Empty line for readability

        context_lines.append("### End of History\n")
        return "\n".join(context_lines)

    def detect_clear_intent(self, message: str) -> bool:
        """Detect if user wants to clear conversation history"""
        clear_patterns = [
            r"\b(clear|delete|remove).*(conversation|history|chat)\b",
            r"\b(conversation|history|chat).*(clear|delete|remove)\b",
            r"\bforget.*(conversation|everything)\b",
            r"\breset.*(conversation|chat|history)\b",
            r"\bclear\s+all\b",
            r"\bstart\s+fresh\b",
            r"\bnew\s+conversation\b",
        ]

        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in clear_patterns)


# Global instance
conversation_service = ConversationHistoryService()
