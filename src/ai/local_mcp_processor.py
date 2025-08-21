# src/ai/local_mcp_processor.py
# Local MCP AI processor using Ollama for immediate responses

import json
import subprocess
import tempfile
import os
from typing import Dict, Optional, Tuple
from openai import OpenAI
from src.ai.mcp_instructions import get_mcp_instructions, get_intent_guidance
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class LocalMCPProcessor:
    """Local MCP AI processor using Ollama deepseek-r1:7b model"""

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

    def process_dynamic_tool_request(
        self, user_query: str, context: Dict, chat_id: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Process dynamic tool creation request locally

        Args:
            user_query: The user's request
            context: Context from intent detection
            chat_id: Telegram chat ID for script execution

        Returns:
            Tuple of (success: bool, result: Dict)
        """
        if not self.is_ollama_available():
            logger.warning("Ollama not available, falling back to webhook")
            return False, {"error": "Ollama not available"}

        try:
            # Get MCP instructions
            base_instructions = get_mcp_instructions()
            intent_guidance = get_intent_guidance("dynamic_tool")

            # Create enhanced prompt
            enhanced_prompt = f"""{base_instructions}

{intent_guidance}

** CONTEXT **
User Request Type: Dynamic Tool Creation
Tool Type: {context.get('tool_type', 'auto')}
Detected Keywords: {context.get('extracted_keywords', [])}
Chat ID: {chat_id or '1172251646'}

** CRITICAL EXECUTION INSTRUCTIONS **
This is being processed locally for immediate execution. Follow these rules EXACTLY:

1. Generate CLEAN, EXECUTABLE code in proper markdown code blocks
2. Use ```python for Python code (required for extraction)
3. DO NOT include explanations, comments, or text inside code blocks
4. Put explanations BEFORE or AFTER code blocks, never inside
5. For calculations, include print() statements for results
6. Keep code simple and focused on the specific request
7. DO NOT use markdown separators (---) near code
8. DO NOT include "Response Format", "Output", or "Note" sections in code

GOOD FORMAT:
```
Here's a Python script for your calculation:

```python
import math
result = math.pi * 4
print(f"Result: {{result}}")
```

This script calculates the requested value.
```

BAD FORMAT (DO NOT DO THIS):
```
---
```python
import math
---
result = math.pi * 4
**Output:**
print(result)
```
---
```

** USER REQUEST **
{user_query}

Generate the appropriate script following the format rules above. Focus on creating clean, executable code."""

            logger.info(f"Processing dynamic tool request with {self.model_name}")

            # Call local Ollama model
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert AI assistant specializing in dynamic tool creation and script generation. Follow the MCP instructions precisely.",
                    },
                    {"role": "user", "content": enhanced_prompt},
                ],
                temperature=0.1,  # Low temperature for consistent code generation
                max_tokens=2000,  # Sufficient for script generation
            )

            ai_response = response.choices[0].message.content

            # Try to extract and execute any Python code if it's safe
            execution_result = self._try_execute_safe_code(ai_response, context)

            result = {
                "success": True,
                "ai_response": ai_response,
                "execution_result": execution_result,
                "model_used": self.model_name,
                "tool_type": context.get("tool_type", "auto"),
            }

            logger.info("Successfully processed dynamic tool request locally")
            return True, result

        except Exception as e:
            logger.error(f"Error processing dynamic tool request: {e}")
            return False, {"error": str(e)}

    def _try_execute_safe_code(self, ai_response: str, context: Dict) -> Optional[Dict]:
        """
        Try to extract and execute safe Python code from AI response

        Args:
            ai_response: The AI's response containing code
            context: Context from intent detection

        Returns:
            Execution result dict or None if no safe execution possible
        """
        try:
            # Look for Python code blocks in different formats
            import re

            # First, try standard markdown code blocks
            python_blocks = re.findall(
                r"```python\s*\n(.*?)\n```", ai_response, re.DOTALL
            )

            # If no markdown blocks found, look for other patterns
            if not python_blocks:
                # Look for code between triple backticks without language specifier
                python_blocks = re.findall(
                    r"```\s*\n(.*?)\n```", ai_response, re.DOTALL
                )

            # If still nothing, look for code that starts with import or common Python patterns
            if not python_blocks:
                # Look for blocks that start with import and contain Python-like syntax
                potential_code = re.findall(
                    r"(import\s+\w+.*?(?=\n\n|\n---|\nNote:|\nOutput:|\Z))",
                    ai_response,
                    re.DOTALL | re.MULTILINE,
                )
                if potential_code:
                    python_blocks = potential_code

            if not python_blocks:
                logger.warning("No Python code blocks found in AI response")
                return None

            # Take the first Python code block and clean it
            code = python_blocks[0].strip()

            # Remove common non-code artifacts
            lines = code.split("\n")
            cleaned_lines = []

            for line in lines:
                line = line.strip()
                # Skip markdown artifacts, explanatory text, and separators
                if (
                    line.startswith("---")
                    or line.startswith("**")
                    or line.startswith("Note:")
                    or line.startswith("Output:")
                    or line.startswith("Response Format:")
                    or line == ""
                    and len(cleaned_lines) == 0
                ):  # Skip leading empty lines
                    continue

                # Stop at common ending markers
                if (
                    line.startswith("---")
                    or line.startswith("**Output:**")
                    or line.startswith("**Note:**")
                    or line.startswith("**Response Format:**")
                ):
                    break

                cleaned_lines.append(line)

            # Remove trailing empty lines
            while cleaned_lines and cleaned_lines[-1] == "":
                cleaned_lines.pop()

            code = "\n".join(cleaned_lines)

            if not code or len(code) < 10:  # Too short to be meaningful code
                logger.warning("Extracted code too short or empty")
                return None

            logger.info(f"Extracted code ({len(code)} chars): {code[:100]}...")

            # Safety check - only allow safe mathematical and basic operations
            dangerous_keywords = [
                "import os",
                "import sys",
                "import subprocess",
                "import shutil",
                "open(",
                "file(",
                "exec(",
                "eval(",
                "__import__",
                "input(",
                "raw_input(",
                "delete",
                "remove",
                "rmdir",
            ]

            if any(keyword in code.lower() for keyword in dangerous_keywords):
                logger.warning(
                    "Code contains potentially unsafe operations, skipping execution"
                )
                return {"status": "skipped", "reason": "unsafe_operations"}

            # For mathematical calculations, we can safely execute
            if any(
                keyword in context.get("query", "").lower()
                for keyword in ["calculate", "compute", "math", "formula"]
            ):
                # Create a temporary file and execute safely
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False
                ) as f:
                    f.write(code)
                    temp_file = f.name

                try:
                    # Execute with timeout and limited environment
                    result = subprocess.run(
                        ["python", temp_file],
                        capture_output=True,
                        text=True,
                        timeout=10,  # 10 second timeout
                        cwd=tempfile.gettempdir(),  # Run in temp directory
                    )

                    if result.returncode == 0:
                        return {
                            "status": "executed",
                            "output": result.stdout.strip(),
                            "code": code,
                        }
                    else:
                        return {
                            "status": "error",
                            "error": result.stderr.strip(),
                            "code": code,
                        }

                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_file)
                    except:
                        pass

            return {"status": "code_generated", "code": code}

        except Exception as e:
            logger.warning(f"Error trying to execute code: {e}")
            return None


# Global instance
local_mcp_processor = LocalMCPProcessor()


def process_locally_if_available(
    user_query: str, context: Dict, chat_id: Optional[str] = None
) -> Tuple[bool, Dict]:
    """
    Process dynamic tool request locally if Ollama is available

    Args:
        user_query: The user's request
        context: Context from intent detection
        chat_id: Telegram chat ID

    Returns:
        Tuple of (processed_locally: bool, result: Dict)
    """
    return local_mcp_processor.process_dynamic_tool_request(
        user_query, context, chat_id
    )
