# config.py - Настройки MAX-бота

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# --- MAX Bot API ---
MAX_TOKEN = os.getenv('MAX_TOKEN')
MAX_BOT_ID = os.getenv('MAX_BOT_ID')
MAX_API_URL = 'https://platform-api2.max.ru'
MAX_CA_BUNDLE = os.getenv('MAX_CA_BUNDLE', '')

# --- Сайт ---
SITE_API_URL = os.getenv('SITE_API_URL')
SITE_API_UNLINK_URL = os.getenv('SITE_API_UNLINK_URL', 'https://trubnik.info/api/unlink_bot.php')
BOT_SECRET_KEY = os.getenv('BOT_SECRET_KEY')
SITE_API_FORECASTS = os.getenv('SITE_API_FORECASTS', 'https://trubnik.info/api/get_forecasts.php')
SITE_API_CHAT = os.getenv('SITE_API_CHAT', 'https://trubnik.info/api/get_chat_messages.php')
SITE_API_FANTASY = os.getenv('SITE_API_FANTASY', 'https://trubnik.info/api/get_fantasy.php')

# --- ⭐ АДМИНЫ ---
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').replace(';', ',').split(',') if x.strip().isdigit()]

# --- База данных ---
DB_FILE = os.getenv('DB_FILE', 'max_bot_database.db')

# --- Логирование ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'max_bot.log')

# --- Планировщик ---
SCHEDULER_INTERVAL = int(os.getenv('SCHEDULER_INTERVAL', '300'))
CHAT_INTERVAL = int(os.getenv('CHAT_INTERVAL', '120'))
FORECAST_INTERVAL = int(os.getenv('FORECAST_INTERVAL', '600'))
FANTASY_INTERVAL = int(os.getenv('FANTASY_INTERVAL', '600'))

# --- Состояния пользователей ---
STATE_WAIT_CODE = 'WAIT_CODE'
STATE_LINKED = 'LINKED'
STATE_SETTINGS = 'SETTINGS'
STATE_SETTINGS_REMINDERS = 'SETTINGS_REMINDERS'
STATE_SETTINGS_FANTASY = 'SETTINGS_FANTASY'
STATE_UNLINK_CONFIRM = 'UNLINK_CONFIRM'

if not MAX_TOKEN:
    raise ValueError("❌ Ошибка: MAX_TOKEN не задан в файле .env")
if not BOT_SECRET_KEY:
    raise ValueError("❌ Ошибка: BOT_SECRET_KEY не задан в файле .env")