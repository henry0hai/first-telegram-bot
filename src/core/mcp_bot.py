# src/core/mcp_bot.py - MCP-enhanced bot application
import time
import fcntl
import asyncio
import signal

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config.config import config
from src.handlers.commands import (
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
)
from src.handlers.scheduler_commands import (
    tasks_command,
    cancel_command,
    schedule_command,
)
from src.handlers.conversation_commands import (
    clear_conversation_command,
    conversation_status_command,
)
from src.handlers.messages import handle_photo, handle_document
from src.handlers.mcp_messages import handle_mcp_text
from src.services.scheduler import on_startup, scheduled_weather, debug_time
from src.services.conversation_history import conversation_service
from src.services.qdrant_conversation_manager import qdrant_conversation_manager
from src.utils.lock import ensure_single_instance
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def error_handler(update, context):
    logger.error(f"Error occurred: {context.error}")


async def main():
    # Avoid modifying globals directly; use local variables and update config explicitly if needed
    # Prevent tokenizers from spawning extra processes/threads that may leak semaphores
    import os

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
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

    # Initialize conversation services
    try:
        # Initialize basic conversation service
        await conversation_service.initialize()
        logger.info("Conversation history service initialized successfully")

        # Initialize enhanced Qdrant conversation manager
        await qdrant_conversation_manager.initialize()
        logger.info("Enhanced Qdrant conversation manager initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize conversation services: {e}")

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

    # Scheduler command handlers
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("schedule", schedule_command))

    # Conversation management command handlers
    application.add_handler(
        CommandHandler("clear_conversation", clear_conversation_command)
    )
    application.add_handler(
        CommandHandler("conversation_status", conversation_status_command)
    )

    application.add_error_handler(error_handler)

    # MCP-enhanced message handlers
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mcp_text)
    )
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Initial scheduling
    job_queue.run_once(on_startup, 0)
    job_queue.run_repeating(
        scheduled_weather, interval=config.scheduled_weather_loop, first=0
    )
    job_queue.run_repeating(debug_time, interval=config.debug_time_loop, first=0)

    print("MCP Bot is running... Press Ctrl+C to stop")
    stop_event = asyncio.Event()

    # Setup signal handlers to stop gracefully
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Fallback in environments without signal support
            pass

    try:
        # Explicit async lifecycle
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        await stop_event.wait()
    except Exception as e:
        logger.error(f"MCP Bot stopped unexpectedly: {e}")
    finally:
        # Clean shutdown
        logger.info("Bot shutting down...")
        try:
            config.is_bot_running = False
            # Stop polling before stopping the app to avoid in-flight network errors
            try:
                if application.updater:
                    await application.updater.stop()
            except Exception:
                pass
            await application.stop()
            await application.shutdown()
        except Exception as e:
            logger.debug(f"Shutdown cleanup error: {e}")
        # Release lock
        if lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_UN)  # Unlock the file
            lock_file.close()
            logger.info("Lock file released")


if __name__ == "__main__":
    asyncio.run(main())
