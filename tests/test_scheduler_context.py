from src.ai.mcp_processor import process_for_mcp_ai

def test_scheduler_context():
    test_cases = [
        ("list tasks", "task_scheduler", "list"),
        ("set alarm after 20 seconds", "task_scheduler", "alarm"),
        ("remind me every 25 seconds", "task_scheduler", "reminder"),
        ("cancel task abc123", "task_scheduler", "cancel"),
    ]
    for query, expected_intent, expected_type in test_cases:
        result = process_for_mcp_ai(query)
        intent = result["intent"].value
        scheduler_type = result["context"].get("scheduler_type")
        print(f"Query: {query}")
        print(f"  Intent: {intent} (expected: {expected_intent})")
        print(f"  Scheduler Type: {scheduler_type} (expected: {expected_type})")
        assert intent == expected_intent
        assert scheduler_type == expected_type

if __name__ == "__main__":
    test_scheduler_context()
    print("All scheduler context tests passed!")