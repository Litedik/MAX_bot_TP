# max_bot.py - MAX-бот (+ админ-панель: Статус, Пользователи, уведомления админам)
# Навигация по кнопкам обновляет сообщение на месте (POST /answers с message)

import time
from datetime import datetime
from config import (
    ADMIN_IDS, CHAT_INTERVAL, FORECAST_INTERVAL, FANTASY_INTERVAL,
    STATE_WAIT_CODE, STATE_LINKED, STATE_SETTINGS,
    STATE_SETTINGS_REMINDERS, STATE_SETTINGS_FANTASY, STATE_UNLINK_CONFIRM
)
from database import (
    init_db, get_user_state, set_user_state, save_linked_user,
    get_linked_user, delete_user_data, is_user_linked,
    get_notification_settings, toggle_notification_setting,
    get_linked_users_count, get_recent_linked_users
)
from max_api import (
    send_message, get_updates, answer_callback, get_me, build_message_body
)
from site_api import link_account_on_site, unlink_account_on_site
from max_keyboards import (
    create_link_keyboard, create_main_keyboard,
    create_settings_keyboard, create_reminders_keyboard,
    create_fantasy_reminders_keyboard,
    create_profile_keyboard, create_unlink_confirm_keyboard,
    create_admin_main_keyboard, create_admin_back_keyboard
)
from scheduler import start_scheduler
import bot_stats
from logger import logger


LINK_TEXT = (
    "👋 Привет! Я бот ХК «СКА-Уральский Трубник».\n\n"
    "🔗 Давайте свяжем ваш профиль MAX с аккаунтом на сайте trubnik.info.\n\n"
    "👇 Нажмите кнопку ниже, чтобы получить код привязки.\n"
    "После получения кода — отправьте его мне следующим сообщением."
)

UNLINK_CONFIRM_TEXT = (
    "⚠️ Вы действительно хотите отвязать аккаунт от сайта?\n\n"
    "Все ваши данные будут удалены из бота."
)

KIND_RU = {'chat': 'чат', 'forecasts': 'прогнозы', 'fantasy': 'фэнтези'}


def is_admin(user_id):
    return user_id in ADMIN_IDS


def main_keyboard_for(user_id):
    return create_admin_main_keyboard() if is_admin(user_id) else create_main_keyboard()


# ============================================
# ⭐ УВЕДОМЛЕНИЯ АДМИНАМ
# ============================================

def notify_admins(text, keyboard=None):
    for admin_id in ADMIN_IDS:
        try:
            send_message(admin_id, text, keyboard)
        except Exception as e:
            logger.error(f"Не удалось уведомить админа {admin_id}: {e}")


def notify_admins_link(user_id, site_id, site_name):
    kb = [[{'type': 'link', 'text': '🌐 Открыть сайт', 'url': 'https://trubnik.info'}]]
    msg = (f"👤 **Профиль привязан**\n——————————————\n"
           f"MAX ID: {user_id}\nПрофиль сайта: {site_name} (ID {site_id})")
    notify_admins(msg, kb)


def notify_admins_unlink(user_id, site_id, site_name):
    kb = [[{'type': 'link', 'text': '🌐 Открыть сайт', 'url': 'https://trubnik.info'}]]
    msg = (f"🔓 **Профиль отвязан**\n——————————————\n"
           f"MAX ID: {user_id}\nПрофиль сайта: {site_name or '?'} (ID {site_id if site_id is not None else '?'})")
    notify_admins(msg, kb)


# ============================================
# ПОСТРОИТЕЛИ ЭКРАНОВ
# ============================================

def build_link_screen():
    return LINK_TEXT, create_link_keyboard()


def build_main_screen(user_id):
    user_data = get_linked_user(user_id)
    display_name = user_data['site_name'] if user_data and user_data['site_name'] else 'друг'
    text = f"👋 Рад вас снова видеть, {display_name}!\nВаш аккаунт связан с сайтом.\n\nВыберите действие:"
    return text, main_keyboard_for(user_id)


def build_settings_screen(user_id):
    settings = get_notification_settings(user_id)
    text = (
        "⚙️ **Настройки уведомлений**\n\n"
        "Нажмите на кнопку, чтобы включить или отключить уведомление.\n\n"
        "📊 — новые прогнозы на матчи\n"
        "💬 — сообщения в командном чате\n"
        "🏑 — напоминания о фэнтези (сборка/заявка команды)"
    )
    return text, create_settings_keyboard(settings)


