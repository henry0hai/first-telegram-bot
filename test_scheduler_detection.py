# test_scheduler_detection.py - Test scheduler type detection fix
"""
Test script to verify scheduler type detection is working correctly
"""

from src.ai.mcp_processor import process_for_mcp_ai
from src.services.task_scheduler import task_scheduler


def test_scheduler_detection():
    """Test scheduler type detection for different queries"""

    test_queries = [
        ("Remind me every 25 seconds to stand up", "reminder"),
        (
            "reminder me every 20 seconds and print message: 'check the status of the FAN'",
            "reminder",
        ),
        ("Set alarm after 30 seconds", "alarm"),
        ("Wake me up in 5 minutes", "alarm"),
        ("Notify me to 'Go to the bank' on next week at 9:00 AM", "notification"),
        ("Every hour remind me to drink water", "reminder"),
        ("Remind me every 25 mins to stand up", "reminder"),
        ("Set reminder every 10 minutes", "reminder"),
        ("Cancel my alarm", "cancel"),
        ("List my tasks", "list"),
    ]

    print("🧪 Testing Scheduler Type Detection")
    print("=" * 60)

    for query, expected_type in test_queries:
        # Test MCP processor detection
        mcp_result = process_for_mcp_ai(query)
        mcp_scheduler_type = mcp_result["context"].get("scheduler_type", "unknown")

        # Test task scheduler detection
        task_scheduler_type = task_scheduler._detect_scheduler_type(query.lower())

        print(f"\n📝 Query: '{query}'")
        print(f"🎯 Expected: {expected_type}")
        print(f"🔍 MCP Processor: {mcp_scheduler_type}")
        print(f"🔧 Task Scheduler: {task_scheduler_type}")

        mcp_correct = mcp_scheduler_type == expected_type
        task_correct = task_scheduler_type == expected_type

        if mcp_correct and task_correct:
            print("✅ CORRECT - Both methods detect correctly")
        elif mcp_correct and not task_correct:
            print("⚠️  PARTIAL - MCP correct, Task Scheduler wrong")
        elif not mcp_correct and task_correct:
            print("⚠️  PARTIAL - Task Scheduler correct, MCP wrong")
        else:
            print("❌ WRONG - Both methods detect incorrectly")

        print("-" * 40)

    print("\n✅ Scheduler Type Detection Test Complete!")


if __name__ == "__main__":
    test_scheduler_detection()
