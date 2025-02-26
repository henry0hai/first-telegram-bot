# src/config.py
import os
from asyncio import Lock
from dotenv import load_dotenv
from src.__version__ import VERSION
import logging
from logging.handlers import RotatingFileHandler

# Load .env file
load_dotenv()

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_USER_NAME = os.getenv("ADMIN_USER_NAME")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
CITIES = os.getenv("CITIES", "").split(",")
HF_API_KEY = os.getenv("HF_API_KEY")

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
START_TIME = None
DEBUG_TIME_LOOP = 1800  # 30 minutes
SCHEDULED_WEATHER_LOOP = 7200  # 2 hours

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
        self.hf_key_api = HF_API_KEY
        self.debug_time_loop = DEBUG_TIME_LOOP
        self.scheduled_weather_loop = SCHEDULED_WEATHER_LOOP
        self.app_version = VERSION

config = BotConfig()

# Logging setup with file handler
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(log_dir, exist_ok=True)  # Use exist_ok to avoid race conditions

log_file = os.path.join(log_dir, "telegram_bot.log")
handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=2)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Optional console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Bot state (avoid global variables where possible)
bot_lock = Lock()  # Keep it as asyncio.Lock for async compatibility

# Test log to confirm setup
logger.info("Logging initialized!")