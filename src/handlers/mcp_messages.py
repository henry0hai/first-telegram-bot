# src/handlers/mcp_messages.py - MCP-enhanced message handlers
import aiohttp
from typing import Tuple

from telegram import Update
from telegram.ext import ContextTypes
from config.config import config
from src.ai.mcp_processor import process_for_mcp_ai, IntentType
from src.ai.mcp_request_preprocessor import preprocess_for_mcp_server
from src.handlers.scheduler_handler import handle_scheduler_command
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


# MCP-enhanced text handler
async def handle_mcp_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced text handler that uses MCP AI preprocessing"""
    user_input = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"

    # Process with MCP AI preprocessing
    mcp_result = process_for_mcp_ai(user_input)

    logger.info(
        f"MCP processed query - Intent: {mcp_result['intent'].value}, User: {username}"
    )

    # Send immediate feedback for DYNAMIC_TOOL requests (before preprocessing)
    if mcp_result["intent"] == IntentType.DYNAMIC_TOOL:
        await update.message.reply_text(
            "🛠️ Creating and executing your custom script..."
        )

    # Handle scheduler requests directly (no webhook needed for local scheduling)
    if mcp_result["intent"] == IntentType.TASK_SCHEDULER:
        await handle_scheduler_command(update, context, mcp_result["context"])
        return  # Exit early for scheduler commands

    # Handle dynamic tool requests with preprocessing (user already got feedback)
    if mcp_result["intent"] == IntentType.DYNAMIC_TOOL:
        success, preprocessed_data = await _handle_dynamic_tool_request_enhanced(
            update, context, mcp_result, user_input, user_id
        )

        # Use preprocessed data for webhook if preprocessing was successful
        if success and preprocessed_data.get("success", False):
            logger.info("Using preprocessed MCP request for webhook")
            # Update the payload with preprocessed request
            mcp_result["preprocessed"] = {
                "tool_calls": preprocessed_data.get("tool_calls", []),
                "reasoning": preprocessed_data.get("reasoning", ""),
                "model_used": preprocessed_data.get("model_used", "deepseek-r1:7b"),
            }
        else:
            logger.info("Using basic preprocessing fallback")

    # Send enhanced payload to N8N webhook if configured
    webhook_url = config.n8n_webhook_url
    if webhook_url:
        payload = {
            "message": {
                "text": user_input,
                "mcp_enhanced": {
                    "intent": mcp_result["intent"].value,
                    "context": mcp_result["context"],
                    "mcp_prompt": mcp_result["mcp_prompt"],
                    "original_query": mcp_result["original_query"],
                },
            },
            "user": {"id": user_id, "username": username},
        }

        # Add preprocessed data to payload if available
        if "preprocessed" in mcp_result:
            payload["message"]["mcp_enhanced"]["preprocessed"] = mcp_result[
                "preprocessed"
            ]
            logger.info(
                f"Enhanced payload with {len(mcp_result['preprocessed'].get('tool_calls', []))} preprocessed tool calls"
            )

        try:
            # Debug: Log the actual payload being sent
            logger.info(
                f"Sending webhook payload for intent {mcp_result['intent'].value}:"
            )
            logger.info(f"Payload keys: {list(payload.keys())}")
            logger.info(f"Message keys: {list(payload['message'].keys())}")
            if "mcp_enhanced" in payload["message"]:
                logger.info(
                    f"MCP enhanced keys: {list(payload['message']['mcp_enhanced'].keys())}"
                )

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(f"N8N webhook returned status {resp.status}")
                    else:
                        logger.info(f"Successfully sent MCP-enhanced payload to N8N")
        except Exception as e:
            logger.error(f"Failed to send to N8N webhook: {e}")

    # Provide user feedback for other intents (DYNAMIC_TOOL already got immediate feedback)
    intent_messages = {
        IntentType.RAG_QUERY: "🔍 Processing your document-related question...",
        IntentType.SEARCH_QUERY: "🌐 Searching for the latest information...",
        IntentType.SYSTEM_INFO: "💻 Getting system information...",
        IntentType.WEATHER: f"🌤️ Getting weather information...",
        IntentType.BUDGET_FINANCE: "💰 Processing your budget/finance request...",
        IntentType.EMAIL_COMMUNICATION: "📧 Handling your email request...",
        IntentType.TRANSLATION_LANGUAGE: "🌍 Processing translation request...",
        IntentType.TASK_SCHEDULER: "⏰ Creating your scheduled task...",
        IntentType.UNKNOWN: "🤖 Processing your request...",
    }

    feedback_message = intent_messages.get(
        mcp_result["intent"], intent_messages[IntentType.UNKNOWN]
    )
    await update.message.reply_text(feedback_message)


async def _handle_dynamic_tool_request_enhanced(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mcp_result: dict,
    user_input: str,
    user_id: int,
) -> Tuple[bool, dict]:
    """
    Enhanced dynamic tool creation request handler with MCP request preprocessing

    This preprocesses user queries into structured MCP tool calls before sending
    to webhook, allowing the MCP server to easily select the correct tools.
    No Telegram message is sent - preprocessing is silent.
    """
    tool_context = mcp_result["context"]
    query = tool_context.get("query", "")
    tool_type = tool_context.get("tool_type", "auto")
    chat_id = str(update.effective_chat.id)

    logger.info(f"Preprocessing DYNAMIC_TOOL request (silent): {tool_type}")

    # Preprocess the request for better MCP server handling - FIXED TUPLE HANDLING
    # Pass the full mcp_result (which contains intent) instead of just tool_context
    ai_success, preprocessed_result = preprocess_for_mcp_server(user_input, mcp_result)

    # Log the preprocessing result but don't send to Telegram
    if ai_success and preprocessed_result.get("success", False):
        tool_calls = preprocessed_result.get("tool_calls", [])
        tool_name = tool_calls[0]["function"]["name"] if tool_calls else "unknown"
        logger.info(
            f"Preprocessed with {preprocessed_result.get('model_used')}: {tool_name}"
        )
    else:
        logger.info("Using fallback preprocessing (AI unavailable)")

    # Return the preprocessed result for webhook enhancement (no Telegram message)
    return True, preprocessed_result
