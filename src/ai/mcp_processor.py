# src/ai/mcp_ai.py
import re
from enum import Enum
from typing import Dict, List, Optional, Tuple
from src.utils.logging_utils import get_logger
from src.ai.mcp_instructions import get_mcp_instructions, get_intent_guidance

logger = get_logger(__name__)


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


class MCPAIProcessor:
    """Pre-processor for MCP AI to detect context and intent"""

    def __init__(self):
        # Keywords for different intent types
        self.rag_keywords = [
            "document",
            "file",
            "pdf",
            "content",
            "uploaded",
            "analyze",
            "summarize",
            "explain",
            "what does",
            "according to",
            "based on",
            "from the document",
            "in the file",
            "mcp",
            "model context protocol",
        ]

        self.search_keywords = [
            "search",
            "google",
            "find",
            "look up",
            "latest",
            "news",
            "recent",
            "current",
            "what's new",
            "developments",
            "updates",
            "trending",
        ]

        self.system_keywords = [
            "system",
            "hardware",
            "cpu",
            "memory",
            "ram",
            "disk",
            "server",
            "specifications",
            "performance",
            "resources",
            "capacity",
            "status",
            "system status",
        ]

        self.weather_keywords = [
            "weather",
            "temperature",
            "rain",
            "sunny",
            "cloudy",
            "forecast",
            "climate",
            "hot",
            "cold",
            "snow",
            "wind",
            "humidity",
        ]

        # New keyword categories for additional MCP servers
        self.budget_keywords = [
            "budget",
            "expense",
            "income",
            "money",
            "cost",
            "spend",
            "spending",
            "save",
            "saving",
            "financial",
            "finance",
            "bill",
            "payment",
            "salary",
            "revenue",
            "profit",
            "loss",
            "investment",
            "bank",
            "account",
            "transaction",
            "balance",
            "summary",
            "overview",
            "report",
            "check my",
            "current balance",
            "budget balance",
            "budget summary",
            "financial status",
            "how much",
            "total spent",
            "monthly budget",
            "expenses",
            "incomes",
            "categorize",
            "category",
            "tracking",
            "track",
        ]

        self.email_keywords = [
            "email",
            "mail",
            "send",
            "message",
            "compose",
            "reply",
            "forward",
            "inbox",
            "outbox",
            "contact",
            "recipient",
            "subject",
            "attachment",
            "correspondence",
            "communication",
            "letter",
            "notify",
            "notification",
        ]

        self.translation_keywords = [
            "translate",
            "translation",
            "language",
            "english",
            "spanish",
            "french",
            "chinese",
            "japanese",
            "german",
            "italian",
            "portuguese",
            "russian",
            "arabic",
            "hindi",
            "korean",
            "convert",
            "interpret",
            "multilingual",
        ]

        # New keyword category for task scheduler
        self.scheduler_keywords = [
            "alarm",
            "remind",
            "reminder",
            "schedule",
            "notify",
            "notification",
            "alert",
            "timer",
            "after",
            "every",
            "recurring",
            "repeat",
            "set",
            "create",
            "cancel task",
            "list tasks",
            "my tasks",
            "wake me",
            "stand up",
            "take water",
            "break",
            "meeting",
            "appointment",
            "deadline",
            "in 20 seconds",
            "in 30 minutes",
            "every 25 mins",
            "after 30 seconds",
            "next week at",
            "tomorrow at",
            "at 9:00",
            "weekly",
            "daily",
            "hourly",
        ]

        # New keyword category for dynamic tool creation
        self.dynamic_tool_keywords = [
            "create script",
            "create a script",
            "create a simple script",
            "create simple python app",
            "create python",
            "create a python",
            "create python script",
            "create a python script",
            "generate code",
            "write script",
            "write a script",
            "write python",
            "write a python",
            "make a script",
            "make script",
            "build a script",
            "build script",
            "develop a script",
            "develop script",
            "automation",
            "automate",
            "automate server",
            "automate system",
            "server automation",
            "system automation",
            "execute script",
            "run script",
            "bash script",
            "python script",
            "shell command",
            "command line",
            "server script",
            "system script",
            "file creation",
            "generate file",
            "create file",
            "write file",
            "make file",
            "script generation",
            "code generation",
            "dynamic script",
            "custom script",
            "tool creation",
            "create tool",
            "build script",
            "develop script",
            "programming",
            "scripting",
            "generate bash",
            "generate python",
            "create bash",
            "create python",
            "write bash",
            "write python",
            "simple script",
            "custom tool",
            "script to",
            "code to",
            "program to",
            "python to",
            "python program",
            "math script",
            "calculation script",
        ]

        # Location patterns for weather queries
        self.location_patterns = [
            r"weather in (\w+(?:\s+\w+)*)",
            r"weather for (\w+(?:\s+\w+)*)",
            r"(\w+(?:\s+\w+)*) weather",
            r"temperature in (\w+(?:\s+\w+)*)",
            r"how's the weather in (\w+(?:\s+\w+)*)",
        ]

    def extract_location(self, text: str) -> Optional[str]:
        """Extract location from weather-related queries"""
        text_lower = text.lower()

        for pattern in self.location_patterns:
            match = re.search(pattern, text_lower)
            if match:
                location = match.group(1).strip()
                # Clean up common words that might be captured
                location = re.sub(r"\b(the|a|an|in|for|at)\b", "", location).strip()
                if location:
                    return location.title()

        return None

    def _detect_scheduler_type(self, text_lower: str) -> str:
        """Detect the type of scheduler request"""
        # Check for cancel/list operations first (highest priority)
        if any(word in text_lower for word in ["cancel", "remove", "delete", "stop"]):
            return "cancel"
        elif any(word in text_lower for word in ["list", "show", "my tasks", "tasks"]):
            return "list"
        # Check for recurring patterns (high priority)
        elif any(
            word in text_lower for word in ["every", "remind", "recurring", "repeat"]
        ):
            return "reminder"
        # Check for alarm patterns (specific patterns including "alarm", "wake", "after", "in X time")
        elif any(word in text_lower for word in ["alarm", "wake me"]) or re.search(
            r"\bafter\s+\d+|\bin\s+\d+\s+(second|minute|hour)", text_lower
        ):
            return "alarm"
        # Check for absolute time patterns (notification)
        elif any(
            word in text_lower
            for word in ["at", "on", "next week", "tomorrow", "schedule"]
        ):
            return "notification"
        else:
            return "unknown"

    def _detect_tool_type(self, text_lower: str) -> str:
        """Detect the type of dynamic tool request"""
        if any(
            word in text_lower
            for word in ["bash", "shell", "command line", "bash script"]
        ):
            return "bash"
        elif any(word in text_lower for word in ["python", "py", "python script"]):
            return "python"
        elif any(
            word in text_lower
            for word in ["create file", "generate file", "write file", "make file"]
        ):
            return "file_creation"
        elif any(
            word in text_lower
            for word in ["automation", "automate", "script generation"]
        ):
            return "automation"
        elif any(
            word in text_lower
            for word in ["execute", "run", "execute script", "run script"]
        ):
            return "execution"
        else:
            return "auto"

    def detect_intent(self, text: str) -> Tuple[IntentType, Dict]:
        """
        Detect the intent of user input and extract relevant context

        Returns:
            Tuple of (IntentType, context_dict)
        """
        text_lower = text.lower()
        context = {}

        # Count keyword matches for each intent type
        rag_score = sum(1 for keyword in self.rag_keywords if keyword in text_lower)
        search_score = sum(
            1 for keyword in self.search_keywords if keyword in text_lower
        )
        system_score = sum(
            1 for keyword in self.system_keywords if keyword in text_lower
        )
        weather_score = sum(
            1 for keyword in self.weather_keywords if keyword in text_lower
        )
        budget_score = sum(
            1 for keyword in self.budget_keywords if keyword in text_lower
        )
        email_score = sum(1 for keyword in self.email_keywords if keyword in text_lower)
        translation_score = sum(
            1 for keyword in self.translation_keywords if keyword in text_lower
        )

        scheduler_score = sum(
            1 for keyword in self.scheduler_keywords if keyword in text_lower
        )

        dynamic_tool_score = sum(
            1 for keyword in self.dynamic_tool_keywords if keyword in text_lower
        )

        logger.info(
            f"Intent scores - RAG: {rag_score}, Search: {search_score}, System: {system_score}, Weather: {weather_score}, Budget: {budget_score}, Email: {email_score}, Translation: {translation_score}, Scheduler: {scheduler_score}, Dynamic Tool: {dynamic_tool_score}"
        )

        # Determine intent based on highest score with priority-based tie-breaking
        scores = {
            IntentType.RAG_QUERY: rag_score,
            IntentType.SEARCH_QUERY: search_score,
            IntentType.SYSTEM_INFO: system_score,
            IntentType.DYNAMIC_TOOL: dynamic_tool_score,
            IntentType.WEATHER: weather_score,
            IntentType.BUDGET_FINANCE: budget_score,
            IntentType.EMAIL_COMMUNICATION: email_score,
            IntentType.TRANSLATION_LANGUAGE: translation_score,
            IntentType.TASK_SCHEDULER: scheduler_score,
        }

        max_score = max(scores.values())

        if max_score == 0:
            # Default to RAG if no clear intent
            return IntentType.RAG_QUERY, {"query": text, "reason": "default_fallback"}

        # Get all intents with the highest score
        top_intents = [intent for intent, score in scores.items() if score == max_score]

        # Priority order for tie-breaking (RAG first per user preference)
        priority_order = [
            IntentType.RAG_QUERY,  # Highest priority per user preference for ties
            IntentType.DYNAMIC_TOOL,  # High priority for script creation
            IntentType.TASK_SCHEDULER,  # High priority for scheduling
            IntentType.WEATHER,  # Specific domain
            IntentType.BUDGET_FINANCE,  # Specific domain
            IntentType.SYSTEM_INFO,  # Specific domain
            IntentType.EMAIL_COMMUNICATION,  # Specific domain
            IntentType.TRANSLATION_LANGUAGE,  # Specific domain
            IntentType.SEARCH_QUERY,  # More general
        ]

        # Select the highest priority intent among tied scores
        for priority_intent in priority_order:
            if priority_intent in top_intents:
                intent = priority_intent
                break
        else:
            # Fallback if somehow no match (shouldn't happen)
            intent = top_intents[0]

        # Extract additional context based on intent
        if intent == IntentType.WEATHER:
            location = self.extract_location(text)
            context = {
                "query": text,
                "location": location,
                "extracted_keywords": [
                    kw for kw in self.weather_keywords if kw in text_lower
                ],
            }
        elif intent == IntentType.SYSTEM_INFO:
            context = {
                "query": text,
                "extracted_keywords": [
                    kw for kw in self.system_keywords if kw in text_lower
                ],
            }
        elif intent == IntentType.DYNAMIC_TOOL:
            context = {
                "query": text,
                "extracted_keywords": [
                    kw for kw in self.dynamic_tool_keywords if kw in text_lower
                ],
                "tool_type": self._detect_tool_type(text_lower),
            }
        elif intent == IntentType.SEARCH_QUERY:
            context = {
                "query": text,
                "search_terms": text,  # The full text as search terms
                "extracted_keywords": [
                    kw for kw in self.search_keywords if kw in text_lower
                ],
            }
        elif intent == IntentType.BUDGET_FINANCE:
            context = {
                "query": text,
                "extracted_keywords": [
                    kw for kw in self.budget_keywords if kw in text_lower
                ],
            }
        elif intent == IntentType.EMAIL_COMMUNICATION:
            context = {
                "query": text,
                "extracted_keywords": [
                    kw for kw in self.email_keywords if kw in text_lower
                ],
            }
        elif intent == IntentType.TRANSLATION_LANGUAGE:
            context = {
                "query": text,
                "extracted_keywords": [
                    kw for kw in self.translation_keywords if kw in text_lower
                ],
            }
        elif intent == IntentType.TASK_SCHEDULER:
            context = {
                "query": text,
                "extracted_keywords": [
                    kw for kw in self.scheduler_keywords if kw in text_lower
                ],
                "scheduler_type": self._detect_scheduler_type(text_lower),
            }
        else:  # RAG_QUERY
            context = {
                "query": text,
                "extracted_keywords": [
                    kw for kw in self.rag_keywords if kw in text_lower
                ],
            }

        return intent, context

    def prepare_mcp_prompt(
        self, intent: IntentType, context: Dict, original_query: str
    ) -> str:
        """
        Prepare a structured prompt for the MCP AI based on detected intent
        """
        # Get base instructions from external file
        base_prompt = get_mcp_instructions()

        # Get intent-specific guidance
        location_hint = ""
        if intent == IntentType.WEATHER and context.get("location"):
            location_hint = f" (Location detected: {context.get('location')})"

        guidance = get_intent_guidance(intent.value, location_hint=location_hint)

        user_query = f"\n** USER QUERY **\n{original_query}\n"

        return base_prompt + guidance + user_query

    def process_query(self, text: str) -> Dict:
        """
        Main processing function that combines intent detection and prompt preparation

        Returns:
            Dictionary containing:
            - intent: IntentType
            - context: Dict with extracted context
            - mcp_prompt: Prepared prompt for MCP AI
            - original_query: Original user input
        """
        intent, context = self.detect_intent(text)
        mcp_prompt = self.prepare_mcp_prompt(intent, context, text)

        result = {
            "intent": intent,
            "context": context,
            "mcp_prompt": mcp_prompt,
            "original_query": text,
        }

        logger.info(f"Processed query with intent: {intent.value}")
        return result


# Global processor instance
mcp_processor = MCPAIProcessor()


def process_for_mcp_ai(user_input: str) -> Dict:
    """
    Process user input for MCP AI integration

    Args:
        user_input: Raw user input text

    Returns:
        Dictionary with processed information for MCP AI
    """
    return mcp_processor.process_query(user_input)
