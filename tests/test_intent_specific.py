#!/usr/bin/env python3
"""Test script to verify intent-specific instructions are working correctly"""

import sys
import os

sys.path.append("/Users/henryhai/Projects/Personal/Private/Python/first-telegram-bot")

from src.ai.mcp_processor import MCPAIProcessor


def test_intent_specific_instructions():
    processor = MCPAIProcessor()

    # Test different intents
    test_queries = [
        ("What's the weather in New York?", "weather"),
        ("Show me system status", "system_info"),
        ("Create a Python script to calculate fibonacci", "dynamic_tool"),
        ("Search for latest AI news", "search_query"),
        ("Translate 'hello' to Spanish", "translation_language"),
        (
            "give me top 5 list of news today in Tokyo? I will need more detail as much as possible.",
            "search_query",
        ),
    ]

    print("Testing intent-specific instructions...\n")

    for query, expected_intent in test_queries:
        print(f"Query: {query}")
        print(f"Expected Intent: {expected_intent}")

        result = processor.process_query(query)
        actual_intent = result["intent"].value

        print(f"Detected Intent: {actual_intent}")
        print(f"Match: {'✓' if actual_intent == expected_intent else '✗'}")

        # Show the first 200 characters of the MCP prompt
        mcp_prompt = result["mcp_prompt"]
        print(f"MCP Prompt Preview: {mcp_prompt[:200]}...")

        # Check if prompt contains only relevant instructions
        if expected_intent == "weather" and "system_info" in mcp_prompt:
            print("⚠️  WARNING: Weather query contains system_info instructions!")
        elif expected_intent == "system_info" and "get_weather" in mcp_prompt:
            print("⚠️  WARNING: System info query contains weather instructions!")
        else:
            print("✓ Prompt appears to contain only relevant instructions")

        assert actual_intent == expected_intent, f"Intent mismatch for query: {query}"

        print("-" * 80)


if __name__ == "__main__":
    test_intent_specific_instructions()
