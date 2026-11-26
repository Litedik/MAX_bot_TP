# database.py - База данных MAX-бота (ключ — user_id MAX)

import sqlite3
from datetime import datetime
from config import DB_FILE, STATE_WAIT_CODE
from logger import logger


def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_states (
        user_id INTEGER PRIMARY KEY,
        state TEXT NOT NULL DEFAULT 'WAIT_CODE',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS linked_users (
        user_id INTEGER PRIMARY KEY,
        platform TEXT DEFAULT 'max',
        site_id INTEGER,
        user_name TEXT,
        site_name TEXT,
        unique_code TEXT UNIQUE,
        linked_at TEXT NOT NULL
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS notification_settings (
        user_id INTEGER PRIMARY KEY,
        platform TEXT DEFAULT 'max',
        notify_forecast INTEGER DEFAULT 1,
        notify_chat INTEGER DEFAULT 1,
        notify_fantasy INTEGER DEFAULT 1,
        notify_1h INTEGER DEFAULT 0,
        notify_2h INTEGER DEFAULT 0,
        notify_5h INTEGER DEFAULT 0,
        notify_12h INTEGER DEFAULT 0,
        notify_24h INTEGER DEFAULT 1,
        notify_fantasy_1h INTEGER DEFAULT 1,
        notify_fantasy_2h INTEGER DEFAULT 1,
        notify_fantasy_3h INTEGER DEFAULT 1,
        notify_fantasy_6h INTEGER DEFAULT 1,
        notify_fantasy_12h INTEGER DEFAULT 1,
        notify_fantasy_24h INTEGER DEFAULT 1,
        updated_at TEXT NOT NULL
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS notification_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        notification_type TEXT NOT NULL,
        event_id TEXT NOT NULL,
        sent_at TEXT NOT NULL,
        UNIQUE(user_id, notification_type, event_id)
    )''')

    conn.commit()
    conn.close()
    logger.info(f"✅ База данных {DB_FILE} инициализирована")


def get_user_state(user_id):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT state FROM user_states WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else STATE_WAIT_CODE
    finally:
        conn.close()


def set_user_state(user_id, state):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute('SELECT user_id FROM user_states WHERE user_id = ?', (user_id,))
        if cursor.fetchone():
            cursor.execute('UPDATE user_states SET state = ?, updated_at = ? WHERE user_id = ?', (state, now, user_id))
        else:
            cursor.execute('INSERT INTO user_states (user_id, state, created_at, updated_at) VALUES (?, ?, ?, ?)', (user_id, state, now, now))
        conn.commit()
    finally:
        conn.close()


def delete_user_data(user_id):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM linked_users WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM notification_settings WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM notification_history WHERE user_id = ?', (user_id,))
        conn.commit()
        logger.info(f"[{user_id}] Все данные пользователя удалены из БД")
    finally:
        conn.close()


def save_linked_user(user_id, site_id, user_name, site_name, unique_code):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute('''INSERT OR REPLACE INTO linked_users
            (user_id, platform, site_id, user_name, site_name, unique_code, linked_at)
            VALUES (?, 'max', ?, ?, ?, ?, ?)''', (user_id, site_id, user_name, site_name, unique_code, now))
        conn.commit()
        logger.info(f"[{user_id}] Пользователь сохранен: site_id={site_id}, site_name={site_name}")
        return True
    except Exception as e:
        logger.error(f"[{user_id}] Ошибка сохранения: {e}")
        return False
    finally:
        conn.close()


def get_linked_user(user_id):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM linked_users WHERE user_id = ?', (user_id,))
        r = cursor.fetchone()
        if r:
            return {'user_id': r[0], 'platform': r[1], 'site_id': r[2],
                    'user_name': r[3], 'site_name': r[4], 'unique_code': r[5], 'linked_at': r[6]}
        return None
    finally:
        conn.close()


def is_user_linked(user_id):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT user_id FROM linked_users WHERE user_id = ?', (user_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def get_all_linked_users():
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, site_id, site_name FROM linked_users WHERE platform = 'max'")
        return [{'user_id': r[0], 'site_id': r[1], 'site_name': r[2]} for r in cursor.fetchall()]
    finally:
        conn.close()


def get_notification_settings(user_id):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM notification_settings WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        if result:
            d = dict(result)
            return {
                'user_id': d['user_id'],
                'notify_forecast': bool(d.get('notify_forecast', 1)),
                'notify_chat': bool(d.get('notify_chat', 1)),
                'notify_fantasy': bool(d.get('notify_fantasy', 1)),
                'notify_1h': bool(d.get('notify_1h', 0)),
                'notify_2h': bool(d.get('notify_2h', 0)),
                'notify_5h': bool(d.get('notify_5h', 0)),
                'notify_12h': bool(d.get('notify_12h', 0)),
                'notify_24h': bool(d.get('notify_24h', 1)),
                'notify_fantasy_1h': bool(d.get('notify_fantasy_1h', 1)),
                'notify_fantasy_2h': bool(d.get('notify_fantasy_2h', 1)),
                'notify_fantasy_3h': bool(d.get('notify_fantasy_3h', 1)),
                'notify_fantasy_6h': bool(d.get('notify_fantasy_6h', 1)),
                'notify_fantasy_12h': bool(d.get('notify_fantasy_12h', 1)),
                'notify_fantasy_24h': bool(d.get('notify_fantasy_24h', 1)),
            }
        return {
            'user_id': user_id,
            'notify_forecast': True, 'notify_chat': True, 'notify_fantasy': True,
            'notify_1h': False, 'notify_2h': False, 'notify_5h': False,
            'notify_12h': False, 'notify_24h': True,
            'notify_fantasy_1h': True, 'notify_fantasy_2h': True, 'notify_fantasy_3h': True,
            'notify_fantasy_6h': True, 'notify_fantasy_12h': True, 'notify_fantasy_24h': True,
        }
    finally:
        conn.close()


def toggle_notification_setting(user_id, setting_name):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    allowed_settings = [
        'notify_forecast', 'notify_chat', 'notify_fantasy',
        'notify_1h', 'notify_2h', 'notify_5h', 'notify_12h', 'notify_24h',
        'notify_fantasy_1h', 'notify_fantasy_2h', 'notify_fantasy_3h',
        'notify_fantasy_6h', 'notify_fantasy_12h', 'notify_fantasy_24h'
    ]

    if setting_name not in allowed_settings:
        conn.close()
        return False

    try:
        current = get_notification_settings(user_id).get(setting_name, True)
        new_value = 0 if current else 1

        cursor.execute('SELECT user_id FROM notification_settings WHERE user_id = ?', (user_id,))
        if cursor.fetchone():
            cursor.execute(f'UPDATE notification_settings SET {setting_name} = ?, updated_at = ? WHERE user_id = ?', (new_value, now, user_id))
        else:
            defaults = {
                'notify_forecast': 1, 'notify_chat': 1, 'notify_fantasy': 1,
                'notify_1h': 0, 'notify_2h': 0, 'notify_5h': 0, 'notify_12h': 0, 'notify_24h': 1,
                'notify_fantasy_1h': 1, 'notify_fantasy_2h': 1, 'notify_fantasy_3h': 1,
                'notify_fantasy_6h': 1, 'notify_fantasy_12h': 1, 'notify_fantasy_24h': 1
            }
            defaults[setting_name] = new_value
            cursor.execute('''INSERT INTO notification_settings
                (user_id, platform, notify_forecast, notify_chat, notify_fantasy,
                 notify_1h, notify_2h, notify_5h, notify_12h, notify_24h,
                 notify_fantasy_1h, notify_fantasy_2h, notify_fantasy_3h,
                 notify_fantasy_6h, notify_fantasy_12h, notify_fantasy_24h, updated_at)
                VALUES (?, 'max', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, defaults['notify_forecast'], defaults['notify_chat'],
                 defaults['notify_fantasy'], defaults['notify_1h'], defaults['notify_2h'],
                 defaults['notify_5h'], defaults['notify_12h'], defaults['notify_24h'],
                 defaults['notify_fantasy_1h'], defaults['notify_fantasy_2h'],
                 defaults['notify_fantasy_3h'], defaults['notify_fantasy_6h'],
                 defaults['notify_fantasy_12h'], defaults['notify_fantasy_24h'], now))
        conn.commit()
        logger.info(f"[{user_id}] Настройка {setting_name} переключена на {new_value}")
        return True
    except Exception as e:
        logger.error(f"[{user_id}] Ошибка переключения настройки: {e}")
        return False
    finally:
        conn.close()


def is_notification_sent(user_id, notification_type, event_id):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM notification_history WHERE user_id = ? AND notification_type = ? AND event_id = ?', (user_id, notification_type, str(event_id)))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def mark_notification_sent(user_id, notification_type, event_id):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute('INSERT OR IGNORE INTO notification_history (user_id, notification_type, event_id, sent_at) VALUES (?, ?, ?, ?)', (user_id, notification_type, str(event_id), now))
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка записи истории: {e}")
    finally:
        conn.close()


def cleanup_old_history(days=30):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM notification_history WHERE sent_at < datetime('now', ?)", (f'-{days} days',))
        conn.commit()
        logger.info(f"Очищена старая история уведомлений (старше {days} дней)")
    finally:
        conn.close()
        
# ============================================
# ⭐ ФУНКЦИИ ДЛЯ АДМИН-ПАНЕЛИ
# ============================================

def get_linked_users_count():
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM linked_users WHERE platform = 'max'")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_recent_linked_users(limit=5):
    conn = sqlite3.connect(DB_FILE, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, site_id, site_name, linked_at FROM linked_users WHERE platform = 'max' ORDER BY linked_at DESC LIMIT ?", (limit,))
        return [{'user_id': r[0], 'site_id': r[1], 'site_name': r[2], 'linked_at': r[3]} for r in cursor.fetchall()]
    finally:
        conn.close()