# src/commands.py
import time
import psutil
import platform

from telegram import Update
from functools import partial
from datetime import datetime
from src.utils import get_weather
from telegram.ext import ContextTypes
from src.config import config, bot_lock, logger
from src.scheduler import on_startup, scheduled_weather, debug_time


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        user_name = update.message.from_user.username
        if user_name != config.admin_user_name:
            await update.message.reply_text("Sorry, only the admin can stop the bot.")
            return

        logger.info(
            f"Stop command received. config.is_bot_running: {config.is_bot_running}"
        )

        if config.job_queue:
            logger.info(f"Current job count: {len(config.job_queue.jobs())}")
        else:
            logger.warning("Job queue is None")

        await update.message.reply_text("Stopping bot activities...")
        logger.info("Bot activities stopped by admin")

        if config.job_queue and config.job_queue.jobs():
            jobs = config.job_queue.jobs()
            logger.info(f"Found {len(jobs)} scheduled jobs before removal")
            for job in jobs:
                job.schedule_removal()
            remaining_jobs = len(config.job_queue.jobs())
            logger.info(f"After removal, {remaining_jobs} jobs remain")
            if remaining_jobs > 0:
                logger.warning("Some jobs may not have been removed immediately")
        else:
            logger.info("No scheduled jobs to remove or job queue is None")

        config.is_bot_running = False
        await update.message.reply_text("All scheduled activities have been stopped.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        user = update.message.from_user.first_name

        if config.is_bot_running:  # Use config.is_bot_running
            message = f"Hello {user}! The bot is already running. Use /help to see available commands."
            await update.message.reply_text(message)
            return

        message = f"Hello {user}! Restarting bot activities now. Use /help to see available commands."
        await update.message.reply_text(message)

        if config.job_queue:
            # Pass user via context.job_data instead of partial
            config.job_queue.run_once(on_startup, 0, data={"user": user})
            config.job_queue.run_repeating(scheduled_weather, interval=config.scheduled_weather_loop, first=0)
            config.job_queue.run_repeating(debug_time, interval=config.debug_time_loop, first=0)
            logger.info(f"User {user} restarted all bot activities")

        config.is_bot_running = True  # Use config.is_bot_running


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        help_text = """
        Available commands:
        /start - Start the bot
        /help - Show this help message
        /say <message> - Echo your message
        /kiemtra - Check bot status
        /cpu - Get CPU usage
        /ram - Get RAM usage
        /disk - Get disk usage
        /stop - Stop the bot (admin only)
        /weather <city> - Get current weather
        /uptime - Show bot uptime
        /info - Show system information
        """
        await update.message.reply_text(help_text)


async def say(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        if context.args:
            message = " ".join(context.args)
            await update.message.reply_text(f"You said: {message}")
        else:
            await update.message.reply_text("Please provide a message after /say")


async def kiemtra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await update.message.reply_text(f"Bot is running! Current time: {current_time}")


async def cpu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            await update.message.reply_text(f"CPU Usage: {cpu_percent}%")
        except Exception as e:
            await update.message.reply_text(f"Error getting CPU usage: {str(e)}")
            logger.error(f"CPU command error: {str(e)}")


async def ram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        try:
            memory = psutil.virtual_memory()
            used = memory.used / (1024 * 1024 * 1024)
            total = memory.total / (1024 * 1024 * 1024)
            await update.message.reply_text(
                f"RAM Usage: {used:.2f}GB / {total:.2f}GB ({memory.percent}%)"
            )
        except Exception as e:
            await update.message.reply_text(f"Error getting RAM usage: {str(e)}")
            logger.error(f"RAM command error: {str(e)}")


async def disk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        try:
            disk = psutil.disk_usage("/")
            used = disk.used / (1024 * 1024 * 1024)
            total = disk.total / (1024 * 1024 * 1024)
            await update.message.reply_text(
                f"Disk Usage: {used:.2f}GB / {total:.2f}GB ({disk.percent}%)"
            )
        except Exception as e:
            await update.message.reply_text(f"Error getting disk usage: {str(e)}")
            logger.error(f"Disk command error: {str(e)}")


async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        if not context.args:
            await update.message.reply_text(
                "Please provide a city name after /weather (e.g., /weather London)"
            )
            return
        city = " ".join(context.args)
        weather_info = await get_weather(city)
        if weather_info:
            await update.message.reply_text(weather_info, parse_mode="Markdown")


async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        if config.start_time is None:
            await update.message.reply_text("Bot start time not set!")
            return
        uptime_seconds = time.time() - config.start_time
        hours, remainder = divmod(int(uptime_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        await update.message.reply_text(f"Bot uptime: {hours}h {minutes}m {seconds}s")


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        try:
            # System Info
            os_info = platform.system() + " " + platform.release()
            python_version = platform.python_version()
            cpu_count = psutil.cpu_count()

            # CPU Usage
            cpu_percent = psutil.cpu_percent(interval=3)

            # RAM Usage
            memory = psutil.virtual_memory()
            ram_used = memory.used / (1024 * 1024 * 1024)  # Convert to GB
            ram_total = memory.total / (1024 * 1024 * 1024)  # Convert to GB

            # Disk Usage
            disk = psutil.disk_usage("/")
            disk_used = disk.used / (1024 * 1024 * 1024)  # Convert to GB
            disk_total = disk.total / (1024 * 1024 * 1024)  # Convert to GB

            # Formatted message with icons (using HTML for better formatting)
            message = (
                "<b>System Information</b> 📊\n"
                f"💻 <b>OS:</b> {os_info}\n"
                f"🐍 <b>Python:</b> {python_version}\n"
                f"🧠 <b>CPU Cores:</b> {cpu_count}\n\n"
                "<b>Resource Usage</b> ⚙️\n"
                f"📈 <b>CPU:</b> {cpu_percent}% (over 3s)\n"
                f"🧮 <b>RAM:</b> {ram_used:.2f}GB / {ram_total:.2f}GB ({memory.percent}%)\n"
                f"💾 <b>Disk:</b> {disk_used:.2f}GB / {disk_total:.2f}GB ({disk.percent}%)"
            )

            await update.message.reply_text(message, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"Error retrieving system info: {str(e)}")
            logger.error(f"Info command error: {str(e)}")
