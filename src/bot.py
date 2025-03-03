# src/bot.py
import time
import fcntl

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters
)
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
    handle_text
)
from src.scheduler import on_startup, scheduled_weather, debug_time
from src.lock import ensure_single_instance

from src.logging_utils import get_logger  
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

    logger.info(f"Bot initialized with config.is_bot_running: {config.is_bot_running}")

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

    # New text handler for non-command messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    # Initial scheduling
    job_queue.run_once(on_startup, 0)
    job_queue.run_repeating(
        scheduled_weather, interval=config.scheduled_weather_loop, first=0
    )
    job_queue.run_repeating(debug_time, interval=config.debug_time_loop, first=0)

    print("Bot is running... Press Ctrl+C to stop")
    try:
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
        application.stop()
        application.shutdown()
    except Exception as e:
        logger.error(f"Bot stopped unexpectedly: {e}")
    finally:
        # Shut down the application synchronously
        if lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_UN)  # Unlock the file
            lock_file.close()
            logger.info("Lock file released")


if __name__ == "__main__":
    main()