def build_reminders_screen(user_id):
    settings = get_notification_settings(user_id)
    text = ("⏰ **Напоминания о матчах**\n\n"
            "Выберите, за сколько часов до начала матча получать напоминание.\n\n"
            "💡 Можно включить несколько вариантов одновременно!")
    return text, create_reminders_keyboard(settings)


def build_fantasy_reminders_screen(user_id):
    settings = get_notification_settings(user_id)
    text = ("🏑 **Напоминания о фэнтези**\n\n"
            "Выберите, за сколько часов до дедлайна получать напоминание "
            "о несобранной или незаявленной команде.\n\n"
            "💡 Можно включить несколько вариантов одновременно!")
    return text, create_fantasy_reminders_keyboard(settings)


def build_profile_screen(user_id):
    user_data = get_linked_user(user_id)
    settings = get_notification_settings(user_id)
    if user_data:
        text = (
            f"👤 **Ваш профиль**\n\n"
            f"🆔 MAX ID: {user_data['user_id']}\n"
            f"🌐 ID на сайте: {user_data['site_id']}\n"
            f"👤 Ник на сайте: {user_data['site_name']}\n"
            f"📅 Привязан: {user_data['linked_at']}\n\n"
        )
        text += "🔔 **Активные уведомления:**\n"
        notifs = []
        if settings['notify_forecast']: notifs.append("📊 Прогнозы")
        if settings['notify_chat']: notifs.append("💬 Сообщения в командном чате")
        if settings['notify_fantasy']: notifs.append("🏑 Фэнтези")
        text += "   ✅ " + ", ".join(notifs) + "\n" if notifs else "   ❌ Все уведомления отключены\n"

        if settings['notify_forecast']:
            text += "\n⏰ **Напоминания о матчах:**\n"
            reminders = [f"{h}ч" for h, key in [(1,'notify_1h'), (2,'notify_2h'), (5,'notify_5h'), (12,'notify_12h'), (24,'notify_24h')] if settings[key]]
            text += f"   ✅ За {', '.join(reminders)} до начала\n" if reminders else "   ❌ Отключены\n"

        if settings['notify_fantasy']:
            text += "\n🏑 **Напоминания о фэнтези (до дедлайна):**\n"
            fr = [f"{h}ч" for h, key in [(1,'notify_fantasy_1h'), (2,'notify_fantasy_2h'), (3,'notify_fantasy_3h'), (6,'notify_fantasy_6h'), (12,'notify_fantasy_12h'), (24,'notify_fantasy_24h')] if settings[key]]
            text += f"   ✅ За {', '.join(fr)}\n" if fr else "   ❌ Отключены\n"

        text += "\n⚠️ Если вы хотите отвязать аккаунт, нажмите кнопку ниже."
    else:
        text = "👤 Информация о профиле недоступна."
    return text, create_profile_keyboard()


# ⭐ АДМИН-ЭКРАНЫ

def build_status_screen():
    stats = bot_stats.get_stats()
    now = datetime.now(bot_stats.EKB_TZ)
    text = (
        f"📊 **Состояние бота**\n——————————————\n"
        f"Время: Екатеринбург (UTC+5), сейчас {now.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        f"Последняя проверка чата: {bot_stats.fmt_dt(stats['chat'])}\n"
        f"Последняя проверка прогнозов: {bot_stats.fmt_dt(stats['forecasts'])}\n"
        f"Последняя проверка фэнтези: {bot_stats.fmt_dt(stats['fantasy'])}\n"
    )
    err = stats['last_error']
    if err:
        dt, kind, err_text = err
        text += f"Последняя ошибка: {bot_stats.fmt_dt(dt)} | {KIND_RU.get(kind, kind)}: {err_text}\n"
    else:
        text += "Последняя ошибка: нет\n"
    text += (f"\nИнтервал опроса: чат каждые {CHAT_INTERVAL} с, "
             f"прогнозы каждые {FORECAST_INTERVAL} с, фэнтези каждые {FANTASY_INTERVAL} с.")
    return text, create_admin_back_keyboard()


def build_users_screen():
    count = get_linked_users_count()
    recent = get_recent_linked_users(5)
    text = f"👥 **Пользователи**\n——————————————\nПривязано профилей: {count}\n\n"
    if recent:
        text += "Последние привязанные профили:\n"
        for u in recent:
            text += f"• {u['site_name']} (ID сайта {u['site_id']}, MAX {u['user_id']})\n"
    else:
        text += "Пока никто не привязан."
    return text, create_admin_back_keyboard()


# ============================================
# ОТПРАВКА НОВЫХ ЭКРАНОВ / ОБНОВЛЕНИЕ НА МЕСТЕ
# ============================================

