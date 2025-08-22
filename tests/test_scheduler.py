# test_scheduler.py - Test script for the new scheduler functionality
"""
Test script to demonstrate the new Task Scheduler functionality.

This script shows how the scheduler can handle various natural language commands:
1. One-time alarms (after X time)
2. Recurring reminders (every X time)
3. Scheduled notifications (at specific times)
4. Task management (list, cancel)
"""

from src.services.task_scheduler import TaskScheduler
import datetime


def test_scheduler():
    """Test the scheduler functionality"""
    scheduler = TaskScheduler()

    print("🧪 Testing Task Scheduler Functionality\n")
    print("=" * 50)

    # Test 1: Parse time delays
    print("\n1️⃣ Testing Time Delay Parsing:")
    test_phrases = [
        "set alarm after 20 seconds",
        "wake me up in 30 minutes",
        "remind me in 2 hours",
        "notify me after 5 mins",
    ]

    for phrase in test_phrases:
        delay = scheduler.parse_time_delay(phrase)
        print(f"   '{phrase}' -> {delay} seconds")

    # Test 2: Parse recurring intervals
    print("\n2️⃣ Testing Recurring Interval Parsing:")
    test_phrases = [
        "remind me every 25 minutes",
        "alert me every hour",
        "notify me every 30 seconds",
        "every 2 hours",
    ]

    for phrase in test_phrases:
        interval = scheduler.parse_recurring_interval(phrase)
        print(f"   '{phrase}' -> {interval} seconds")

    # Test 3: Parse absolute times
    print("\n3️⃣ Testing Absolute Time Parsing:")
    test_phrases = [
        "next week at 9:00 AM",
        "at 2:30 PM",
        "tomorrow at 8:00",
        "at 14:00",
    ]

    for phrase in test_phrases:
        abs_time = scheduler.parse_absolute_time(phrase)
        print(f"   '{phrase}' -> {abs_time}")

    # Test 4: Extract custom messages
    print("\n4️⃣ Testing Message Extraction:")
    test_phrases = [
        'notify me to "Go to the bank" next week at 9:00',
        "remind me to stand up every 25 minutes",
        "wake me up after 30 minutes",
        "alert me about the meeting tomorrow",
    ]

    for phrase in test_phrases:
        message = scheduler.extract_task_message(phrase)
        print(f"   '{phrase}' -> '{message}'")

    # Test 5: Scheduler type detection and MCP intent integration
    print("\n5️⃣ Testing Scheduler Type Detection & MCP Integration:")

    # Import the MCP processor to test integration
    from src.ai.mcp_processor import MCPAIProcessor

    mcp_processor = MCPAIProcessor()

    test_phrases = [
        "set alarm after 20 seconds",
        "remind me every hour",
        "notify me next week at 9:00",
        "cancel task abc123",
        "list my tasks",
    ]

    for phrase in test_phrases:
        # Test scheduler type detection
        scheduler_type = scheduler._detect_scheduler_type(phrase.lower())

        # Test MCP intent detection
        result = mcp_processor.process_query(phrase)
        intent = result["intent"].value
        context = result["context"]
        mcp_scheduler_type = context.get("scheduler_type", "unknown")

        print(f"   '{phrase}'")
        print(f"     → Scheduler Type: {scheduler_type}")
        print(f"     → MCP Intent: {intent}")
        print(f"     → MCP Scheduler Type: {mcp_scheduler_type}")
        print(f"     → Match: {'✅' if scheduler_type == mcp_scheduler_type else '❌'}")

        # Show snippet of MCP prompt to verify context hints
        mcp_prompt = result["mcp_prompt"]
        if "→ This is a" in mcp_prompt:
            hint_line = [
                line for line in mcp_prompt.split("\n") if "→ This is a" in line
            ][0]
            print(f"     → Hint: {hint_line}")
        print()

    print("\n" + "=" * 50)
    print("✅ Task Scheduler Test Complete!")
    print("\n📝 Usage Examples:")
    print("   • 'Set alarm after 20 seconds'")
    print("   • 'Remind me every 25 minutes to stand up and take water'")
    print("   • 'Notify me to \"Go to the bank\" next week at 9:00 AM'")
    print("   • '/tasks' or 'list my tasks'")
    print("   • '/cancel task_id' or 'cancel task task_id'")


if __name__ == "__main__":
    test_scheduler()
