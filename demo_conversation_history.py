#!/usr/bin/env python3
"""
Conversation History System Demo

This demonstrates the conversation history system with example usage.
Run this after setting up Redis and Qdrant to see how it works.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.conversation_history import conversation_service
from src.services.conversation_processor import conversation_processor


async def demo_conversation_flow():
    """Demonstrate a typical conversation flow"""
    print("🤖 Conversation History System Demo")
    print("=" * 50)

    # Initialize the service
    print("Initializing conversation service...")
    await conversation_service.initialize()
    print("✅ Service initialized\n")

    # Demo user
    user_id = "demo_user_123"
    username = "DemoUser"

    # Clear any existing demo data
    await conversation_service.clear_conversation_history(user_id)
    print(f"🧹 Cleared any existing history for {username}\n")

    # Simulate a conversation flow
    conversation_flow = [
        {
            "user": "Hello, I'm new to programming",
            "bot": "Welcome! Programming is exciting. What language interests you?",
            "intent": "UNKNOWN",
        },
        {
            "user": "I heard Python is good for beginners",
            "bot": "Absolutely! Python is perfect for beginners. It has clean, readable syntax.",
            "intent": "SEARCH_QUERY",
        },
        {
            "user": "Can you show me a simple example?",
            "bot": "Sure! Here's a simple Python program:\n\nprint('Hello, World!')\n\nThis prints 'Hello, World!' to the screen.",
            "intent": "SEARCH_QUERY",
        },
        {
            "user": "What about variables?",
            "bot": "Variables store data. In Python: name = 'John' or age = 25. Very simple!",
            "intent": "SEARCH_QUERY",
        },
        {
            "user": "How do I create functions?",
            "bot": "Functions use 'def':\n\ndef greet(name):\n    return f'Hello, {name}!'\n\nprint(greet('Alice'))",
            "intent": "SEARCH_QUERY",
        },
    ]

    print("📝 Simulating conversation...")

    # Store the conversation with small delays
    for i, exchange in enumerate(conversation_flow):
        await conversation_service.add_conversation(
            user_id=user_id,
            username=username,
            user_message=exchange["user"],
            bot_response=exchange["bot"],
            intent=exchange["intent"],
        )

        print(f"  {i+1}. User: {exchange['user'][:60]}...")
        print(f"     Bot:  {exchange['bot'][:60]}...")

        # Small delay to ensure different timestamps
        await asyncio.sleep(0.2)

    print(f"\n✅ Stored {len(conversation_flow)} conversation exchanges\n")

    # Now demonstrate context retrieval for a new message
    print("🔍 Testing Context Retrieval")
    print("-" * 30)

    new_message = (
        "Can you explain more about Python functions and give me another example?"
    )

    print(f"New user message: {new_message}")
    print()

    # Get context using the basic service
    print("📚 Basic Context Retrieval:")
    context_messages = await conversation_service.get_conversation_context(
        user_id=user_id, current_message=new_message, include_semantic=True
    )

    print(f"  - Retrieved {len(context_messages)} relevant messages")
    if context_messages:
        for msg in context_messages[-3:]:  # Show last 3
            score = getattr(msg, "context_score", 0.0)
            print(f"  - Score: {score:.3f} | {msg.message[:50]}...")

    # Format context for AI
    formatted_context = conversation_service.format_context_for_ai(context_messages)
    print(f"  - Formatted context length: {len(formatted_context)} characters\n")

    # Get advanced context using the processor
    print("🧠 Advanced Context Processing:")
    context_data = await conversation_processor.process_conversation_for_context(
        user_id=user_id, current_message=new_message, max_context_length=2000
    )

    print(f"  - Context confidence: {context_data.get('confidence_score', 0.0):.2f}")
    print(f"  - Relevant topics: {context_data.get('relevant_topics', [])}")
    print(f"  - Context summary: {context_data.get('context_summary', '')}")
    print(f"  - Messages processed: {context_data.get('messages_count', 0)}")
    print(f"  - Chunks created: {context_data.get('chunks_processed', 0)}")

    # Show how the context would be included in an AI prompt
    print("\n📤 Example AI Prompt with Context:")
    print("-" * 40)
    context_text = context_data.get("context_text", "")
    if context_text:
        # Truncate for display
        display_context = (
            context_text[:500] + "..." if len(context_text) > 500 else context_text
        )
        print(display_context)
        print(f"\n[Context length: {len(context_text)} characters]")
    else:
        print("No context would be included (confidence too low)")

    # Demonstrate conversation summary
    print("\n📊 Conversation Summary:")
    print("-" * 25)
    summary = await conversation_service.get_conversation_summary(user_id)
    print(f"  - Recent messages: {summary.get('recent_messages_count', 0)}")
    print(f"  - Total messages: {summary.get('total_messages_count', 0)}")
    if summary.get("last_conversation"):
        print(f"  - Last conversation: {summary.get('last_conversation')}")

    # Demonstrate pattern detection
    print("\n🔍 Pattern Detection:")
    print("-" * 20)
    patterns = conversation_processor.detect_conversation_patterns(context_messages)
    if patterns.get("patterns"):
        print(f"  - Detected patterns: {patterns['patterns']}")
    if patterns.get("insights"):
        for insight in patterns["insights"]:
            print(f"  - Insight: {insight}")

    stats = patterns.get("statistics", {})
    if stats:
        print(
            f"  - Average message length: {stats.get('avg_message_length', 0):.1f} chars"
        )
        print(
            f"  - Conversation span: {stats.get('conversation_span_hours', 0):.2f} hours"
        )
        print(f"  - Unique intents: {stats.get('unique_intents', 0)}")

    # Demonstrate clear intent detection
    print("\n🧹 Clear Intent Detection:")
    print("-" * 25)

    clear_messages = [
        "clear all conversation",
        "forget everything we discussed",
        "start fresh please",
        "I want to reset our chat",
        "This is not a clear message",
    ]

    for msg in clear_messages:
        is_clear = conversation_service.detect_clear_intent(msg)
        status = "✅ CLEAR INTENT" if is_clear else "❌ NOT CLEAR"
        print(f"  {status}: '{msg}'")

    print("\n🎉 Demo completed successfully!")
    print("\nTo test with your bot:")
    print("1. Start Redis: redis-server")
    print("2. Start Qdrant: docker run -p 6333:6333 qdrant/qdrant")
    print("3. Update your .env with REDIS_URL and QDRANT_API_URL")
    print("4. Run your bot and try these commands:")
    print("   - /conversation_status")
    print("   - /clear_conversation")
    print("   - Chat normally and see how context is maintained!")


if __name__ == "__main__":
    asyncio.run(demo_conversation_flow())
