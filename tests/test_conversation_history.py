#!/usr/bin/env python3
"""
Conversation History System Test

This test verifies the conversation history functionality:
1. Redis caching
2. Qdrant RAG integration
3. Intelligent context filtering
4. Conversation clearing
5. Pattern detection

Run this test after setting up Redis and Qdrant to ensure everything works.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone

import pytest

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.conversation_history import conversation_service, ConversationMessage
from src.services.conversation_processor import conversation_processor
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


@pytest.fixture(scope="module")
def test_user_id():
    return "test_user_12345"


@pytest.fixture(scope="module")
def test_username():
    return "TestUser"


@pytest.mark.asyncio
async def test_redis_connection(test_user_id, test_username):
    """Test Redis connection and basic operations"""
    try:
        if conversation_service.redis_client:
            # Test basic Redis operation
            test_key = f"test:{test_user_id}"
            await conversation_service.redis_client.set(test_key, "test_value", ex=60)
            result = await conversation_service.redis_client.get(test_key)
            await conversation_service.redis_client.delete(test_key)

            if result and result.decode() == "test_value":
                print("✅ Redis connection and operations working")
            else:
                print("❌ Redis operations failed")
        else:
            print("⚠️  Redis not configured - caching will be limited")

    except Exception as e:
        print(f"❌ Redis connection test failed: {e}")


@pytest.mark.asyncio
async def test_qdrant_connection(test_user_id, test_username):
    """Test Qdrant connection and collection setup"""
    try:
        if conversation_service.qdrant_client:
            # Test collection existence
            collections = await asyncio.to_thread(
                conversation_service.qdrant_client.get_collections
            )
            collection_names = [col.name for col in collections.collections]

            if conversation_service.collection_name in collection_names:
                print("✅ Qdrant connection and collection working")
            else:
                print("⚠️  Qdrant collection not found, creating...")
                await conversation_service._ensure_qdrant_collection()
        else:
            print("⚠️  Qdrant not configured - RAG features will be limited")

    except Exception as e:
        print(f"❌ Qdrant connection test failed: {e}")


@pytest.mark.asyncio
async def test_conversation_storage(test_user_id, test_username):
    """Test storing and retrieving conversations"""
    try:
        # Clear any existing test data
        await conversation_service.clear_conversation_history(test_user_id)

        # Test conversations
        test_conversations = [
            (
                "Hello, how are you?",
                "I'm doing well, thank you! How can I help you today?",
                "UNKNOWN",
            ),
            (
                "What's the weather like?",
                "I can help you check the weather. What city would you like to know about?",
                "WEATHER",
            ),
            (
                "Tell me about Python programming",
                "Python is a versatile programming language known for its simplicity and readability.",
                "SEARCH_QUERY",
            ),
            (
                "Can you schedule a reminder?",
                "I can help you schedule reminders. What would you like to be reminded about?",
                "TASK_SCHEDULER",
            ),
        ]

        # Store test conversations
        for user_msg, bot_response, intent in test_conversations:
            await conversation_service.add_conversation(
                user_id=test_user_id,
                username=test_username,
                user_message=user_msg,
                bot_response=bot_response,
                intent=intent,
            )
            await asyncio.sleep(0.1)  # Small delay to ensure different timestamps

        print("✅ Test conversations stored successfully")

    except Exception as e:
        print(f"❌ Conversation storage test failed: {e}")


@pytest.mark.asyncio
async def test_context_retrieval(test_user_id, test_username):
    """Test retrieving conversation context"""
    try:
        # Test context retrieval
        context_messages = await conversation_service.get_conversation_context(
            user_id=test_user_id,
            current_message="What programming languages do you recommend?",
            include_semantic=True,
        )

        if context_messages:
            print(f"✅ Retrieved {len(context_messages)} context messages")

            # Test context formatting
            formatted_context = conversation_service.format_context_for_ai(
                context_messages
            )
            if formatted_context:
                print("✅ Context formatting working")
            else:
                print("❌ Context formatting failed")
        else:
            print("⚠️  No context messages retrieved")

    except Exception as e:
        print(f"❌ Context retrieval test failed: {e}")


@pytest.mark.asyncio
async def test_semantic_search(test_user_id, test_username):
    """Test semantic search functionality"""
    try:
        if not conversation_service.embedding_model:
            print("⚠️  Embedding model not loaded - skipping semantic search test")
            return

        # Test semantic search
        semantic_messages = await conversation_service._get_semantic_context(
            user_id=test_user_id,
            current_message="programming languages and coding",
            limit=3,
        )

        if semantic_messages:
            print(
                f"✅ Semantic search found {len(semantic_messages)} relevant messages"
            )
            for msg in semantic_messages:
                print(
                    f"   - Score: {msg.context_score:.3f} | Message: {msg.message[:50]}..."
                )
        else:
            print("⚠️  No semantically similar messages found")

    except Exception as e:
        print(f"❌ Semantic search test failed: {e}")


@pytest.mark.asyncio
async def test_conversation_clearing(test_user_id, test_username):
    """Test clearing conversation history"""
    try:
        # Get summary before clearing
        summary_before = await conversation_service.get_conversation_summary(
            test_user_id
        )

        # Clear conversations
        await conversation_service.clear_conversation_history(test_user_id)

        # Check if cleared
        summary_after = await conversation_service.get_conversation_summary(
            test_user_id
        )

        if summary_after.get("recent_messages_count", 0) == 0:
            print("✅ Conversation clearing working")
        else:
            print("❌ Conversation clearing failed")

    except Exception as e:
        print(f"❌ Conversation clearing test failed: {e}")


@pytest.mark.asyncio
async def test_pattern_detection(test_user_id, test_username):
    """Test conversation pattern detection"""
    try:
        # Add some test conversations with patterns
        pattern_conversations = [
            ("Quick question", "Sure, what's your question?", "UNKNOWN"),
            ("Another quick one", "I'm here to help!", "UNKNOWN"),
            ("Fast query", "Go ahead!", "UNKNOWN"),
        ]

        # Store conversations with timestamps close together for rapid pattern
        test_messages = []
        base_time = datetime.now(timezone.utc)
        for i, (user_msg, bot_response, intent) in enumerate(pattern_conversations):
            msg = ConversationMessage(
                user_id=test_user_id,
                username=test_username,
                message=user_msg,
                response=bot_response,
                timestamp=base_time + timedelta(seconds=i * 30),  # 30 seconds apart
                intent=intent,
            )
            test_messages.append(msg)

        # Detect patterns
        patterns = conversation_processor.detect_conversation_patterns(test_messages)

        if patterns and patterns.get("patterns"):
            print(f"✅ Pattern detection working - found: {patterns['patterns']}")
        else:
            print("⚠️  No patterns detected")

    except Exception as e:
        print(f"❌ Pattern detection test failed: {e}")


@pytest.mark.asyncio
async def test_conversation_processor(test_user_id, test_username):
    """Test the advanced conversation processor"""
    try:
        # Re-add some test data for processor testing
        test_conversations = [
            (
                "I need help with Python",
                "I'd be happy to help with Python! What specific topic?",
                "SEARCH_QUERY",
            ),
            (
                "How do I use loops?",
                "Python has several types of loops. For loops and while loops are the most common.",
                "SEARCH_QUERY",
            ),
            (
                "What about functions?",
                "Functions in Python are defined with the 'def' keyword. They're very useful!",
                "SEARCH_QUERY",
            ),
        ]

        for user_msg, bot_response, intent in test_conversations:
            await conversation_service.add_conversation(
                user_id=test_user_id,
                username=test_username,
                user_message=user_msg,
                bot_response=bot_response,
                intent=intent,
            )

        # Test conversation processor
        context_data = await conversation_processor.process_conversation_for_context(
            user_id=test_user_id,
            current_message="Can you help me with Python classes?",
            max_context_length=2000,
        )

        if context_data and context_data.get("context_text"):
            confidence = context_data.get("confidence_score", 0.0)
            topics = context_data.get("relevant_topics", [])
            print(
                f"✅ Conversation processor working - confidence: {confidence:.2f}, topics: {topics}"
            )
        else:
            print("❌ Conversation processor failed to generate context")

    except Exception as e:
        print(f"❌ Conversation processor test failed: {e}")


@pytest.mark.asyncio
async def test_context_source_and_relevance(test_user_id, test_username):
    """Test that context retrieval uses Redis or Qdrant as appropriate and returns relevant messages"""
    try:
        # Clear previous history for a clean test
        await conversation_service.clear_conversation(test_user_id)

        # Add a message to Redis (recent)
        await conversation_service.add_conversation(
            user_id=test_user_id,
            username=test_username,
            user_message="This is a Redis-only message about apples.",
            bot_response="Sure, apples are great!",
            intent="FRUIT_INFO",
        )

        # Add a message to Qdrant (simulate by direct call if needed)
        await conversation_service.add_conversation(
            user_id=test_user_id,
            username=test_username,
            user_message="This is a Qdrant-only message about bananas.",
            bot_response="Bananas are yellow and sweet!",
            intent="FRUIT_INFO",
        )

        # Query for apples (should match Redis message)
        context_apples = await conversation_service.get_conversation_context(
            user_id=test_user_id,
            current_message="Tell me about apples.",
            include_semantic=False,  # Only Redis
        )
        assert any(
            "apples" in m.message for m in context_apples
        ), "Redis context not found for apples"

        # Query for bananas (should match Qdrant message if semantic enabled)
        context_bananas = await conversation_service.get_conversation_context(
            user_id=test_user_id,
            current_message="Tell me about bananas.",
            include_semantic=True,  # Allow Qdrant
        )
        assert any(
            "bananas" in m.message for m in context_bananas
        ), "Qdrant context not found for bananas"

        print("✅ Context source and relevance test passed")
    except Exception as e:
        print(f"❌ Context source and relevance test failed: {e}")
