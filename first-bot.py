import os
import sys
import time
import pytz  # For timezone handling
import fcntl  # For Unix-like systems
import signal
import psutil
import logging
import requests
import platform
import threading

from telegram import Update
from functools import partial
from datetime import datetime
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create a lock for thread safety
bot_lock = threading.Lock()

# Record bot start time
START_TIME = time.time()

# Token from BotFather
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Your Telegram user ID (for /stop command)
ADMIN_ID = os.getenv("ADMIN_ID")  # Replace with your actual ID
ADMIN_USER_NAME = os.getenv(
    "ADMIN_USER_NAME"
)  # Replace with your actual admin user name

# OpenWeatherMap API key (get one from openweathermap.org)
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

CITIES = os.getenv("CITIES", "").split(",")  # Split comma-separated string into list

# Validate environment variables
if not all([TELEGRAM_BOT_TOKEN, ADMIN_ID, WEATHER_API_KEY, CITIES]):
    raise ValueError(
        "Missing required environment variables: TELEGRAM_BOT_TOKEN, ADMIN_ID, WEATHER_API_KEY, or CITIES"
    )

# Weather condition icons (Unicode emojis)
WEATHER_ICONS = {
    "Clear": "☀️",  # Clear sky
    "Clouds": "☁️",  # Cloudy
    "Rain": "🌧️",  # Rain
    "Drizzle": "🌦️",  # Light rain
    "Thunderstorm": "⛈️",  # Thunderstorm
    "Snow": "❄️",  # Snow
    "Mist": "🌫️",  # Mist/Fog
    "Haze": "🌫️",  # Haze
}

# Additional icons
ICON_WIND = "💨"  # Wind
ICON_TEMP = "🌡️"  # Temperature
ICON_HUMIDITY = "💧"  # Humidity
ICON_SUNRISE = "🌅"  # Sunrise
ICON_SUNSET = "🌇"  # Sunset
ICON_TIME = "🕒"  # Time

# Global variables to track bot state
is_bot_running = False
job_queue = None


# Command handlers
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_running, job_queue

    with bot_lock:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.username
        if user_name != ADMIN_USER_NAME:
            print(f"user_id: {user_id}")
            print(f"user_name: {user_name}")
            await update.message.reply_text("Sorry, only the admin can stop the bot.")
            return

        if not is_bot_running:
            await update.message.reply_text("Bot activities are already stopped!")
            return

        await update.message.reply_text("Bot activities are stopping...")
        logger.info("Bot activities stopped by admin")

        # Stop all scheduled jobs
        if job_queue:
            for job in job_queue.jobs():
                job.schedule_removal()
            logger.info("All scheduled jobs removed")

        # Mark bot as not running
        is_bot_running = False

        # Note: We're not stopping the application, just the scheduled activities


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_running, job_queue

    with bot_lock:
        user = update.message.from_user.first_name

        # If bot is already running, just send a greeting
        if is_bot_running:
            message = f"Hello {user}! The bot is already running. Use /help to see available commands."
            await update.message.reply_text(message)
            return

        # Bot was stopped, we need to restart everything
        message = f"Hello {user}! I'm your bot. Restarting all activities now. Use /help to see available commands."
        await update.message.reply_text(message)

        # Restart the job queue if it exists
        if job_queue:
            # First, clear any existing jobs (just to be safe)
            for job in job_queue.jobs():
                job.schedule_removal()

            # Re-schedule all the jobs
            job_queue.run_once(partial(on_startup, user=user), 0)
            job_queue.run_repeating(scheduled_weather, interval=7200, first=0)
            job_queue.run_repeating(debug_time, interval=10, first=0)

            logger.info(f"User {user} restarted all bot activities")

        # Mark bot as running
        is_bot_running = True


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
            used = memory.used / (1024 * 1024 * 1024)  # Convert to GB
            total = memory.total / (1024 * 1024 * 1024)  # Convert to GB
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
            used = disk.used / (1024 * 1024 * 1024)  # Convert to GB
            total = disk.total / (1024 * 1024 * 1024)  # Convert to GB
            await update.message.reply_text(
                f"Disk Usage: {used:.2f}GB / {total:.2f}GB ({disk.percent}%)"
            )
        except Exception as e:
            await update.message.reply_text(f"Error getting disk usage: {str(e)}")
            logger.error(f"Disk command error: {str(e)}")


# Function to convert degrees to cardinal direction
def degrees_to_direction(deg):
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(deg / 45) % 8
    return directions[index]