def show_link_screen(user_id):
    set_user_state(user_id, STATE_WAIT_CODE)
    text, kb = build_link_screen()
    send_message(user_id, text, kb)
    logger.info(f"[{user_id}] Показан экран привязки")


def show_main_screen(user_id):
    text, kb = build_main_screen(user_id)
    send_message(user_id, text, kb)


def update_screen_in_place(user_id, callback_id, text, keyboard):
    body = build_message_body(text, keyboard, notify=False)
    result = answer_callback(callback_id, message=body)
    if result is None:
        logger.warning(f"[{user_id}] Не удалось обновить сообщение на месте, отправляю новое")
        send_message(user_id, text, keyboard)
    else:
        logger.debug(f"[{user_id}] Экран обновлён на месте")


# ============================================
# ОБРАБОТКА НАЖАТИЙ КНОПОК
# ============================================

def handle_callback(user_id, payload, callback_id):
    logger.debug(f"[{user_id}] Callback: {payload}")

    if payload == 'back':
        if is_user_linked(user_id):
            set_user_state(user_id, STATE_LINKED)
            text, kb = build_main_screen(user_id)
        else:
            set_user_state(user_id, STATE_WAIT_CODE)
            text, kb = build_link_screen()

    elif payload == 'settings':
        set_user_state(user_id, STATE_SETTINGS)
        text, kb = build_settings_screen(user_id)

    elif payload == 'profile':
        text, kb = build_profile_screen(user_id)

    elif payload.startswith('toggle:'):
        setting_name = payload.split(':', 1)[1]
        toggle_notification_setting(user_id, setting_name)
        state = get_user_state(user_id)
        if state == STATE_SETTINGS_REMINDERS:
            text, kb = build_reminders_screen(user_id)
        elif state == STATE_SETTINGS_FANTASY:
            text, kb = build_fantasy_reminders_screen(user_id)
        else:
            text, kb = build_settings_screen(user_id)

    elif payload == 'reminders':
        if get_notification_settings(user_id)['notify_forecast']:
            set_user_state(user_id, STATE_SETTINGS_REMINDERS)
            text, kb = build_reminders_screen(user_id)
        else:
            text = "⚠️ Сначала включите уведомления о прогнозах."
            kb = create_settings_keyboard(get_notification_settings(user_id))

    elif payload == 'fantasy_reminders':
        if get_notification_settings(user_id)['notify_fantasy']:
            set_user_state(user_id, STATE_SETTINGS_FANTASY)
            text, kb = build_fantasy_reminders_screen(user_id)
        else:
            text = "⚠️ Сначала включите уведомления о фэнтези."
            kb = create_settings_keyboard(get_notification_settings(user_id))

    elif payload == 'unlink':
        set_user_state(user_id, STATE_UNLINK_CONFIRM)
        text, kb = UNLINK_CONFIRM_TEXT, create_unlink_confirm_keyboard()

    elif payload == 'unlink_confirm_yes':
        user_data = get_linked_user(user_id)  # ⭐ запоминаем ДО удаления
        delete_user_data(user_id)
        success, msg, affected = unlink_account_on_site('max', user_id)
        if success:
            logger.info(f"[{user_id}] Сайт очистил max_id (затронуто строк: {affected})")
        else:
            logger.warning(f"[{user_id}] Сайт вернул ошибку при отвязке: {msg}")
        logger.warning(f"[{user_id}] ПОЛЬЗОВАТЕЛЬ ОТВЯЗАЛ АККАУНТ (MAX)")
        notify_admins_unlink(user_id,
                             user_data['site_id'] if user_data else None,
                             user_data['site_name'] if user_data else None)  # ⭐ админам
        set_user_state(user_id, STATE_WAIT_CODE)
        link_text, link_kb = build_link_screen()
        text = "✅ Ваш аккаунт успешно отвязан. Все данные удалены.\n\n" + link_text
        kb = link_kb

    # ⭐ АДМИН-КНОПКИ
    elif payload == 'status':
        if not is_admin(user_id):
            answer_callback(callback_id, notification='⛔ Раздел доступен только администраторам')
            return
        text, kb = build_status_screen()
        logger.info(f"[{user_id}] Админ открыл Статус")

    elif payload == 'users':
        if not is_admin(user_id):
            answer_callback(callback_id, notification='⛔ Раздел доступен только администраторам')
            return
        text, kb = build_users_screen()
        logger.info(f"[{user_id}] Админ открыл Пользователи")

    else:
        answer_callback(callback_id)
        logger.warning(f"[{user_id}] Неизвестный callback: {payload}")
        return

    update_screen_in_place(user_id, callback_id, text, kb)


