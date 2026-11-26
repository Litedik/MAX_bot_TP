# max_keyboards.py - Inline-клавиатуры MAX (формат: rows кнопок)
# Кнопка действия: {'type': 'callback', 'text': ..., 'payload': ...}
# Кнопка-ссылка:   {'type': 'link', 'text': ..., 'url': ...}

LINK_PAGE_URL = 'https://trubnik.info/profile/linkbot?featured=max'


def create_link_keyboard():
    return [
        [{'type': 'link', 'text': '🔑 Получить код для привязки', 'url': LINK_PAGE_URL}]
    ]


def create_main_keyboard():
    return [
        [{'type': 'callback', 'text': '⚙️ Настройки уведомлений', 'payload': 'settings'}],
        [{'type': 'callback', 'text': '🔗 Мой профиль', 'payload': 'profile'}]
    ]


def create_settings_keyboard(settings):
    rows = [
        [{'type': 'callback', 'text': f"📊 Прогнозы: {'✅' if settings['notify_forecast'] else '❌'}", 'payload': 'toggle:notify_forecast'}],
        [{'type': 'callback', 'text': f"💬 Сообщения в командном чате: {'✅' if settings['notify_chat'] else '❌'}", 'payload': 'toggle:notify_chat'}],
        [{'type': 'callback', 'text': f"🏑 Фэнтези: {'✅' if settings['notify_fantasy'] else '❌'}", 'payload': 'toggle:notify_fantasy'}],
    ]

    if settings['notify_forecast']:
        rows.append([{'type': 'callback', 'text': '⏰ Напоминания о матчах →', 'payload': 'reminders'}])

    if settings['notify_fantasy']:
        rows.append([{'type': 'callback', 'text': '🏑 Напоминания о фэнтези →', 'payload': 'fantasy_reminders'}])

    rows.append([{'type': 'callback', 'text': '🔙 Назад в меню', 'payload': 'back'}])
    return rows


def _hours_word(h):
    return 'час' if h == 1 else 'часа' if h < 5 else 'часов'


def create_reminders_keyboard(settings):
    rows = []
    for hours, key in [(1, 'notify_1h'), (2, 'notify_2h'), (5, 'notify_5h'), (12, 'notify_12h'), (24, 'notify_24h')]:
        rows.append([{
            'type': 'callback',
            'text': f"🔔 За {hours} {_hours_word(hours)}: {'✅' if settings[key] else '❌'}",
            'payload': f'toggle:{key}'
        }])
    rows.append([{'type': 'callback', 'text': '🔙 К настройкам', 'payload': 'settings'}])
    return rows


def create_fantasy_reminders_keyboard(settings):
    rows = []
    for hours, key in [(1, 'notify_fantasy_1h'), (2, 'notify_fantasy_2h'), (3, 'notify_fantasy_3h'),
                       (6, 'notify_fantasy_6h'), (12, 'notify_fantasy_12h'), (24, 'notify_fantasy_24h')]:
        rows.append([{
            'type': 'callback',
            'text': f"🔔 За {hours} {_hours_word(hours)}: {'✅' if settings[key] else '❌'}",
            'payload': f'toggle:{key}'
        }])
    rows.append([{'type': 'callback', 'text': '✅ Готово', 'payload': 'settings'}])
    return rows


def create_profile_keyboard():
    return [
        [{'type': 'callback', 'text': '🔓 Отвязать аккаунт', 'payload': 'unlink'}],
        [{'type': 'callback', 'text': '🔙 Назад', 'payload': 'back'}]
    ]


def create_unlink_confirm_keyboard():
    return [
        [{'type': 'callback', 'text': '✅ Да, отвязать', 'payload': 'unlink_confirm_yes'}],
        [{'type': 'callback', 'text': '❌ Нет, отмена', 'payload': 'back'}]
    ]
    
# ============================================
# ⭐ АДМИН-КЛАВИАТУРЫ
# ============================================

def create_admin_main_keyboard():
    """Главное меню АДМИНА: обычные кнопки + Статус и Пользователи"""
    rows = create_main_keyboard()
    rows.append([
        {'type': 'callback', 'text': '📊 Статус', 'payload': 'status'},
        {'type': 'callback', 'text': '👥 Пользователи', 'payload': 'users'}
    ])
    return rows


def create_admin_back_keyboard():
    return [[{'type': 'callback', 'text': '🔙 Назад', 'payload': 'back'}]]