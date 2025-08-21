# src/ai/mcp_request_preprocessor.py
# MCP request pre-processor using Ollama for enhanced webhook payloads

import json
import subprocess
from typing import Dict, Optional, Tuple
from openai import OpenAI
from src.ai.mcp_instructions import get_mcp_instructions, get_intent_guidance
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class MCPRequestPreprocessor:
    """MCP request pre-processor using Ollama to create structured MCP tool calls"""

    def __init__(self, model_name: str = "deepseek-r1:7b"):
        self.model_name = model_name
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",  # Point to local Ollama server
            api_key="ollama",  # Placeholder key for Ollama
        )

    def is_ollama_available(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            # Check if Ollama is running
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False

            # Check if our model is available
            models_data = json.loads(result.stdout)
            available_models = [
                model["name"] for model in models_data.get("models", [])
            ]

            # Check for exact match or partial match (deepseek-r1:7b might show as deepseek-r1)
            model_available = any(
                self.model_name in model or model in self.model_name
                for model in available_models
            )

            if not model_available:
                logger.warning(
                    f"Model {self.model_name} not found. Available models: {available_models}"
                )

            return model_available

        except Exception as e:
            logger.warning(f"Failed to check Ollama availability: {e}")
            return False

    def preprocess_mcp_request(
        self, user_query: str, context: Dict, chat_id: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Pre-process user request to create structured MCP tool call

        Args:
            user_query: The user's original request
            context: Context from intent detection
            chat_id: Telegram chat ID

        Returns:
            Tuple of (success: bool, preprocessed_request: Dict)
        """
        if not self.is_ollama_available():
            logger.warning("Ollama not available, using basic preprocessing")
            return False, self._create_basic_preprocessed_request(
                user_query, context, chat_id
            )

        try:
            # Get MCP instructions
            base_instructions = get_mcp_instructions()
            intent_guidance = get_intent_guidance(
                context.get("intent_type", "dynamic_tool")
            )

            # Create preprocessing prompt
            preprocessing_prompt = f"""{base_instructions}

{intent_guidance}

** MCP REQUEST PREPROCESSING TASK **

Your job is to analyze the user's request and create a structured MCP tool call for the "generic_tool_creation" tool that the MCP server can easily understand and execute.

** USER CONTEXT **
Intent Type: {context.get("intent_type", "dynamic_tool")} (MUST use generic_tool_creation tool)
Tool Type: {context.get('tool_type', 'auto')}
Detected Keywords: {context.get('extracted_keywords', [])}
Chat ID: {chat_id or '1172251646'}

** TASK INSTRUCTIONS **

1. You MUST use the "generic_tool_creation" tool for DYNAMIC_TOOL requests
2. Extract the specific parameters needed for dynamic tool creation
3. Create a clear, structured tool call specification
4. Provide reasoning for your parameter choices

IMPORTANT: For DYNAMIC_TOOL intent, always use tool_name: "generic_tool_creation"

Format your response as a JSON structure like this:

```json
{{
    "tool_name": "generic_tool_creation",
    "parameters": {{
        "user_request": "create a Python script to calculate cylinder volume and surface area with radius 6 and height 4",
        "preferred_language": "python",
        "send_to_telegram": true,
        "chat_id": "{chat_id or '1172251646'}"
    }},
    "reasoning": "DYNAMIC_TOOL request requires generic_tool_creation tool. User wants Python code for mathematical calculations with specific parameters.",
    "expected_outcome": "A working Python script that calculates and displays cylinder volume and surface area"
}}
```

** USER REQUEST **
{user_query}

Create the structured MCP tool call using generic_tool_creation following the JSON format above."""

            logger.info(f"Pre-processing MCP request with {self.model_name}")

            # Call local Ollama model for preprocessing
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert MCP request analyzer. Your job is to convert user requests into structured MCP tool calls that servers can easily understand and execute. Always respond with valid JSON in the specified format.",
                    },
                    {"role": "user", "content": preprocessing_prompt},
                ],
                temperature=0.1,  # Low temperature for consistent structured output
                max_tokens=1000,  # Sufficient for structured response
            )

            ai_response = response.choices[0].message.content

            # Extract JSON from AI response
            structured_request = self._extract_json_from_response(ai_response)

            if structured_request:
                # Create tool_calls format for webhook compatibility
                tool_calls = [
                    {
                        "function": {
                            "name": structured_request.get(
                                "tool_name", "generic_tool_creation"
                            ),
                            "parameters": structured_request.get("parameters", {}),
                        },
                        "reasoning": structured_request.get("reasoning", ""),
                        "expected_outcome": structured_request.get(
                            "expected_outcome", ""
                        ),
                    }
                ]

                result = {
                    "success": True,
                    "tool_calls": tool_calls,
                    "reasoning": structured_request.get("reasoning", ""),
                    "model_used": self.model_name,
                    "original_query": user_query,
                    "raw_ai_response": ai_response,
                }

                logger.info(
                    f"Successfully preprocessed MCP request - tool: {structured_request.get('tool_name')}"
                )
                return True, result
            else:
                logger.warning("Failed to extract valid JSON from AI response")
                return False, self._create_basic_preprocessed_request(
                    user_query, context, chat_id
                )

        except Exception as e:
            logger.error(f"Error preprocessing MCP request: {e}")
            return False, self._create_basic_preprocessed_request(
                user_query, context, chat_id
            )

    def _extract_json_from_response(self, ai_response: str) -> Optional[Dict]:
        """Extract JSON structure from AI response"""
        try:
            import re

            # Look for JSON blocks
            json_blocks = re.findall(r"```json\s*\n(.*?)\n```", ai_response, re.DOTALL)

            if json_blocks:
                json_str = json_blocks[0].strip()
                return json.loads(json_str)

            # If no markdown blocks, try to find JSON-like structure
            # Look for content between { and } that spans multiple lines
            json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
            matches = re.findall(json_pattern, ai_response, re.DOTALL)

            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue

            return None

        except Exception as e:
            logger.warning(f"Error extracting JSON: {e}")
            return None

    def _create_basic_preprocessed_request(
        self, user_query: str, context: Dict, chat_id: Optional[str]
    ) -> Dict:
        """Create basic preprocessed request when AI processing fails"""

        # Determine tool based on intent type
        intent_type = context.get("intent_type", "dynamic_tool")
        tool_type = context.get("tool_type", "auto")

        if intent_type == "dynamic_tool":
            # Always use generic_tool_creation for dynamic tool requests
            tool_name = "generic_tool_creation"
            parameters = {
                "user_request": user_query,
                "preferred_language": "python" if tool_type == "python" else "auto",
                "send_to_telegram": True,
                "chat_id": chat_id or "1172251646",
            }
            reasoning = f"DYNAMIC_TOOL request fallback: using generic_tool_creation with tool type: {tool_type}"

        elif intent_type == "task_scheduler":
            # Map to appropriate scheduler tool
            scheduler_type = context.get("scheduler_type", "unknown")
            if scheduler_type == "alarm":
                tool_name = "create_alarm"
            elif scheduler_type == "reminder":
                tool_name = "create_reminder"
            elif scheduler_type == "notification":
                tool_name = "create_notification"
            elif scheduler_type == "list":
                tool_name = "list_tasks"
            elif scheduler_type == "cancel":
                tool_name = "cancel_task"
            else:
                tool_name = "create_reminder"  # Default

            parameters = {"user_request": user_query, "scheduler_type": scheduler_type}
            reasoning = f"Task scheduler request detected: {scheduler_type}"

        elif intent_type == "budget_finance":
            # Determine budget tool based on keywords
            if any(
                word in user_query.lower()
                for word in ["balance", "summary", "overview", "check my"]
            ):
                tool_name = "get_budget_summary"
                parameters = {"month": None}  # Could extract month if specified
            elif any(
                word in user_query.lower()
                for word in ["add expense", "spent", "bought", "paid"]
            ):
                tool_name = "add_expense"
                parameters = {"user_request": user_query}
            elif any(
                word in user_query.lower()
                for word in ["add income", "earned", "salary", "received"]
            ):
                tool_name = "add_income"
                parameters = {"user_request": user_query}
            elif any(
                word in user_query.lower() for word in ["report", "export", "csv"]
            ):
                tool_name = "get_expense_report"
                parameters = {"format": "csv"}
            else:
                tool_name = "get_budget_summary"
                parameters = {"month": None}

            reasoning = f"Budget/finance request detected: {tool_name}"

        elif intent_type == "weather":
            tool_name = "get_weather"
            location = context.get("location", "current location")
            parameters = {"location": location}
            reasoning = f"Weather request detected for location: {location}"

        else:
            # Default fallback
            tool_name = "generic_tool_creation"
            parameters = {
                "user_request": user_query,
                "preferred_language": "auto",
                "send_to_telegram": True,
                "chat_id": chat_id or "1172251646",
            }
            reasoning = f"General request preprocessing for intent: {intent_type}"

        # Create tool_calls format for webhook compatibility
        tool_calls = [
            {
                "function": {"name": tool_name, "parameters": parameters},
                "reasoning": reasoning,
                "expected_outcome": "Process user request according to detected intent",
            }
        ]

        return {
            "success": False,  # AI preprocessing failed, using basic fallback
            "tool_calls": tool_calls,
            "reasoning": reasoning,
            "model_used": "fallback",
            "original_query": user_query,
            "fallback_used": True,
        }


# Global instance
mcp_request_preprocessor = MCPRequestPreprocessor()


def preprocess_for_mcp_server(
    user_query: str, context: Dict, chat_id: Optional[str] = None
) -> Tuple[bool, Dict]:
    """
    Pre-process user request for MCP server

    Args:
        user_query: The user's request
        context: Context from intent detection (should include intent_type)
        chat_id: Telegram chat ID

    Returns:
        Tuple of (ai_preprocessed: bool, preprocessed_data: Dict)
    """
    # Add intent type to context for preprocessing
    if "intent" in context and hasattr(context["intent"], "value"):
        context["intent_type"] = context["intent"].value

    return mcp_request_preprocessor.preprocess_mcp_request(user_query, context, chat_id)
