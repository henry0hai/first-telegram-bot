# src/handlers/mcp_messages.py - MCP-enhanced message handlers
import aiohttp

from telegram import Update
from telegram.ext import ContextTypes
from config.config import config
from src.ai.mcp_processor import process_for_mcp_ai, IntentType
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

    # Handle scheduler requests directly (no webhook needed for local scheduling)
    if mcp_result["intent"] == IntentType.TASK_SCHEDULER:
        await handle_scheduler_command(update, context, mcp_result["context"])
        return  # Exit early for scheduler commands

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
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(f"N8N webhook returned status {resp.status}")
                    else:
                        logger.info(f"Successfully sent MCP-enhanced payload to N8N")
        except Exception as e:
            logger.error(f"Failed to send to N8N webhook: {e}")

    # Provide user feedback based on detected intent
    intent_messages = {
        IntentType.RAG_QUERY: "🔍 Processing your document-related question...",
        IntentType.SEARCH_QUERY: "🌐 Searching for the latest information...",
        IntentType.SYSTEM_INFO: "💻 Getting system information...",
        IntentType.WEATHER: f"🌤️ Getting weather information{' for ' + mcp_result['context'].get('location', '') if mcp_result['context'].get('location') else ''}...",
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
