# bot_stats.py - Статистика работы бота (в памяти процесса)

import threading
from datetime import datetime, timezone, timedelta

EKB_TZ = timezone(timedelta(hours=5))  # Екатеринбург, UTC+5

_lock = threading.Lock()
_stats = {'chat': None, 'forecasts': None, 'fantasy': None, 'last_error': None}


def mark_check(kind):
    with _lock:
        if kind in _stats:
            _stats[kind] = datetime.now(EKB_TZ)


def mark_error(kind, message):
    with _lock:
        _stats['last_error'] = (datetime.now(EKB_TZ), kind, str(message)[:250])


def get_stats():
    with _lock:
        return dict(_stats)


def fmt_dt(dt):
    return dt.strftime('%d.%m.%Y %H:%M:%S') if dt else 'ещё не было'