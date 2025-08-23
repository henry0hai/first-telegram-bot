# src/services/qdrant_conversation_manager.py
"""
Qdrant Conversation Manager

This service ensures all conversation data is comprehensively stored in Qdrant
for external MCP server access. It provides:

1. Comprehensive conversation storage with full metadata
2. Advanced search capabilities for MCP tools
3. Data validation and integrity checks
4. Export capabilities for external systems
5. Schema standardization for MCP server compatibility
"""

import json
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from config.config import config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class QdrantConversationEntry:
    """Standardized conversation entry for Qdrant storage"""

    # Core conversation data
    id: str
    user_id: str
    username: str
    user_message: str
    response: str
    timestamp: str  # ISO format for consistency
    timestamp_unix: float = 0.0  # Unix timestamp for numeric filtering

    # Metadata for MCP server queries
    intent: Optional[str] = None
    confidence_score: float = 0.0
    message_length: int = 0
    response_length: int = 0
    conversation_turn: int = 0  # Turn number in conversation

    # Semantic data
    combined_text: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"

    # Context and classification
    topics: List[str] = None
    entities: List[str] = None  # Future: extracted entities
    sentiment: str = "neutral"  # Future: sentiment analysis

    # Session data
    session_id: str = ""  # For grouping related conversations
    is_multi_turn: bool = False
    context_used: bool = False

    # System metadata
    bot_version: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if self.topics is None:
            self.topics = []
        if self.entities is None:
            self.entities = []


