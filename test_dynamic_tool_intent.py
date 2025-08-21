# test_dynamic_tool_intent.py - Test dynamic tool intent detection
"""
Test script to verify dynamic tool creation intent detection
"""

from src.ai.mcp_processor import process_for_mcp_ai


def test_dynamic_tool_queries():
    """Test various dynamic tool creation queries"""

    test_queries = [
        "create a simple script to get the current computer name of this server",
        "create a script to check server IP address",
        "generate a bash script for disk usage",
        "write a python script to check memory",
        "make a script to list processes",
        "create automation for system monitoring",
        "generate code to get date time",
        "write a file creation script",
        "automate server status check",
        "create tool for network diagnostics",
        "build script for performance monitoring",
        "develop custom automation",
        "scripting for system admin tasks",
        "programming solution for file operations",
        "execute script to check system resources",
    ]

    print("🧪 Testing Dynamic Tool Creation Intent Detection")
    print("=" * 60)

    for query in test_queries:
        result = process_for_mcp_ai(query)
        intent = result["intent"].value
        context = result["context"]

        print(f"\n📝 Query: '{query}'")
        print(f"🎯 Intent: {intent}")
        print(f"🔍 Keywords found: {context.get('extracted_keywords', [])}")

        if "tool_type" in context:
            print(f"🛠️  Tool Type: {context['tool_type']}")

        if intent == "dynamic_tool":
            print("✅ CORRECT - Dynamic tool intent detected")
        else:
            print(f"❌ WRONG - Expected 'dynamic_tool', got '{intent}'")

        print("-" * 40)

    print("\n" + "=" * 60)
    print("✅ Dynamic Tool Intent Detection Test Complete!")
    print("\n📝 Usage Examples for Dynamic Tool Creation:")
    print("   • 'Create a script to check server IP address'")
    print("   • 'Generate bash script for disk usage monitoring'")
    print("   • 'Write Python code to analyze memory usage'")
    print("   • 'Automate system status checks'")
    print("   • 'Build custom tool for network diagnostics'")


if __name__ == "__main__":
    test_dynamic_tool_queries()
