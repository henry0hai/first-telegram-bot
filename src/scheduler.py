# src/scheduler.py
from telegram.ext import ContextTypes
from src.config import ADMIN_ID, CITIES, bot_lock, logger
from src.utils import get_weather
from datetime import datetime


async def on_startup(context: ContextTypes.DEFAULT_TYPE, user=None):
    with bot_lock:
        notification = "Bot activities have been started successfully! Use /help to see available commands."
        if user:
            notification = f"Bot activities restarted by {user}! Use /help to see available commands."
        await context.bot.send_message(chat_id=ADMIN_ID, text=notification)
        logger.info(
            f"Startup notification sent to admin (triggered by: {user or 'system'})"
        )


async def scheduled_weather(context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        if not CITIES or all(not city.strip() for city in CITIES):
            logger.warning(
                "No valid cities defined in CITIES for scheduled weather updates"
            )
            return
        for city in CITIES:
            city = city.strip()
            if city:
                weather_info = await get_weather(city, context, ADMIN_ID)
                if weather_info:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID, text=weather_info, parse_mode="Markdown"
                    )
                else:
                    logger.warning(
                        f"Failed to fetch weather for {city} in scheduled update"
                    )


async def debug_time(context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await context.bot.send_message(
            chat_id=ADMIN_ID, text=f"Debug: Current time is {current_time}"
        )
        logger.info(f"Debug time message sent: {current_time}")