# Function to get weather data (shared logic)
async def get_weather(city, context=None, chat_id=None):
    try:
        params = {"q": city, "appid": WEATHER_API_KEY, "units": "metric"}
        response = requests.get(WEATHER_BASE_URL, params=params)
        data = response.json()
        if data.get("cod") != 200:
            error_msg = f"Error for {city}: {data.get('message', 'City not found')}"
            if context and chat_id:
                await context.bot.send_message(chat_id=chat_id, text=error_msg)
            return None

        condition_main = data["weather"][0]["main"]
        condition_desc = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        temp_max = data["main"]["temp_max"]
        temp_min = data["main"]["temp_min"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"] * 3.6
        wind_deg = data["wind"]["deg"]
        sunrise = data["sys"]["sunrise"]
        sunset = data["sys"]["sunset"]
        timezone_offset = data["timezone"]
        country = data["sys"]["country"]

        icon = WEATHER_ICONS.get(condition_main, "🌍")
        utc = pytz.utc
        local_tz = pytz.timezone(
            f"Etc/GMT{'+' if timezone_offset < 0 else '-'}{abs(timezone_offset) // 3600}"
        )
        sunrise_dt = datetime.fromtimestamp(sunrise, utc).astimezone(local_tz)
        sunset_dt = datetime.fromtimestamp(sunset, utc).astimezone(local_tz)
        current_dt = datetime.now(utc).astimezone(local_tz)
        local_now = datetime.now()

        tz_offset_str = (
            f"GMT{'+' if timezone_offset >= 0 else '-'}{abs(timezone_offset) // 3600}"
        )

        weather_info = (
            f"Weather in: *{city}:*\n"
            f"{icon} Condition: {condition_main} - {condition_desc}\n"
            f"{ICON_TEMP} Temp: {temp}°C, Feels like: {feels_like}°C\n"
            f"{ICON_TEMP} Range: {temp_max}°C (max) - {temp_min}°C (min)\n"
            f"{ICON_HUMIDITY} Humidity: {humidity}%\n"
            f"{ICON_WIND} Wind: {wind_speed:.2f} km/h, Direction: {degrees_to_direction(wind_deg)}\n"
            f"{ICON_SUNRISE} Sunrise: {sunrise_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"{ICON_SUNSET} Sunset: {sunset_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"{ICON_TIME} Location Time: {current_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} ({tz_offset_str}, {country})\n"
            f"{ICON_TIME} Local Time: {local_now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )

        logger.info(f"Weather data for {city}: {data}")
        return weather_info

    except Exception as e:
        logger.error(f"Error fetching weather for {city}: {str(e)}")
        if context and chat_id:
            await context.bot.send_message(
                chat_id=chat_id, text=f"Error fetching weather for {city}: {str(e)}"
            )
        return None


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


# Scheduled weather update for cities in .env
async def scheduled_weather(context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        for city in CITIES:
            city = city.strip()  # Remove any extra whitespace
            if city:  # Skip empty entries
                weather_info = await get_weather(city, context, ADMIN_ID)
                if weather_info:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID, text=weather_info, parse_mode="Markdown"
                    )


async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        uptime_seconds = time.time() - START_TIME
        hours, remainder = divmod(int(uptime_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        await update.message.reply_text(f"Bot uptime: {hours}h {minutes}m {seconds}s")


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with bot_lock:
        os_info = platform.system() + " " + platform.release()
        python_version = platform.python_version()
        cpu_count = psutil.cpu_count()
        await update.message.reply_text(
            f"System Info:\nOS: {os_info}\nPython: {python_version}\nCPU Cores: {cpu_count}"
        )


# Debug function to send current time
async def debug_time(context: ContextTypes.DEFAULT_TYPE):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await context.bot.send_message(
        chat_id=ADMIN_ID, text=f"Debug: Current time is {current_time}"
    )
    logger.info(f"Debug time sent: {current_time}")


# Run startup logic and notify admin
async def on_startup(context: ContextTypes.DEFAULT_TYPE, user=None):
    with bot_lock:
        notification = "Bot activities have been started successfully! Use /help to see available commands."
        if user:
            notification = f"Bot activities restarted by {user}! Use /help to see available commands."

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=notification,
        )
        logger.info("Bot startup notification sent to admin")


# Define an error handler
async def error_handler(update, context):
    logger.error(f"Error occurred: {context.error}")


def ensure_single_instance():
    """Ensure only one instance of the bot is running using a lock file."""
    lock_file_path = "/tmp/telegram_bot.lock"  # Adjust path as needed for your system

    # Create lock file
    try:
        # Create the file if it doesn't exist
        lock_file = open(lock_file_path, "w")

        # Try to acquire an exclusive lock (non-blocking)
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Keep a reference to prevent garbage collection
        return lock_file
    except IOError:
        logger.error("Another instance of the bot is already running!")
        logger.error("Please stop that instance first or use 'pkill -f your_script.py'")
        sys.exit(1)


def main():
    """Start the bot."""
    global is_bot_running, job_queue
    # Ensure only one instance is running
    lock_file = ensure_single_instance()

    # Build the application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Store reference to job queue
    job_queue = application.job_queue

    # Reset any webhook (just to be safe)
    async def remove_webhook(context):
        await context.bot.delete_webhook()
        logger.info("Removed webhook to ensure clean polling")

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("say", say))
    application.add_handler(CommandHandler("kiemtra", kiemtra))
    application.add_handler(CommandHandler("cpu", cpu))
    application.add_handler(CommandHandler("ram", ram))
    application.add_handler(CommandHandler("disk", disk))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(CommandHandler("uptime", uptime))
    application.add_handler(CommandHandler("info", info))

    """Initial scheduling."""
    # Schedule the startup task
    job_queue.run_once(on_startup, 0)

    # Schedule weather updates every 2 hours (7200 seconds)
    job_queue.run_repeating(scheduled_weather, interval=7200, first=0)

    # Debug task - run every 10 seconds
    job_queue.run_repeating(debug_time, interval=10, first=0)

    # Mark bot as running
    is_bot_running = True

    # Start the bot
    print("Bot is running... Press Ctrl+C to stop")
    application.add_error_handler(error_handler)

    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"Bot stopped unexpectedly: {e}")
    finally:
        # Release the lock when done
        if lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
            logger.info("Lock file released")


if __name__ == "__main__":
    main()
