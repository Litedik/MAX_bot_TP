# scheduler.py - Планировщик MAX с раздельными интервалами

import threading
import time
from database import (
    get_all_linked_users, get_notification_settings,
    is_notification_sent, mark_notification_sent, cleanup_old_history
)
from site_api import get_forecasts, get_chat_messages, get_fantasy_teams
from max_api import send_message, rate_limit_pause
from config import CHAT_INTERVAL, FORECAST_INTERVAL, FANTASY_INTERVAL
from logger import logger


def check_forecasts(users, forecast_data):
    if not forecast_data or 'data' not in forecast_data:
        return
    site_to_user = {int(u['site_id']): u['user_id'] for u in users if u['site_id']}

    for tournament in forecast_data['data']:
        tournament_id = tournament.get('tournament_id')
        tournament_name = tournament.get('tournament_name', 'Неизвестный турнир')
        tournament_link = tournament.get('tournament_link') or f'https://trubnik.info/aforecasts/{tournament_id}'
        users_missing = {}

        for match in tournament.get('matches', []):
            seconds_until = match.get('seconds_until_match', 0)
            not_forecasted = match.get('not_forecasted', [])
            if seconds_until > 0 and not_forecasted:
                is_urgent = seconds_until < 3600
                for site_user_id in not_forecasted:
                    site_user_id = int(site_user_id)
                    if site_user_id not in users_missing:
                        users_missing[site_user_id] = {'matches': [], 'match_ids': [], 'is_urgent': False}
                    users_missing[site_user_id]['matches'].append(match.get('match_name', 'Матч'))
                    users_missing[site_user_id]['match_ids'].append(int(match.get('match_id', 0)))
                    if is_urgent:
                        users_missing[site_user_id]['is_urgent'] = True

        for site_user_id, data in users_missing.items():
            if site_user_id not in site_to_user:
                continue
            user_id = site_to_user[site_user_id]
            if not get_notification_settings(user_id)['notify_forecast']:
                continue
            sorted_ids = sorted(data['match_ids'])
            event_id = f"forecast_tourn_{tournament_id}_{'_'.join(map(str, sorted_ids))}"
            if is_notification_sent(user_id, 'forecast_reminder', event_id):
                continue
            urgency = "🔥 **СРОЧНО:** " if data['is_urgent'] else ""
            matches_list = "\n".join([f"🆚 {m}" for m in data['matches']])
            msg = (f"{urgency}📊 **Вы не проставили прогнозы!**\n\n🏆 {tournament_name}\n\n"
                   f"Матчи без прогноза:\n{matches_list}\n\n🔗 Страница тура: {tournament_link}\n\n"
                   f"Пожалуйста, сделайте свой выбор до начала игр.")
            keyboard = [
                [{'type': 'link', 'text': '🔗 Перейти к прогнозам', 'url': tournament_link}],
                [{'type': 'callback', 'text': '🔙 В главное меню', 'payload': 'back'}]
            ]
            send_message(user_id, msg, keyboard)
            mark_notification_sent(user_id, 'forecast_reminder', event_id)
            logger.info(f"[{user_id}] Напоминание по турниру {tournament_id} ({len(data['matches'])} матчей)")
            rate_limit_pause()


def check_chat_messages(users, chat_data):
    site_to_user = {int(u['site_id']): u['user_id'] for u in users if u['site_id']}
    for team in chat_data:
        team_id = team.get('team_id')
        team_name = team.get('team_name', 'Неизвестная команда')
        last_msg_id = team.get('last_message_id')
        unread_by = team.get('unread_by', [])
        if not last_msg_id or not unread_by:
            continue
        event_id = f"chat_unread_{team_id}_{last_msg_id}"
        for site_user_id in unread_by:
            site_user_id = int(site_user_id)
            if site_user_id not in site_to_user:
                continue
            user_id = site_to_user[site_user_id]
            if not get_notification_settings(user_id)['notify_chat']:
                continue
            if is_notification_sent(user_id, 'chat_unread', event_id):
                continue
            msg = (f"💬 В командном чате вашей команды **\"{team_name}\"** появилось новое сообщение!\n\n"
                   f"🔗 Перейти в чат: https://trubnik.info/forecasts/teamspeek")
            send_message(user_id, msg)
            mark_notification_sent(user_id, 'chat_unread', event_id)
            logger.info(f"[{user_id}] Уведомление о чате команды {team_name}")
            rate_limit_pause()


