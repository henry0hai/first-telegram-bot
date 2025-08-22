#!/usr/bin/env python3
"""Test the specific scheduler issues mentioned by user"""

import sys
import os

sys.path.append("/Users/henryhai/Projects/Personal/Private/Python/first-telegram-bot")

from src.ai.mcp_processor import MCPAIProcessor
from src.services.task_scheduler import TaskScheduler


def test_specific_issues():
    mcp_processor = MCPAIProcessor()
    task_scheduler = TaskScheduler()

    problem_queries = [
        "set alarm after 20 seconds",  # Should be ALARM, getting REMINDER
        "Remind me every 25 seconds",  # Should be REMINDER, getting system info
        'Remind me every 25 seconds with text "Checking this one"',
        "list tasks",
    ]

    print("🐛 Testing Specific Scheduler Issues\n")

    for query in problem_queries:
        print(f"Query: '{query}'")

        # Test MCP processor
        mcp_result = mcp_processor.process_query(query)
        mcp_intent = mcp_result["intent"].value
        mcp_scheduler_type = mcp_result["context"].get("scheduler_type", "unknown")

        # Test task scheduler's own detection
        task_scheduler_type = task_scheduler._detect_scheduler_type(query.lower())

        # Test parsing methods
        delay = task_scheduler.parse_time_delay(query)
        interval = task_scheduler.parse_recurring_interval(query)

        print(f"  MCP Intent: {mcp_intent}")
        print(f"  MCP Scheduler Type: {mcp_scheduler_type}")
        print(f"  Task Scheduler Type: {task_scheduler_type}")
        print(f"  Parse Time Delay: {delay} seconds")
        print(f"  Parse Recurring Interval: {interval} seconds")

        # Check what create_* method would return
        if mcp_scheduler_type == "alarm":
            can_create_alarm = delay is not None
            print(f"  Can Create Alarm: {can_create_alarm}")
        elif mcp_scheduler_type == "reminder":
            can_create_reminder = interval is not None
            print(f"  Can Create Reminder: {can_create_reminder}")

        print("  " + "-" * 50)


if __name__ == "__main__":
    test_specific_issues()
