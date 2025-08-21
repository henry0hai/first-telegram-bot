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

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.conversation_history import conversation_service, ConversationMessage
from src.services.conversation_processor import conversation_processor
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ConversationHistoryTester:
    """Test suite for conversation history functionality"""

    def __init__(self):
        self.test_user_id = "test_user_12345"
        self.test_username = "TestUser"
        self.test_results = []

    async def run_all_tests(self):
        """Run all conversation history tests"""
        print("🧪 Starting Conversation History System Tests")
        print("=" * 60)

        try:
            # Initialize the conversation service
            await conversation_service.initialize()
            print("✅ Conversation service initialized")

            # Run individual tests
            await self.test_redis_connection()
            await self.test_qdrant_connection()
            await self.test_conversation_storage()
            await self.test_context_retrieval()
            await self.test_semantic_search()
            await self.test_conversation_clearing()
            await self.test_pattern_detection()
            await self.test_conversation_processor()

            # Print summary
            self.print_test_summary()

        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            print(f"❌ Test suite failed: {e}")

    async def test_redis_connection(self):
        """Test Redis connection and basic operations"""
        try:
            if conversation_service.redis_client:
                # Test basic Redis operation
                test_key = f"test:{self.test_user_id}"
                await conversation_service.redis_client.set(
                    test_key, "test_value", ex=60
                )
                result = await conversation_service.redis_client.get(test_key)
                await conversation_service.redis_client.delete(test_key)

                if result and result.decode() == "test_value":
                    print("✅ Redis connection and operations working")
                    self.test_results.append(
                        ("Redis Connection", True, "Connected and operational")
                    )
                else:
                    print("❌ Redis operations failed")
                    self.test_results.append(
                        ("Redis Connection", False, "Operations failed")
                    )
            else:
                print("⚠️  Redis not configured - caching will be limited")
                self.test_results.append(("Redis Connection", False, "Not configured"))

        except Exception as e:
            print(f"❌ Redis connection test failed: {e}")
            self.test_results.append(("Redis Connection", False, str(e)))

    async def test_qdrant_connection(self):
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
                    self.test_results.append(
                        ("Qdrant Connection", True, "Collection exists")
                    )
                else:
                    print("⚠️  Qdrant collection not found, creating...")
                    await conversation_service._ensure_qdrant_collection()
                    self.test_results.append(
                        ("Qdrant Connection", True, "Collection created")
                    )
            else:
                print("⚠️  Qdrant not configured - RAG features will be limited")
                self.test_results.append(("Qdrant Connection", False, "Not configured"))

        except Exception as e:
            print(f"❌ Qdrant connection test failed: {e}")
            self.test_results.append(("Qdrant Connection", False, str(e)))

    async def test_conversation_storage(self):
        """Test storing and retrieving conversations"""
        try:
            # Clear any existing test data
            await conversation_service.clear_conversation_history(self.test_user_id)

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
                    user_id=self.test_user_id,
                    username=self.test_username,
                    user_message=user_msg,
                    bot_response=bot_response,
                    intent=intent,
                )
                await asyncio.sleep(0.1)  # Small delay to ensure different timestamps

            print("✅ Test conversations stored successfully")
            self.test_results.append(
                (
                    "Conversation Storage",
                    True,
                    f"Stored {len(test_conversations)} conversations",
                )
            )

        except Exception as e:
            print(f"❌ Conversation storage test failed: {e}")
            self.test_results.append(("Conversation Storage", False, str(e)))

    async def test_context_retrieval(self):
        """Test retrieving conversation context"""
        try:
            # Test context retrieval
            context_messages = await conversation_service.get_conversation_context(
                user_id=self.test_user_id,
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
                    self.test_results.append(
                        (
                            "Context Retrieval",
                            True,
                            f"Retrieved {len(context_messages)} messages",
                        )
                    )
                else:
                    print("❌ Context formatting failed")
                    self.test_results.append(
                        ("Context Retrieval", False, "Formatting failed")
                    )
            else:
                print("⚠️  No context messages retrieved")
                self.test_results.append(
                    ("Context Retrieval", False, "No messages retrieved")
                )

        except Exception as e:
            print(f"❌ Context retrieval test failed: {e}")
            self.test_results.append(("Context Retrieval", False, str(e)))

    async def test_semantic_search(self):
        """Test semantic search functionality"""
        try:
            if not conversation_service.embedding_model:
                print("⚠️  Embedding model not loaded - skipping semantic search test")
                self.test_results.append(
                    ("Semantic Search", False, "Embedding model not available")
                )
                return

            # Test semantic search
            semantic_messages = await conversation_service._get_semantic_context(
                user_id=self.test_user_id,
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
                self.test_results.append(
                    (
                        "Semantic Search",
                        True,
                        f"Found {len(semantic_messages)} relevant messages",
                    )
                )
            else:
                print("⚠️  No semantically similar messages found")
                self.test_results.append(
                    ("Semantic Search", False, "No similar messages found")
                )

        except Exception as e:
            print(f"❌ Semantic search test failed: {e}")
            self.test_results.append(("Semantic Search", False, str(e)))

    async def test_conversation_clearing(self):
        """Test clearing conversation history"""
        try:
            # Get summary before clearing
            summary_before = await conversation_service.get_conversation_summary(
                self.test_user_id
            )

            # Clear conversations
            await conversation_service.clear_conversation_history(self.test_user_id)

            # Check if cleared
            summary_after = await conversation_service.get_conversation_summary(
                self.test_user_id
            )

            if summary_after.get("recent_messages_count", 0) == 0:
                print("✅ Conversation clearing working")
                self.test_results.append(
                    ("Conversation Clearing", True, "History cleared successfully")
                )
            else:
                print("❌ Conversation clearing failed")
                self.test_results.append(
                    ("Conversation Clearing", False, "History not cleared")
                )

        except Exception as e:
            print(f"❌ Conversation clearing test failed: {e}")
            self.test_results.append(("Conversation Clearing", False, str(e)))

    async def test_pattern_detection(self):
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
                    user_id=self.test_user_id,
                    username=self.test_username,
                    message=user_msg,
                    response=bot_response,
                    timestamp=base_time + timedelta(seconds=i * 30),  # 30 seconds apart
                    intent=intent,
                )
                test_messages.append(msg)

            # Detect patterns
            patterns = conversation_processor.detect_conversation_patterns(
                test_messages
            )

            if patterns and patterns.get("patterns"):
                print(f"✅ Pattern detection working - found: {patterns['patterns']}")
                self.test_results.append(
                    ("Pattern Detection", True, f"Detected: {patterns['patterns']}")
                )
            else:
                print("⚠️  No patterns detected")
                self.test_results.append(
                    ("Pattern Detection", False, "No patterns found")
                )

        except Exception as e:
            print(f"❌ Pattern detection test failed: {e}")
            self.test_results.append(("Pattern Detection", False, str(e)))

    async def test_conversation_processor(self):
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
                    user_id=self.test_user_id,
                    username=self.test_username,
                    user_message=user_msg,
                    bot_response=bot_response,
                    intent=intent,
                )

            # Test conversation processor
            context_data = (
                await conversation_processor.process_conversation_for_context(
                    user_id=self.test_user_id,
                    current_message="Can you help me with Python classes?",
                    max_context_length=2000,
                )
            )

            if context_data and context_data.get("context_text"):
                confidence = context_data.get("confidence_score", 0.0)
                topics = context_data.get("relevant_topics", [])
                print(
                    f"✅ Conversation processor working - confidence: {confidence:.2f}, topics: {topics}"
                )
                self.test_results.append(
                    ("Conversation Processor", True, f"Confidence: {confidence:.2f}")
                )
            else:
                print("❌ Conversation processor failed to generate context")
                self.test_results.append(
                    ("Conversation Processor", False, "No context generated")
                )

        except Exception as e:
            print(f"❌ Conversation processor test failed: {e}")
            self.test_results.append(("Conversation Processor", False, str(e)))

    def print_test_summary(self):
        """Print a summary of all test results"""
        print("\n" + "=" * 60)
        print("🧪 TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)

        print(f"Tests Passed: {passed}/{total}")
        print("-" * 40)

        for test_name, success, details in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status:<10} {test_name:<25} {details}")

        print("\n" + "=" * 60)

        if passed == total:
            print(
                "🎉 ALL TESTS PASSED! Your conversation history system is ready to use."
            )
        else:
            print(
                f"⚠️  {total - passed} tests failed. Check the configuration and try again."
            )

        print("\n📝 Next Steps:")
        print("1. Make sure Redis is running (redis-server)")
        print("2. Make sure Qdrant is running (docker or local)")
        print("3. Update your .env file with REDIS_URL and QDRANT_API_URL")
        print("4. Test with the Telegram bot")


async def main():
    """Main test runner"""
    tester = ConversationHistoryTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
