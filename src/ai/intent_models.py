# src/ai/intent_models.py
from enum import Enum

class IntentType(Enum):
    """Intent types for MCP AI processing"""

    RAG_QUERY = "rag_query"
    SEARCH_QUERY = "search_query"
    SYSTEM_INFO = "system_info"
    DYNAMIC_TOOL = "dynamic_tool"
    WEATHER = "weather"
    BUDGET_FINANCE = "budget_finance"
    EMAIL_COMMUNICATION = "email_communication"
    TRANSLATION_LANGUAGE = "translation_language"
    TASK_SCHEDULER = "task_scheduler"
    UNKNOWN = "unknown"