def check_fantasy(users, fantasy_data):
    if not fantasy_data or 'data' not in fantasy_data or fantasy_data['data'] is None:
        return
    data = fantasy_data['data']
    tournament_id = data.get('tournament_id')
    tournament_name = data.get('tournament_name', 'Фэнтези')
    day_num = data.get('day_num')
    day_deadline = data.get('day_deadline', '')
    seconds_until = data.get('seconds_until_deadline', 0)

    intervals = [(1, 'notify_fantasy_1h'), (2, 'notify_fantasy_2h'), (3, 'notify_fantasy_3h'),
                 (6, 'notify_fantasy_6h'), (12, 'notify_fantasy_12h'), (24, 'notify_fantasy_24h')]
    site_to_user = {int(u['site_id']): u['user_id'] for u in users if u['site_id']}

    def process_list(user_list, msg_type, action_text):
        for site_user_id in user_list:
            site_user_id = int(site_user_id)
            if site_user_id not in site_to_user:
                continue
            user_id = site_to_user[site_user_id]
            settings = get_notification_settings(user_id)
            if not settings.get('notify_fantasy', True):
                continue
            for hours, setting_name in intervals:
                if not settings.get(setting_name, True):
                    continue
                if abs(seconds_until - hours * 3600) > 330:
                    continue
                event_id = f"fantasy_{tournament_id}_{day_num}_{msg_type}_{hours}h"
                if is_notification_sent(user_id, 'fantasy_reminder', event_id):
                    continue
                if seconds_until <= 3600:
                    urgency = "🔥 **СРОЧНО:** "
                elif seconds_until <= 21600:
                    urgency = "⚠️ **СКОРО:** "
                else:
                    urgency = "🔔 **НАПОМИНАНИЕ:** "
                msg = (f"{urgency}Тур {day_num} «{tournament_name}»\n\n{action_text}\n"
                       f"⏰ Дедлайн: {day_deadline} (МСК)\n\n"
                       f"🔗 Управление командой: https://trubnik.info/fantasy")
                keyboard = [
                    [{'type': 'link', 'text': '🔗 Перейти в фэнтези', 'url': 'https://trubnik.info/fantasy'}],
                    [{'type': 'callback', 'text': '🔙 В главное меню', 'payload': 'back'}]
                ]
                send_message(user_id, msg, keyboard)
                mark_notification_sent(user_id, 'fantasy_reminder', event_id)
                logger.info(f"[{user_id}] Фэнтези-уведомление ({msg_type}, за {hours}ч), тур {day_num}")
                rate_limit_pause()

    if data.get('not_submitted'):
        process_list(data['not_submitted'], 'not_submitted', "Ваша команда собрана, но не заявлена!")
    if data.get('not_assembled'):
        process_list(data['not_assembled'], 'not_assembled', "Вы ещё не собрали команду на этот тур!")


def scheduler_loop():
    logger.info(f"📅 Планировщик MAX запущен (чат: {CHAT_INTERVAL}с, прогнозы: {FORECAST_INTERVAL}с, фэнтези: {FANTASY_INTERVAL}с)")
    last_run = {'chat': 0.0, 'forecasts': 0.0, 'fantasy': 0.0}
    last_cleanup = time.time()

    while True:
        try:
            users = get_all_linked_users()
            if users:
                now = time.time()
                if now - last_run['chat'] >= CHAT_INTERVAL:
                    check_chat_messages(users, get_chat_messages())
                    last_run['chat'] = now
                if now - last_run['forecasts'] >= FORECAST_INTERVAL:
                    check_forecasts(users, get_forecasts())
                    last_run['forecasts'] = now
                if now - last_run['fantasy'] >= FANTASY_INTERVAL:
                    check_fantasy(users, get_fantasy_teams())
                    last_run['fantasy'] = now
                if now - last_cleanup >= 86400:
                    cleanup_old_history(days=30)
                    last_cleanup = now
        except Exception as e:
            logger.error(f"Ошибка в планировщике MAX: {e}", exc_info=True)
        time.sleep(30)


def start_scheduler():
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    logger.info("✅ Фоновый планировщик MAX запущен")