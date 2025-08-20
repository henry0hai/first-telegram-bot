# src/mcp_bot.py
import time
import fcntl

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from src.config import config
from src.commands import (
    start,
    stop,
    help_command,
    say,
    status,
    cpu,
    ram,
    disk,
    weather,
    uptime,
    info,
    handle_photo,
    handle_document,
)
from src.scheduler import on_startup, scheduled_weather, debug_time
from src.lock import ensure_single_instance
from src.mcp_ai import process_for_mcp_ai, IntentType

from src.logging_utils import get_logger

logger = get_logger(__name__)


def error_handler(update, context):
    logger.error(f"Error occurred: {context.error}")


# MCP-enhanced text handler
async def handle_mcp_text(update, context):
    """Enhanced text handler that uses MCP AI preprocessing"""
    from telegram import Update
    from telegram.ext import ContextTypes
    import aiohttp

    user_input = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"

    # Process with MCP AI preprocessing
    mcp_result = process_for_mcp_ai(user_input)

    logger.info(
        f"MCP processed query - Intent: {mcp_result['intent'].value}, User: {username}"
    )

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
        IntentType.UNKNOWN: "🤖 Processing your request...",
    }

    feedback_message = intent_messages.get(
        mcp_result["intent"], intent_messages[IntentType.UNKNOWN]
    )
    await update.message.reply_text(feedback_message)


def main():
    # Avoid modifying globals directly; use local variables and update config explicitly if needed
    lock_file = ensure_single_instance()
    start_time = time.time()  # Local start time for this instance
    application = ApplicationBuilder().token(config.telegram_bot_token).build()
    job_queue = application.job_queue

    # Update config object
    config.start_time = start_time
    config.is_bot_running = True
    config.job_queue = job_queue

    logger.info(
        f"MCP Bot initialized with config.is_bot_running: {config.is_bot_running}"
    )

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("say", say))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("cpu", cpu))
    application.add_handler(CommandHandler("ram", ram))
    application.add_handler(CommandHandler("disk", disk))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(CommandHandler("uptime", uptime))
    application.add_handler(CommandHandler("info", info))
    application.add_error_handler(error_handler)

    # MCP-enhanced text handler for non-command messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mcp_text)
    )

    # Photo handler
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Document handler
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Initial scheduling
    job_queue.run_once(on_startup, 0)
    job_queue.run_repeating(
        scheduled_weather, interval=config.scheduled_weather_loop, first=0
    )
    job_queue.run_repeating(debug_time, interval=config.debug_time_loop, first=0)

    print("MCP Bot is running... Press Ctrl+C to stop")
    try:
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("MCP Bot stopped by user (Ctrl+C)")
        application.stop()
        application.shutdown()
    except Exception as e:
        logger.error(f"MCP Bot stopped unexpectedly: {e}")
    finally:
        # Shut down the application synchronously
        if lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_UN)  # Unlock the file
            lock_file.close()
            logger.info("Lock file released")


if __name__ == "__main__":
    main()