# ============================================
# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
# ============================================

def handle_message(user_id, text, sender=None):
    text = (text or '').strip()
    text_lower = text.lower()
    state = get_user_state(user_id)

    logger.debug(f"[{user_id}] Сообщение: '{text}', состояние: {state}")

    if text_lower in ['/start', 'меню', 'старт', 'в меню', 'начало', 'привет']:
        if is_user_linked(user_id):
            set_user_state(user_id, STATE_LINKED)
            show_main_screen(user_id)
        else:
            show_link_screen(user_id)
        return

    if state == STATE_WAIT_CODE:
        send_message(user_id, "⏳ Проверяю код и связываю аккаунты...")

        user_name = 'пользователь'
        if sender:
            user_name = ((sender.get('first_name') or '') + ' ' + (sender.get('last_name') or '')).strip() or 'пользователь'

        success, msg, site_id, site_name = link_account_on_site('max', user_id, text)

        if success and site_id:
            if save_linked_user(user_id, site_id, user_name, site_name, text):
                set_user_state(user_id, STATE_LINKED)
                logger.info(f"[{user_id}] 🎉 УСПЕШНАЯ ПРИВЯЗКА: site_id={site_id}")
                notify_admins_link(user_id, site_id, site_name)  # ⭐ админам
                send_message(
                    user_id,
                    f"🎉 Готово, {site_name}!\n\nВаш аккаунт успешно связан с сайтом.\n🆔 Ваш ID на сайте: {site_id}\n\nТеперь вам доступны персональные уведомления!",
                    main_keyboard_for(user_id)
                )
            else:
                send_message(user_id, "❌ Не удалось сохранить данные.", create_link_keyboard())
        else:
            send_message(user_id, f"❌ Не удалось связать аккаунты. {msg}", create_link_keyboard())
        return

    if is_user_linked(user_id):
        show_main_screen(user_id)
    else:
        show_link_screen(user_id)


# ============================================
# РАЗБОР СОБЫТИЙ И POLLING
# ============================================

def process_update(update):
    utype = update.get('update_type')

    if utype == 'bot_started':
        user = update.get('user', {})
        user_id = user.get('user_id')
        if not user_id:
            return
        logger.info(f"[{user_id}] bot_started")
        if is_user_linked(user_id):
            set_user_state(user_id, STATE_LINKED)
            show_main_screen(user_id)
        else:
            show_link_screen(user_id)
        return

    if utype == 'message_created':
        message = update.get('message', {})
        sender = message.get('sender', {})
        recipient = message.get('recipient', {})
        if sender.get('is_bot'):
            return
        if recipient.get('chat_type') not in (None, 'dialog'):
            return
        user_id = sender.get('user_id')
        text = (message.get('body') or {}).get('text', '')
        if user_id and text:
            handle_message(user_id, text, sender)
        return

    if utype == 'message_callback':
        callback = update.get('callback', {})
        user_id = (callback.get('user') or {}).get('user_id')
        payload = callback.get('payload', '')
        callback_id = callback.get('callback_id')
        if user_id and payload and callback_id:
            handle_callback(user_id, payload, callback_id)
        return

    logger.debug(f"Событие пропущено: {utype}")


def poll_updates():
    marker = None
    logger.info("⏳ Ожидание событий от MAX (Long Polling)...")
    while True:
        try:
            updates, new_marker = get_updates(marker=marker, timeout=30)
            if updates is None:
                time.sleep(5)
                continue
            for update in updates:
                try:
                    process_update(update)
                except Exception as e:
                    logger.error(f"Ошибка обработки события: {e}", exc_info=True)
            if new_marker is not None:
                marker = new_marker
        except Exception as e:
            logger.error(f"Ошибка в polling: {e}", exc_info=True)
            time.sleep(5)


def main():
    logger.info("=" * 50)
    logger.info("🤖 MAX-бот ХК Трубник запускается...")
    logger.info(f"👑 Админы: {ADMIN_IDS}")
    logger.info("=" * 50)

    me = get_me()
    if me:
        logger.info(f"✅ MAX API: токен действителен, бот «{me.get('name', '?')}» (id={me.get('user_id')})")
    else:
        logger.warning("⚠️ Не удалось проверить токен через GET /me")

    init_db()
    start_scheduler()
    poll_updates()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 MAX-бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка MAX-бота: {e}", exc_info=True)