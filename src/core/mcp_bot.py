# src/core/mcp_bot.py - MCP-enhanced bot application
import time
import fcntl

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
from src.handlers.messages import handle_photo, handle_document
from src.handlers.mcp_messages import handle_mcp_text
from src.services.scheduler import on_startup, scheduled_weather, debug_time
from src.utils.lock import ensure_single_instance
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def error_handler(update, context):
    logger.error(f"Error occurred: {context.error}")


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

    # Scheduler command handlers
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("schedule", schedule_command))

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
