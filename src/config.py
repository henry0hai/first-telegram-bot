# src/config.py
import os
import threading
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Logging setup
import logging


# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_USER_NAME = os.getenv("ADMIN_USER_NAME")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
CITIES = os.getenv("CITIES", "").split(",")

# Validate environment variables
if not all([TELEGRAM_BOT_TOKEN, ADMIN_ID, WEATHER_API_KEY, CITIES]):
    raise ValueError(
        "Missing required environment variables: TELEGRAM_BOT_TOKEN, ADMIN_ID, WEATHER_API_KEY, or CITIES"
    )

# Weather condition icons
WEATHER_ICONS = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Haze": "🌫️",
}
ICON_WIND, ICON_TEMP, ICON_HUMIDITY = "💨", "🌡️", "💧"
ICON_SUNRISE, ICON_SUNSET, ICON_TIME = "🌅", "🌇", "🕒"

# Global state
START_TIME = None  # Will be set in bot.py

DEBUG_TIME_LOOP = 1800 # 30 minutes
SCHEDULED_WEATHER_LOOP = 7200 # 2 hours

class BotConfig:
    def __init__(self):
        self.is_bot_running = False
        self.start_time = None
        self.job_queue = None
        self.telegram_bot_token = TELEGRAM_BOT_TOKEN
        self.admin_user_name = ADMIN_USER_NAME
        self.admin_id = ADMIN_ID
        self.weather_api_key = WEATHER_API_KEY
        self.weather_base_url = WEATHER_BASE_URL
        self.cities = CITIES
        self.debug_time_loop = DEBUG_TIME_LOOP
        self.scheduled_weather_loop = SCHEDULED_WEATHER_LOOP


config = BotConfig()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

is_bot_running = False
job_queue = None
bot_lock = threading.Lock()
