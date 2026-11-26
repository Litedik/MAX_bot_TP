# logger.py - Логирование для MAX-бота

import logging
import sys
from config import LOG_LEVEL, LOG_FILE

logger = logging.getLogger('max_trubnik_bot')
logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

# Вывод в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(console_fmt)
logger.addHandler(console_handler)

# Вывод в файл
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_fmt)
logger.addHandler(file_handler)