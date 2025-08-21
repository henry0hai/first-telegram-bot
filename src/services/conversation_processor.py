# src/services/conversation_processor.py
"""
Advanced Conversation Processing Service

This service enhances conversation processing by:
1. Chunking long conversations for better memory management
2. Intelligent conversation summarization
3. Context-aware response generation
4. Conversation topic tracking and clustering
"""

import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import re

from src.services.conversation_history import ConversationMessage, conversation_service
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class ConversationChunk:
    """Represents a chunk of conversation for processing"""

    messages: List[ConversationMessage]
    start_time: datetime
    end_time: datetime
    topic_keywords: List[str]
    summary: str
    chunk_id: str


class ConversationProcessor:
    """Advanced conversation processing with chunking and summarization"""

    def __init__(self):
        self.chunk_size = 10  # Messages per chunk
        self.chunk_overlap = 2  # Overlap between chunks
        self.max_context_tokens = 4000  # Approximate token limit for context

    async def process_conversation_for_context(
        self, user_id: str, current_message: str, max_context_length: int = 3000
    ) -> Dict[str, Any]:
        """
        Process conversation history to create optimal context for AI responses

        Returns:
            - context_text: Formatted context for AI
            - context_summary: Brief summary of conversation themes
            - relevant_topics: Topics related to current message
            - confidence_score: Confidence in context relevance
        """
        try:
            # Get conversation context
            context_messages = await conversation_service.get_conversation_context(
                user_id=user_id, current_message=current_message, include_semantic=True
            )

            if not context_messages:
                return {
                    "context_text": "",
                    "context_summary": "No previous conversation history",
                    "relevant_topics": [],
                    "confidence_score": 0.0,
                }

            # Create chunks for better processing
            chunks = self._create_conversation_chunks(context_messages)

            # Analyze topics and themes
            topics = self._extract_conversation_topics(context_messages)

            # Generate smart summary
            summary = await self._generate_conversation_summary(
                context_messages, current_message
            )

            # Create optimized context text
            context_text = self._create_optimized_context(
                context_messages, current_message, max_context_length
            )

            # Calculate confidence score
            confidence = self._calculate_context_confidence(
                context_messages, current_message
            )

            return {
                "context_text": context_text,
                "context_summary": summary,
                "relevant_topics": topics,
                "confidence_score": confidence,
                "chunks_processed": len(chunks),
                "messages_count": len(context_messages),
            }

        except Exception as e:
            logger.error(f"Failed to process conversation for context: {e}")
            return {
                "context_text": "",
                "context_summary": f"Error processing context: {str(e)}",
                "relevant_topics": [],
                "confidence_score": 0.0,
            }

    def _create_conversation_chunks(
        self, messages: List[ConversationMessage]
    ) -> List[ConversationChunk]:
        """Create chunks from conversation messages with overlap"""
        if not messages:
            return []

        chunks = []
        for i in range(0, len(messages), self.chunk_size - self.chunk_overlap):
            chunk_messages = messages[i : i + self.chunk_size]
            if not chunk_messages:
                break

            chunk = ConversationChunk(
                messages=chunk_messages,
                start_time=chunk_messages[0].timestamp,
                end_time=chunk_messages[-1].timestamp,
                topic_keywords=self._extract_chunk_keywords(chunk_messages),
                summary=self._summarize_chunk(chunk_messages),
                chunk_id=f"chunk_{i}_{len(chunk_messages)}",
            )
            chunks.append(chunk)

        return chunks

    def _extract_chunk_keywords(self, messages: List[ConversationMessage]) -> List[str]:
        """Extract keywords from a chunk of messages"""
        try:
            # Combine all text from the chunk
            all_text = " ".join([f"{msg.message} {msg.response}" for msg in messages])

            # Simple keyword extraction (could be enhanced with NLP)
            words = re.findall(r"\b[a-zA-Z]{3,}\b", all_text.lower())

            # Remove common stop words
            stop_words = {
                "the",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
                "from",
                "up",
                "about",
                "into",
                "through",
                "during",
                "before",
                "after",
                "above",
                "below",
                "between",
                "among",
                "this",
                "that",
                "these",
                "those",
                "i",
                "me",
                "my",
                "myself",
                "we",
                "our",
                "you",
                "your",
                "yourself",
                "he",
                "him",
                "his",
                "she",
                "her",
                "it",
                "its",
                "they",
                "them",
                "their",
                "what",
                "which",
                "who",
                "when",
                "where",
                "why",
                "how",
                "all",
                "any",
                "both",
                "each",
                "few",
                "more",
                "most",
                "other",
                "some",
                "such",
                "only",
                "own",
                "same",
                "than",
                "too",
                "very",
                "can",
                "will",
                "just",
                "should",
                "now",
                "get",
                "got",
                "have",
                "has",
                "had",
                "do",
                "does",
                "did",
                "say",
                "said",
                "says",
                "tell",
                "told",
                "ask",
                "asked",
                "give",
                "gave",
                "take",
                "took",
                "come",
                "came",
                "go",
                "went",
                "see",
                "saw",
                "know",
                "knew",
                "think",
                "thought",
                "look",
                "looked",
                "want",
                "wanted",
                "use",
                "used",
                "find",
                "found",
                "work",
                "worked",
            }

            # Filter and count words
            filtered_words = [w for w in words if w not in stop_words and len(w) > 3]
            word_count = Counter(filtered_words)

            # Return top keywords
            return [word for word, count in word_count.most_common(10)]

        except Exception as e:
            logger.warning(f"Failed to extract keywords: {e}")
            return []

    def _summarize_chunk(self, messages: List[ConversationMessage]) -> str:
        """Create a brief summary of a message chunk"""
        if not messages:
            return "Empty chunk"

        try:
            # Simple summarization - could be enhanced with AI
            topics = set()
            for msg in messages:
                # Extract key phrases
                if len(msg.message) > 20:
                    topics.add(msg.message[:50] + "...")

            if not topics:
                return f"Conversation chunk with {len(messages)} messages"

            return f"Discussion about: {', '.join(list(topics)[:3])}"

        except Exception as e:
            return f"Chunk summary error: {str(e)}"

    def _extract_conversation_topics(
        self, messages: List[ConversationMessage]
    ) -> List[str]:
        """Extract main topics from conversation history"""
        try:
            # Combine keywords from all messages
            all_keywords = []
            for msg in messages:
                # Simple topic extraction based on intents and keywords
                if msg.intent:
                    all_keywords.append(msg.intent.lower().replace("_", " "))

                # Extract potential topics from messages
                words = re.findall(r"\b[A-Z][a-z]+\b", msg.message)
                all_keywords.extend([w.lower() for w in words if len(w) > 3])

            # Count and return most common topics
            topic_count = Counter(all_keywords)
            return [topic for topic, count in topic_count.most_common(5)]

        except Exception as e:
            logger.warning(f"Failed to extract topics: {e}")
            return []

    async def _generate_conversation_summary(
        self, messages: List[ConversationMessage], current_message: str
    ) -> str:
        """Generate an intelligent summary of the conversation"""
        try:
            if not messages:
                return "No conversation history"

            # Basic summary components
            total_messages = len(messages)
            time_span = messages[-1].timestamp - messages[0].timestamp

            # Intent distribution
            intents = [msg.intent for msg in messages if msg.intent]
            intent_count = Counter(intents)

            # Time-based grouping
            recent_messages = [
                msg
                for msg in messages
                if (datetime.now(timezone.utc) - msg.timestamp).total_seconds()
                < 3600  # Last hour
            ]

            # Build summary
            summary_parts = [f"Conversation with {total_messages} messages"]

            if time_span.total_seconds() > 3600:
                hours = int(time_span.total_seconds() // 3600)
                summary_parts.append(
                    f"spanning {hours} hour{'s' if hours != 1 else ''}"
                )

            if intent_count:
                top_intent = intent_count.most_common(1)[0][0]
                summary_parts.append(f"mainly about {top_intent.replace('_', ' ')}")

            if recent_messages:
                summary_parts.append(f"with {len(recent_messages)} recent messages")

            return ". ".join(summary_parts) + "."

        except Exception as e:
            logger.warning(f"Failed to generate summary: {e}")
            return "Summary generation failed"

    def _create_optimized_context(
        self, messages: List[ConversationMessage], current_message: str, max_length: int
    ) -> str:
        """Create optimized context text within length limits"""
        try:
            if not messages:
                return ""

            # Sort by relevance score (highest first)
            sorted_messages = sorted(
                messages, key=lambda m: getattr(m, "context_score", 0.0), reverse=True
            )

            context_lines = ["### Relevant Conversation History:"]
            current_length = len(context_lines[0])

            # Add messages until we reach length limit
            for msg in sorted_messages:
                # Format message
                timestamp = msg.timestamp.strftime("%H:%M")
                user_line = f"[{timestamp}] User: {msg.message}"
                bot_line = f"[{timestamp}] Bot: {msg.response}"
                msg_block = f"{user_line}\n{bot_line}\n"

                # Check if we can add this message
                if current_length + len(msg_block) > max_length:
                    break

                context_lines.append(user_line)
                context_lines.append(bot_line)
                context_lines.append("")  # Empty line
                current_length += len(msg_block)

            if len(context_lines) == 1:  # Only header
                return ""

            context_lines.append("### Current Message:")
            context_lines.append(f"User: {current_message}")
            context_lines.append("")

            return "\n".join(context_lines)

        except Exception as e:
            logger.warning(f"Failed to create optimized context: {e}")
            return f"Context error: {str(e)}"

    def _calculate_context_confidence(
        self, messages: List[ConversationMessage], current_message: str
    ) -> float:
        """Calculate confidence score for context relevance"""
        try:
            if not messages:
                return 0.0

            # Factors affecting confidence:
            factors = []

            # 1. Number of messages (more is better, up to a point)
            msg_count_score = min(len(messages) / 10.0, 1.0)
            factors.append(("message_count", msg_count_score, 0.2))

            # 2. Recency (newer messages are more relevant)
            avg_age = sum(
                [
                    (datetime.now(timezone.utc) - msg.timestamp).total_seconds()
                    for msg in messages
                ]
            ) / len(messages)
            recency_score = max(
                0.0, 1.0 - (avg_age / (24 * 3600))
            )  # Decay over 24 hours
            factors.append(("recency", recency_score, 0.3))

            # 3. Semantic relevance (average context scores)
            relevance_scores = [getattr(msg, "context_score", 0.0) for msg in messages]
            avg_relevance = (
                sum(relevance_scores) / len(relevance_scores)
                if relevance_scores
                else 0.0
            )
            factors.append(("semantic_relevance", avg_relevance, 0.4))

            # 4. Intent consistency
            intents = [msg.intent for msg in messages if msg.intent]
            if intents:
                intent_diversity = len(set(intents)) / len(intents)
                intent_score = (
                    1.0 - intent_diversity
                )  # Lower diversity = more focused conversation
            else:
                intent_score = 0.5
            factors.append(("intent_consistency", intent_score, 0.1))

            # Calculate weighted confidence
            confidence = sum([score * weight for _, score, weight in factors])

            logger.debug(f"Confidence calculation: {factors} = {confidence:.3f}")

            return min(confidence, 1.0)

        except Exception as e:
            logger.warning(f"Failed to calculate confidence: {e}")
            return 0.0

    def detect_conversation_patterns(
        self, messages: List[ConversationMessage]
    ) -> Dict[str, Any]:
        """Detect patterns in conversation for insights"""
        try:
            if not messages:
                return {"patterns": [], "insights": []}

            patterns = []
            insights = []

            # Timing patterns
            timestamps = [msg.timestamp for msg in messages]
            if len(timestamps) > 1:
                intervals = [
                    (timestamps[i + 1] - timestamps[i]).total_seconds()
                    for i in range(len(timestamps) - 1)
                ]
                avg_interval = sum(intervals) / len(intervals)

                if avg_interval < 60:
                    patterns.append("rapid_conversation")
                    insights.append("User is actively engaged in rapid conversation")
                elif avg_interval > 3600:
                    patterns.append("sporadic_conversation")
                    insights.append("Conversation happens sporadically over time")

            # Intent patterns
            intents = [msg.intent for msg in messages if msg.intent]
            if intents:
                intent_count = Counter(intents)
                if intent_count.most_common(1)[0][1] > len(intents) * 0.7:
                    patterns.append("focused_topic")
                    insights.append(
                        f"Conversation is focused on {intent_count.most_common(1)[0][0]}"
                    )

            # Message length patterns
            msg_lengths = [len(msg.message) for msg in messages]
            avg_length = sum(msg_lengths) / len(msg_lengths)

            if avg_length > 100:
                patterns.append("detailed_messages")
                insights.append("User provides detailed, lengthy messages")
            elif avg_length < 20:
                patterns.append("brief_messages")
                insights.append("User prefers brief, concise messages")

            return {
                "patterns": patterns,
                "insights": insights,
                "statistics": {
                    "total_messages": len(messages),
                    "avg_message_length": avg_length,
                    "unique_intents": len(set(intents)) if intents else 0,
                    "conversation_span_hours": (
                        (timestamps[-1] - timestamps[0]).total_seconds() / 3600
                        if len(timestamps) > 1
                        else 0
                    ),
                },
            }

        except Exception as e:
            logger.warning(f"Failed to detect patterns: {e}")
            return {"patterns": [], "insights": [], "error": str(e)}


# Global instance
conversation_processor = ConversationProcessor()
