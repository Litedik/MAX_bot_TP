# max_api.py - Обёртка над MAX Bot API (platform-api2.max.ru)
# Авторизация: заголовок "Authorization: <token>" (без Bearer!)

import time
import requests
from config import MAX_TOKEN, MAX_API_URL, MAX_CA_BUNDLE
from logger import logger

HEADERS = {
    'Authorization': MAX_TOKEN,
    'Content-Type': 'application/json'
}

# Если задан путь к сертификату Минцифры — используем его, иначе системные сертификаты
VERIFY = MAX_CA_BUNDLE if MAX_CA_BUNDLE else True


def _request(method, path, params=None, body=None, timeout=15):
    """Базовый запрос к MAX Bot API"""
    url = f"{MAX_API_URL}{path}"
    try:
        response = requests.request(
            method, url,
            params=params, json=body,
            headers=HEADERS, timeout=timeout, verify=VERIFY
        )

        try:
            data = response.json()
        except ValueError:
            data = None

        if response.status_code == 200:
            # Часть методов возвращает ошибку с кодом 200 и success=false
            if isinstance(data, dict) and data.get('success') is False:
                logger.error(f"MAX API ошибка ({path}): {data.get('code')} — {data.get('message')}")
                return None
            return data

        logger.error(f"MAX API HTTP {response.status_code} ({path}): {response.text[:300]}")
        return None
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL-ошибка при запросе {path}: {e}. Установите сертификат Минцифры.")
        return None
    except Exception as e:
        logger.error(f"Ошибка связи с MAX API ({path}): {e}")
        return None


def get_me():
    """Информация о боте (проверка токена при запуске)"""
    return _request('GET', '/me')


def get_updates(marker=None, timeout=30, limit=100):
    """Long Polling: GET /updates. Возвращает (updates, marker)."""
    params = {'timeout': timeout, 'limit': limit}
    if marker is not None:
        params['marker'] = marker

    data = _request('GET', '/updates', params=params, timeout=timeout + 15)
    if data is None:
        return None, marker
    return data.get('updates', []), data.get('marker')


def build_message_body(text, keyboard=None, fmt='markdown', notify=True):
    """Собирает тело сообщения (NewMessageBody) для /messages и /answers"""
    body = {'text': text[:4000], 'notify': notify}
    if fmt:
        body['format'] = fmt
    if keyboard is not None:
        body['attachments'] = [{
            'type': 'inline_keyboard',
            'payload': {'buttons': keyboard}
        }]
    return body


def send_message(user_id, text, keyboard=None, fmt='markdown'):
    """Отправка НОВОГО сообщения: POST /messages?user_id=..."""
    body = build_message_body(text, keyboard, fmt)
    result = _request('POST', '/messages', params={'user_id': user_id}, body=body)
    if result is not None:
        logger.debug(f"[{user_id}] Сообщение отправлено")
    return result


def answer_callback(callback_id, notification=None, message=None):
    """
    Ответ на нажатие кнопки: POST /answers?callback_id=...
    ⭐ Если передать message (тело NewMessageBody) — ИСХОДНОЕ сообщение
    обновляется на месте (текст + клавиатура), без создания нового.
    """
    body = {}
    if notification:
        body['notification'] = notification
    if message is not None:
        body['message'] = message
    return _request('POST', '/answers', params={'callback_id': callback_id}, body=body)


def rate_limit_pause():
    """Пауза между рассылками (лимит MAX: 2 сообщения/сек в один диалог)"""
    time.sleep(0.6)