class QdrantConversationManager:
    """Enhanced Qdrant manager for comprehensive conversation storage"""

    def __init__(self):
        self.qdrant_client: Optional[QdrantClient] = None
        self.embedding_model = None
        self.collection_name = "conversation_history_v2"  # Enhanced collection
        self.legacy_collection = "conversation_history"  # Original collection

        # Enhanced configuration for MCP server compatibility
        self.vector_size = 384  # MiniLM model dimension
        self.batch_size = 100  # For bulk operations

    async def initialize(self):
        """Initialize Qdrant with enhanced schema"""
        try:
            # Initialize Qdrant client
            if config.qdrant_api_url:
                self.qdrant_client = QdrantClient(
                    url=config.qdrant_api_url, api_key=config.qdrant_api_key
                )
                await self._ensure_enhanced_collection()
                logger.info("Enhanced Qdrant conversation manager initialized")
            else:
                logger.warning("Qdrant not configured")

            # Initialize embedding model
            try:
                # Avoid tokenizer multiprocessing which can leak semaphores on macOS
                import os

                os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Embedding model loaded for enhanced storage")
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize enhanced Qdrant manager: {e}")

    async def _ensure_enhanced_collection(self):
        """Create enhanced collection with comprehensive schema"""
        try:
            collections = await asyncio.to_thread(self.qdrant_client.get_collections)
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                # Create enhanced collection with proper indexing
                await asyncio.to_thread(
                    self.qdrant_client.create_collection,
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size, distance=models.Distance.COSINE
                    ),
                    # Create indexes for common MCP queries
                    # This helps with faster filtering by user_id, intent, etc.
                )
                logger.info(
                    f"Created enhanced Qdrant collection: {self.collection_name}"
                )

                # Create indexes for faster MCP queries
                await self._create_field_indexes()

        except Exception as e:
            logger.error(f"Failed to create enhanced collection: {e}")

    async def _create_field_indexes(self):
        """Create field indexes for faster MCP server queries"""
        try:
            # Index commonly queried fields for MCP server
            index_fields = [
                "user_id",  # Query conversations by user
                "intent",  # Query by intent type
                "timestamp",  # Query by time range (string)
                "timestamp_unix",  # Query by time range (numeric)
                "username",  # Query by username
                "topics",  # Query by topic
                "session_id",  # Query by session
                "is_multi_turn",  # Query multi-turn conversations
            ]

            for field in index_fields:
                try:
                    await asyncio.to_thread(
                        self.qdrant_client.create_payload_index,
                        collection_name=self.collection_name,
                        field_name=field,
                        field_schema=models.PayloadSchemaType.KEYWORD,
                    )
                    logger.info(f"Created index for field: {field}")
                except Exception as e:
                    # Index might already exist
                    logger.debug(f"Index creation for {field}: {e}")

        except Exception as e:
            logger.warning(f"Could not create field indexes: {e}")

    async def store_conversation(
        self,
        user_id: str,
        username: str,
        user_message: str,
        response: str,
        intent: Optional[str] = None,
        context_used: bool = False,
        session_id: Optional[str] = None,
        conversation_turn: int = 0,
        message_id: Optional[str] = None,
    ) -> str:
        """
        Store conversation with comprehensive metadata for MCP server access

        Args:
            message_id: Optional UUID to use. If not provided, will generate one.

        Returns:
            str: The UUID of the stored conversation
        """
        try:
            # Use provided message_id or generate deterministic UUID
            if message_id is None:
                timestamp = datetime.now(timezone.utc)
                content = f"{user_id}:{timestamp.isoformat()}"
                namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "conversation.bot.v2")
                entry_id = str(uuid.uuid5(namespace, content))
            else:
                entry_id = message_id
                timestamp = datetime.now(timezone.utc)

            # Create comprehensive conversation entry
            entry = QdrantConversationEntry(
                id=entry_id,
                user_id=user_id,
                username=username,
                user_message=user_message,
                response=response,
                timestamp=timestamp.isoformat(),
                timestamp_unix=timestamp.timestamp(),  # Add Unix timestamp for filtering
                intent=intent,
                message_length=len(user_message),
                response_length=len(response),
                conversation_turn=conversation_turn,
                combined_text=f"User: {user_message}\nBot: {response}",
                session_id=session_id
                or f"session_{user_id}_{timestamp.strftime('%Y%m%d')}",
                is_multi_turn=conversation_turn > 0,
                context_used=context_used,
                bot_version=getattr(config, "app_version", "unknown"),
                created_at=timestamp.isoformat(),
                updated_at=timestamp.isoformat(),
            )

            # Extract topics for better searchability
            entry.topics = self._extract_topics(user_message, response, intent)

            # Generate embedding
            if self.embedding_model:
                embedding = await asyncio.to_thread(
                    lambda: self.embedding_model.encode(
                        entry.combined_text,
                        show_progress_bar=False,
                    )
                )

                # Store in Qdrant
                payload = asdict(entry)
                # Remove fields that shouldn't be in payload
                payload.pop("id", None)

                await asyncio.to_thread(
                    self.qdrant_client.upsert,
                    collection_name=self.collection_name,
                    points=[
                        models.PointStruct(
                            id=entry_id, vector=embedding.tolist(), payload=payload
                        )
                    ],
                )

                logger.info(
                    f"Stored enhanced conversation {entry_id} for user {username}"
                )
                return entry_id
            else:
                logger.warning("No embedding model available, storing without vector")
                return entry_id

        except Exception as e:
            logger.error(f"Failed to store enhanced conversation: {e}")
            return ""

    async def update_conversation_response(self, message_id: str, new_response: str):
        """Update the response field for an existing conversation in Qdrant"""
        try:
            if not self.qdrant_client:
                logger.warning("Qdrant client not initialized")
                return False

            # First, retrieve the existing point to get current payload
            search_result = await asyncio.to_thread(
                self.qdrant_client.retrieve,
                collection_name=self.collection_name,
                ids=[message_id],
                with_payload=True,
                with_vectors=True,
            )

            if not search_result:
                logger.warning(
                    f"Conversation with message_id {message_id} not found in Qdrant"
                )
                return False

            existing_point = search_result[0]
            payload = existing_point.payload.copy()

            # Update the response field
            payload["response"] = new_response

            # Update combined_text for consistency
            payload["combined_text"] = (
                f"User: {payload.get('user_message', '')}\nBot: {new_response}"
            )

            # Re-generate embedding with updated text if embedding model is available
            vector = existing_point.vector
            if self.embedding_model:
                try:
                    new_embedding = await asyncio.to_thread(
                        lambda: self.embedding_model.encode(
                            payload["combined_text"], show_progress_bar=False
                        )
                    )
                    vector = new_embedding.tolist()
                except Exception as e:
                    logger.warning(
                        f"Failed to regenerate embedding, keeping original: {e}"
                    )

            # Update the point in Qdrant
            await asyncio.to_thread(
                self.qdrant_client.upsert,
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(id=message_id, vector=vector, payload=payload)
                ],
            )

            logger.info(
                f"Successfully updated conversation response for message_id: {message_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update conversation response in Qdrant: {e}")
            return False

    def _extract_topics(
        self, user_message: str, response: str, intent: Optional[str]
    ) -> List[str]:
        """Extract topics from conversation for better MCP server queries"""
        topics = []

        # Add intent as primary topic
        if intent:
            topics.append(intent.lower().replace("_", " "))

        # Simple keyword extraction (can be enhanced with NLP)
        import re

        text = f"{user_message} {response}".lower()

        # Common topic patterns
        topic_patterns = {
            "programming": r"\b(python|javascript|code|programming|function|variable|class|method)\b",
            "weather": r"\b(weather|temperature|rain|sunny|cloudy|forecast)\b",
            "system": r"\b(cpu|memory|disk|system|server|performance)\b",
            "scheduling": r"\b(schedule|remind|alarm|task|timer|calendar)\b",
            "help": r"\b(help|how|what|explain|show|tell)\b",
        }

        for topic, pattern in topic_patterns.items():
            if re.search(pattern, text):
                topics.append(topic)

        return topics[:5]  # Limit to 5 topics

    async def query_conversations(
        self, filters: Dict[str, Any], limit: int = 100, include_vectors: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Query conversations with filters for MCP server

        Args:
            filters: Dictionary of filters (user_id, intent, topics, time_range, etc.)
            limit: Maximum number of results
            include_vectors: Whether to include embedding vectors

        Returns:
            List of conversation dictionaries
        """
        try:
            if not self.qdrant_client:
                return []

            # Build Qdrant filters
            qdrant_filters = []

            if "user_id" in filters:
                qdrant_filters.append(
                    models.FieldCondition(
                        key="user_id", match=models.MatchValue(value=filters["user_id"])
                    )
                )

            if "intent" in filters:
                qdrant_filters.append(
                    models.FieldCondition(
                        key="intent", match=models.MatchValue(value=filters["intent"])
                    )
                )

            if "topics" in filters:
                # Search in topics array
                for topic in filters["topics"]:
                    qdrant_filters.append(
                        models.FieldCondition(
                            key="topics", match=models.MatchValue(value=topic)
                        )
                    )

            if "username" in filters:
                qdrant_filters.append(
                    models.FieldCondition(
                        key="username",
                        match=models.MatchValue(value=filters["username"]),
                    )
                )

            if "session_id" in filters:
                qdrant_filters.append(
                    models.FieldCondition(
                        key="session_id",
                        match=models.MatchValue(value=filters["session_id"]),
                    )
                )

            # Time range filter using Unix timestamps for numeric comparison
            if "start_time" in filters:
                start_time = filters["start_time"]
                if isinstance(start_time, datetime):
                    start_unix = start_time.timestamp()
                else:
                    # Assume it's already a Unix timestamp
                    start_unix = float(start_time)

                qdrant_filters.append(
                    models.FieldCondition(
                        key="timestamp_unix",
                        range=models.Range(gte=start_unix),
                    )
                )

            if "end_time" in filters:
                end_time = filters["end_time"]
                if isinstance(end_time, datetime):
                    end_unix = end_time.timestamp()
                else:
                    # Assume it's already a Unix timestamp
                    end_unix = float(end_time)

                qdrant_filters.append(
                    models.FieldCondition(
                        key="timestamp_unix", range=models.Range(lte=end_unix)
                    )
                )

            # Execute query
            if qdrant_filters:
                filter_condition = models.Filter(must=qdrant_filters)
            else:
                filter_condition = None

            # Use scroll for better performance with large datasets
            results = await asyncio.to_thread(
                self.qdrant_client.scroll,
                collection_name=self.collection_name,
                scroll_filter=filter_condition,
                limit=limit,
                with_vectors=include_vectors,
                with_payload=True,
            )

            # Format results for MCP server
            conversations = []
            for point in results[0]:  # results is tuple (points, next_page_offset)
                conversation = {"id": str(point.id), **point.payload}
                if include_vectors and point.vector:
                    conversation["vector"] = point.vector
                conversations.append(conversation)

            logger.info(
                f"Retrieved {len(conversations)} conversations with filters: {filters}"
            )
            return conversations

        except Exception as e:
            logger.error(f"Failed to query conversations: {e}")
            return []

    async def semantic_search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for MCP server tools

        Args:
            query: Search query text
            user_id: Optional user filter
            limit: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of similar conversations with scores
        """
        try:
            if not self.embedding_model or not self.qdrant_client:
                return []

            # Generate query embedding
            query_embedding = await asyncio.to_thread(
                lambda: self.embedding_model.encode(
                    query,
                    show_progress_bar=False,
                )
            )

            # Build filters
            search_filters = []
            if user_id:
                search_filters.append(
                    models.FieldCondition(
                        key="user_id", match=models.MatchValue(value=user_id)
                    )
                )

            search_filter = (
                models.Filter(must=search_filters) if search_filters else None
            )

            # Execute semantic search
            search_results = await asyncio.to_thread(
                self.qdrant_client.search,
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
            )

            # Format results
            results = []
            for result in search_results:
                conversation = {
                    "id": str(result.id),
                    "score": float(result.score),
                    **result.payload,
                }
                results.append(conversation)

            logger.info(f"Semantic search found {len(results)} results for: {query}")
            return results

        except Exception as e:
            logger.error(f"Failed to perform semantic search: {e}")
            return []

    async def get_conversation_analytics(
        self, user_id: Optional[str] = None, time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get conversation analytics for MCP server dashboards

        Args:
            user_id: Optional user filter
            time_range_hours: Time range for analytics

        Returns:
            Analytics dictionary
        """
        try:
            # Calculate time range
            start_time = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)

            filters = {"start_time": start_time}  # Pass datetime object, not string
            if user_id:
                filters["user_id"] = user_id

            conversations = await self.query_conversations(
                filters=filters, limit=10000  # Large limit for analytics
            )

            # Calculate analytics
            analytics = {
                "total_conversations": len(conversations),
                "unique_users": len(set(c.get("user_id", "") for c in conversations)),
                "unique_sessions": len(
                    set(c.get("session_id", "") for c in conversations)
                ),
                "average_message_length": 0,
                "average_response_length": 0,
                "intent_distribution": {},
                "topic_distribution": {},
                "multi_turn_conversations": 0,
                "context_used_count": 0,
                "time_range_hours": time_range_hours,
            }

            if conversations:
                analytics["average_message_length"] = sum(
                    c.get("message_length", 0) for c in conversations
                ) / len(conversations)

                analytics["average_response_length"] = sum(
                    c.get("response_length", 0) for c in conversations
                ) / len(conversations)

                # Intent distribution
                from collections import Counter

                intents = [
                    c.get("intent", "unknown") for c in conversations if c.get("intent")
                ]
                analytics["intent_distribution"] = dict(Counter(intents))

                # Topic distribution
                all_topics = []
                for c in conversations:
                    topics = c.get("topics", [])
                    if isinstance(topics, list):
                        all_topics.extend(topics)
                analytics["topic_distribution"] = dict(Counter(all_topics))

                # Multi-turn and context usage
                analytics["multi_turn_conversations"] = sum(
                    1 for c in conversations if c.get("is_multi_turn", False)
                )
                analytics["context_used_count"] = sum(
                    1 for c in conversations if c.get("context_used", False)
                )

            return analytics

        except Exception as e:
            logger.error(f"Failed to get conversation analytics: {e}")
            return {"error": str(e)}

    async def export_conversations(
        self, filters: Dict[str, Any], format: str = "json"
    ) -> str:
        """
        Export conversations for external systems or backup

        Args:
            filters: Query filters
            format: Export format ('json', 'csv', 'jsonl')

        Returns:
            Exported data as string
        """
        try:
            conversations = await self.query_conversations(
                filters=filters, limit=100000  # Large limit for export
            )

            if format == "json":
                return json.dumps(conversations, indent=2)
            elif format == "jsonl":
                return "\n".join([json.dumps(c) for c in conversations])
            elif format == "csv":
                if not conversations:
                    return "No conversations found"

                import csv
                import io

                output = io.StringIO()
                if conversations:
                    fieldnames = conversations[0].keys()
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    for conv in conversations:
                        # Handle list fields
                        conv_copy = conv.copy()
                        for key, value in conv_copy.items():
                            if isinstance(value, list):
                                conv_copy[key] = ", ".join(map(str, value))
                        writer.writerow(conv_copy)

                return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to export conversations: {e}")
            return f"Export error: {str(e)}"

    async def migrate_legacy_data(self):
        """Migrate data from legacy collection to enhanced collection"""
        try:
            if not self.qdrant_client:
                return

            # Get all data from legacy collection
            legacy_results = await asyncio.to_thread(
                self.qdrant_client.scroll,
                collection_name=self.legacy_collection,
                limit=10000,
                with_payload=True,
                with_vectors=True,
            )

            migrated_count = 0
            for point in legacy_results[0]:
                try:
                    # Convert legacy format to enhanced format
                    legacy_payload = point.payload

                    # Create enhanced entry
                    enhanced_entry = QdrantConversationEntry(
                        id=str(point.id),
                        user_id=legacy_payload.get("user_id", ""),
                        username=legacy_payload.get("username", ""),
                        user_message=legacy_payload.get("message", ""),
                        response=legacy_payload.get("response", ""),
                        timestamp=legacy_payload.get("timestamp", ""),
                        intent=legacy_payload.get("intent"),
                        combined_text=legacy_payload.get("combined_text", ""),
                        topics=self._extract_topics(
                            legacy_payload.get("message", ""),
                            legacy_payload.get("response", ""),
                            legacy_payload.get("intent"),
                        ),
                    )

                    # Store in enhanced collection
                    await asyncio.to_thread(
                        self.qdrant_client.upsert,
                        collection_name=self.collection_name,
                        points=[
                            models.PointStruct(
                                id=enhanced_entry.id,
                                vector=point.vector,
                                payload=asdict(enhanced_entry),
                            )
                        ],
                    )

                    migrated_count += 1

                except Exception as e:
                    logger.warning(f"Failed to migrate point {point.id}: {e}")
                    continue

            logger.info(
                f"Successfully migrated {migrated_count} conversations to enhanced collection"
            )

        except Exception as e:
            logger.warning(f"Migration failed or legacy collection doesn't exist: {e}")


# Global instance
qdrant_conversation_manager = QdrantConversationManager()
