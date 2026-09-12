#!/usr/bin/env python3
"""Телеграм-бот проверки компании в нейровыдаче.

Менеджер присылает ИНН — бот отвечает картинкой и короткой выжимкой.

Запуск:  python bot.py
Остановка: Ctrl+C.

Бот работает опросом: сам спрашивает у телеграма новые сообщения.
Это значит, что ему не нужен ни белый адрес, ни сертификат — он
запускается на любом компьютере, где есть интернет. Пока программа
закрыта, бот не отвечает.
"""

import configparser
import os
import sys
import threading
import time
import traceback

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nejroanaliz import run as runner  # noqa: E402

API = 'https://api.telegram.org/bot%s/%s'


def load_config(path='config.ini'):
    if not os.path.exists(path):
        print('Нет файла %s. Скопируйте config.example.ini в config.ini '
              'и впишите свои ключи.' % path)
        sys.exit(1)

    p = configparser.ConfigParser()
    p.read(path, encoding='utf-8')
    s = p['keys'] if 'keys' in p else p['DEFAULT']

    cfg = {k: s.get(k, '').strip() for k in s.keys()}
    cfg['gigachat_verify'] = s.get('gigachat_verify', 'yes').strip().lower() not in ('no', 'нет', '0', 'false')

    missing = [k for k in ('telegram_token', 'dadata_token') if not cfg.get(k)]
    if missing:
        print('В config.ini не заполнено: %s' % ', '.join(missing))
        sys.exit(1)
    return cfg


def api(cfg, method, **params):
    r = requests.post(API % (cfg['telegram_token'], method), data=params, timeout=60)
    return r.json()


def send(cfg, chat_id, text):
    return api(cfg, 'sendMessage', chat_id=chat_id, text=text, disable_web_page_preview=True)


def send_photo(cfg, chat_id, path, caption):
    with open(path, 'rb') as f:
        r = requests.post(API % (cfg['telegram_token'], 'sendPhoto'),
                          data={'chat_id': chat_id, 'caption': caption[:1024]},
                          files={'photo': f}, timeout=180)
    return r.json()


def allowed(cfg, chat_id):
    """Кому разрешено пользоваться. Если список пуст — разрешено всем,
    кто найдёт бота. Лучше вписать свои номера: проверка стоит денег."""
    raw = (cfg.get('allowed_chats') or '').replace(' ', '')
    if not raw:
        return True
    return str(chat_id) in raw.split(',')


HELP = (
    'Пришлите ИНН компании — проверю, называют ли её нейросети '
    'и на каком месте она в поиске Яндекса.\n\n'
    '10 цифр у компании, 12 у предпринимателя. '
    'Проверка занимает одну-две минуты.'
)


def handle(cfg, chat_id, text):
    text = (text or '').strip()

    if text in ('/start', '/help', 'помощь'):
        send(cfg, chat_id, HELP)
        return

    if not any(ch.isdigit() for ch in text):
        send(cfg, chat_id, HELP)
        return

    def progress(msg):
        send(cfg, chat_id, msg)

    try:
        data = runner.analyze(text, cfg, progress=progress)
        send_photo(cfg, chat_id, data['png'], runner.as_text(data))
    except runner.RunError as e:
        send(cfg, chat_id, str(e))
    except Exception as e:
        traceback.print_exc()
        send(cfg, chat_id, 'Не получилось: %s' % e)


def main():
    cfg = load_config()
    print('Бот запущен. Остановить — Ctrl+C.')

    offset = 0
    while True:
        try:
            r = requests.get(API % (cfg['telegram_token'], 'getUpdates'),
                             params={'offset': offset, 'timeout': 30}, timeout=60).json()
        except Exception as e:
            print('Телеграм недоступен: %s' % e)
            time.sleep(5)
            continue

        if not r.get('ok'):
            print('Телеграм ответил отказом: %s' % r)
            time.sleep(5)
            continue

        for upd in r.get('result', []):
            offset = upd['update_id'] + 1
            msg = upd.get('message') or upd.get('channel_post')
            if not msg:
                continue
            chat_id = msg['chat']['id']

            if not allowed(cfg, chat_id):
                send(cfg, chat_id, 'Этот бот не для общего пользования.')
                print('Отказано чату %s' % chat_id)
                continue

            print('Запрос от %s: %s' % (chat_id, (msg.get('text') or '')[:40]))
            # Каждая проверка в своём потоке: пока идёт одна, бот
            # отвечает остальным, а не копит очередь молча.
            threading.Thread(target=handle, args=(cfg, chat_id, msg.get('text')),
                             daemon=True).start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nОстановлено.')
