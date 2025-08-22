#!/usr/bin/env python3
"""
Test the enhanced conversation system with comprehensive Qdrant storage
"""

import asyncio
import uuid
import pytest
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_enhanced_conversation():
    """Test enhanced conversation storage and MCP server compatibility"""
    from config.config import get_logger
    from src.services.conversation_history import conversation_service
    from src.services.qdrant_conversation_manager import qdrant_conversation_manager

    logger = get_logger("test_enhanced")
    logger.info("🧪 Testing Enhanced Conversation System")

    # Initialize the enhanced manager
    print("\n🔧 Initializing Enhanced Qdrant Manager...")
    await qdrant_conversation_manager.initialize()
    print("✅ Enhanced Qdrant Manager initialized")

    # Test data
    user_id = "test_user_123"
    username = "test_user"
    test_conversations = [
        {
            "user_message": "Hello, I need help with Python programming",
            "bot_response": "I'd be happy to help you with Python programming! What specific topic would you like to learn about?",
            "intent": "programming_help",
        },
        {
            "user_message": "I want to learn about web scraping",
            "bot_response": "Web scraping is a great skill! Let me explain the key libraries and techniques like requests, BeautifulSoup, and scrapy.",
            "intent": "programming_tutorial",
        },
    ]

    print("\n📝 Testing Enhanced Storage...")

    # Store conversations in enhanced Qdrant
    session_id = str(uuid.uuid4())

    for turn, conv in enumerate(test_conversations):
        conversation_id = await qdrant_conversation_manager.store_conversation(
            user_id=user_id,
            username=username,
            user_message=conv["user_message"],
            bot_response=conv["bot_response"],
            session_id=session_id,
            intent=conv["intent"],
            conversation_turn=turn + 1,
            context_used=turn > 0,  # Second message uses context from first
        )
        print(f"✅ Stored conversation {turn + 1} with ID: {conversation_id[:8]}...")

    print("\n🔍 Testing Query Capabilities...")

    # Test querying conversations - use filters dict
    conversations = await qdrant_conversation_manager.query_conversations(
        filters={"user_id": user_id}, limit=10
    )
    print(f"✅ Retrieved {len(conversations)} conversations for user {user_id}")

    # Test semantic search
    search_results = await qdrant_conversation_manager.semantic_search(
        query="python programming help", user_id=user_id, limit=5
    )
    print(f"✅ Semantic search found {len(search_results)} relevant conversations")

    # Test analytics
    analytics = await qdrant_conversation_manager.get_conversation_analytics(user_id)
    print(f"✅ Analytics: {analytics}")

    print("\n📊 Testing MCP Server Export...")

    # Test export for MCP server - use filters dict
    export_data = await qdrant_conversation_manager.export_conversations(
        filters={"user_id": user_id, "session_id": session_id}
    )
    print(
        f"✅ Exported conversations: {len(export_data) if isinstance(export_data, list) else 'JSON string'}"
    )

    # Parse export data if it's a JSON string
    if isinstance(export_data, str):
        import json

        try:
            parsed_data = json.loads(export_data)
            if parsed_data and isinstance(parsed_data, list):
                sample_entry = parsed_data[0]
                print(f"📋 Sample entry fields: {list(sample_entry.keys())}")
                print(f"   - User ID: {sample_entry.get('user_id')}")
                print(f"   - Intent: {sample_entry.get('intent')}")
                print(f"   - Topics: {sample_entry.get('topics')}")
                print(f"   - Session: {sample_entry.get('session_id')}")
        except json.JSONDecodeError:
            print(f"📋 Export data (first 200 chars): {export_data[:200]}...")
    elif export_data:
        sample_entry = export_data[0] if isinstance(export_data, list) else export_data
        print(
            f"📋 Sample entry fields: {list(sample_entry.keys()) if hasattr(sample_entry, 'keys') else 'N/A'}"
        )

    print("\n✨ Enhanced conversation system is ready for MCP server integration!")
    print("🔧 MCP server can now query Qdrant directly using:")
    print("   - user_id for user-specific conversations")
    print("   - session_id for specific sessions")
    print("   - intent for conversation categorization")
    print("   - topics for semantic filtering")
    print("   - timestamp for temporal queries")


if __name__ == "__main__":
    asyncio.run(test_enhanced_conversation())
