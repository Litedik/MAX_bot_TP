# site_api.py - Функции для работы с сайтом (MAX-версия, + статистика)

import requests
from config import (
    SITE_API_URL, SITE_API_UNLINK_URL,
    SITE_API_FORECASTS, SITE_API_CHAT, SITE_API_FANTASY,
    BOT_SECRET_KEY
)
import bot_stats
from logger import logger


def link_account_on_site(platform, bot_user_id, user_code):
    try:
        payload = {'platform': str(platform), 'bot_user_id': str(bot_user_id),
                   'code': str(user_code), 'secret': BOT_SECRET_KEY}
        response = requests.post(SITE_API_URL, data=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                return True, 'Успешно', result.get('site_id'), result.get('site_name', 'Пользователь')
            return False, result.get('message', 'Ошибка'), None, None
        return False, "Ошибка сервера", None, None
    except Exception as e:
        logger.error(f"Ошибка связи с сайтом: {e}")
        return False, "Не удалось связаться с сайтом", None, None


def unlink_account_on_site(platform, bot_user_id):
    try:
        payload = {'platform': str(platform), 'bot_user_id': str(bot_user_id), 'secret': BOT_SECRET_KEY}
        response = requests.post(SITE_API_UNLINK_URL, data=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                return True, 'Успешно', result.get('affected', 0)
            return False, result.get('message', 'Ошибка'), 0
        return False, f"Ошибка сервера (HTTP {response.status_code})", 0
    except Exception as e:
        logger.error(f"Ошибка при отвязке на сайте: {e}")
        return False, "Не удалось связаться с сайтом", 0


def _fetch_site_data(api_url, timeout=10, kind=None):
    try:
        response = requests.post(api_url, data={'secret': BOT_SECRET_KEY}, timeout=timeout)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                if kind:
                    bot_stats.mark_check(kind)
                return result
            msg = f"Сайт вернул ошибку: {result.get('message')}"
            logger.error(msg)
            if kind:
                bot_stats.mark_error(kind, msg)
            return None
        msg = f"Сайт вернул код {response.status_code}"
        logger.error(msg)
        if kind:
            bot_stats.mark_error(kind, msg)
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Таймаут при обращении к {api_url}")
        if kind:
            bot_stats.mark_error(kind, 'Таймаут запроса')
        return None
    except Exception as e:
        logger.error(f"Ошибка запроса к {api_url}: {e}")
        if kind:
            bot_stats.mark_error(kind, e)
        return None


def get_forecasts():
    data = _fetch_site_data(SITE_API_FORECASTS, kind='forecasts')
    return data if data else {}


def get_chat_messages():
    data = _fetch_site_data(SITE_API_CHAT, kind='chat')
    return data.get('data', []) if data else []


def get_fantasy_teams():
    data = _fetch_site_data(SITE_API_FANTASY, kind='fantasy')
    return data if data else {}