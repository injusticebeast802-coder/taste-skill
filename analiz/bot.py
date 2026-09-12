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

# Вывод в utf-8: на Windows консоль по умолчанию в cp866, и русские
# сообщения превращались бы в мусор или роняли программу.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nejroanaliz import run as runner  # noqa: E402

API = 'https://api.telegram.org/bot%s/%s'


# Проводник Windows по умолчанию прячет расширения, и копия
# config.example.ini, переименованная в «config.ini», на самом деле
# получает имя config.ini.ini. Человек видит правильное имя, а файла
# с таким именем на диске нет. Поэтому ищем и такие варианты — и
# говорим, как назвать файл по-человечески.
CONFIG_NAMES = ('config.ini', 'config.ini.ini', 'config.ini.txt',
                'config.txt', 'config.example.ini.ini')


def find_config(folder='.'):
    for name in CONFIG_NAMES:
        full = os.path.join(folder, name)
        if os.path.exists(full):
            return full, name
    return '', ''


def load_config(path=''):
    folder = os.path.dirname(os.path.abspath(__file__))

    if not path:
        path, name = find_config(folder)
        if not path:
            print('Не нашёл файл настроек в папке:')
            print('  %s' % folder)
            print('')
            print('Скопируйте config.example.ini, назовите копию config.ini')
            print('и впишите в неё ключи.')
            # Код 2 — «неправильно настроено». Окно запуска по нему
            # понимает, что перезапускать бесполезно: без ключей он
            # упадёт точно так же и через десять секунд, и через час.
            sys.exit(2)
        if name != 'config.ini':
            print('Файл настроек называется «%s», а должен «config.ini».' % name)
            print('Читаю его как есть, но лучше переименовать.')
            print('')
            print('Чтобы имена файлов было видно целиком: в проводнике')
            print('вкладка «Вид» -> галочка «Расширения имён файлов».')
            print('')

    p = configparser.ConfigParser()
    p.read(path, encoding='utf-8')
    s = p['keys'] if 'keys' in p else p['DEFAULT']

    cfg = {k: s.get(k, '').strip() for k in s.keys()}
    cfg['gigachat_verify'] = s.get('gigachat_verify', 'yes').strip().lower() not in ('no', 'нет', '0', 'false')

    # Многоточие — это то, что стоит в образце. Значит, строку не
    # заполнили, а не забыли: так и скажем.
    for k, v in list(cfg.items()):
        if isinstance(v, str) and set(v.strip()) == {'.'}:
            cfg[k] = ''

    # Токен нужен только при прямом обращении: если ходим через
    # посредника на хостинге, токен лежит там, а не здесь.
    nuzhno = ['dadata_token'] if cfg.get('telegram_api') else ['telegram_token', 'dadata_token']
    missing = [k for k in nuzhno if not cfg.get(k)]
    if missing:
        print('В файле настроек не заполнено: %s' % ', '.join(missing))
        sys.exit(2)

    cfg['out_dir'] = cfg.get('out_dir') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'otchety')
    return cfg


def api(cfg, method, **params):
    r = requests.post(tg_url(cfg, method), data=params,
                      proxies=tg_proxy(cfg), timeout=60)
    return r.json()


def tg_url(cfg, method):
    """Адрес, по которому обращаемся к телеграму.

    Обычно это api.telegram.org. Если он с этого компьютера закрыт,
    в config.ini вписывают telegram_api — адрес файла tg.php на нашем
    же хостинге. Хостинг до телеграма достаёт (заявки с форм туда
    уходят), и получается: программа -> свой сайт -> телеграм. Токен
    при этом лежит на хостинге, на компьютер менеджера не попадает.
    """
    relay = (cfg.get('telegram_api') or '').strip()
    if relay:
        return '%s%sm=%s' % (relay, '&' if '?' in relay else '?', method)
    return API % (cfg['telegram_token'], method)


def tg_proxy(cfg):
    """Прокси для телеграма — и только для него.

    api.telegram.org у российских провайдеров закрыт, и программа
    висит на таймауте подключения. Яндекс, GigaChat и DaData при этом
    открыты и работают напрямую, поэтому гнать их через тот же прокси
    нельзя: будет медленнее, а Яндекс ещё и отвечает отказом на запрос
    из-за границы. Так что подменяем адрес ровно у трёх вызовов.
    """
    url = (cfg.get('telegram_proxy') or '').strip()
    if not url:
        return None
    return {'http': url, 'https': url}


def send(cfg, chat_id, text):
    return api(cfg, 'sendMessage', chat_id=chat_id, text=text, disable_web_page_preview=True)


def send_photo(cfg, chat_id, path, caption):
    with open(path, 'rb') as f:
        r = requests.post(tg_url(cfg, 'sendPhoto'),
                          data={'chat_id': chat_id, 'caption': caption[:1024]},
                          files={'photo': f}, proxies=tg_proxy(cfg), timeout=180)
    return r.json()


def allowed(cfg, chat_id):
    """Кому разрешено пользоваться. Если список пуст — разрешено всем,
    кто найдёт бота. Лучше вписать свои номера: проверка стоит денег."""
    raw = (cfg.get('allowed_chats') or '').replace(' ', '')
    if not raw:
        return True
    return str(chat_id) in raw.split(',')


HELP = (
    'Проверяю, называют ли компанию нейросети и на каком месте она '
    'в поиске Яндекса.\n\n'
    'Лучше всего — ИНН и то, что клиент написал в заявке:\n'
    '9702020445 Flowwow, доставка цветов\n\n'
    'Можно короче, одним ИНН — тогда название и род занятий возьму '
    'из реестра:\n'
    '9702020445\n\n'
    'Можно и без ИНН, прямо из заявки — тогда через запятую нужны '
    'название, род занятий и город:\n'
    'Flowwow, доставка цветов, Москва\n\n'
    'Название пишите так, как компания сама себя называет, а не как '
    'в реестре: нейросети знают Flowwow, а не «ООО ФЛАУВАУ».\n\n'
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
        # Две картинки: одна и та же проверка в оформлении двух наших
        # сайтов. Менеджер пересылает клиенту ту, на сайте которого
        # тот оставил заявку.
        pngs = data.get('pngs') or {'genii': data['png']}
        send_photo(cfg, chat_id, pngs['genii'],
                   runner.as_text(data) + '\n\n↑ для заявки с genii-ai.ru')
        if pngs.get('prompter'):
            send_photo(cfg, chat_id, pngs['prompter'],
                       'То же самое для заявки с prompter-ai.moscow')
    except runner.RunError as e:
        send(cfg, chat_id, str(e))
    except Exception as e:
        traceback.print_exc()
        send(cfg, chat_id, 'Не получилось: %s' % e)


def main():
    cfg = load_config()
    print('Бот запущен. Остановить — Ctrl+C.')

    offset = 0
    beda = 0          # сколько раз подряд не достучались до телеграма

    # Сколько секунд держать линию в ожидании сообщения. Напрямую
    # телеграм спокойно держит полминуты. Через посредника на хостинге
    # столько нельзя: у PHP там свой предел на время работы, и запрос
    # оборвался бы на середине.
    dozhidanie = 20 if (cfg.get('telegram_api') or '').strip() else 30
    while True:
        try:
            r = requests.get(tg_url(cfg, 'getUpdates'),
                             params={'offset': offset, 'timeout': dozhidanie},
                             proxies=tg_proxy(cfg), timeout=dozhidanie + 30).json()
        except Exception as e:
            # Печатаем по-человечески и один раз. Раньше сюда каждые
            # пять секунд валилась строка urllib3 на три строки, и в
            # окне было не видно ничего, кроме неё.
            beda += 1
            if beda == 1:
                print('')
                print('Телеграм не отвечает.')
                if 'imeout' in str(e) or 'onnect' in str(e):
                    print('Обычно это блокировка у провайдера: сайт и заявки')
                    print('работают, а api.telegram.org с этого компьютера нет.')
                    print('')
                    print('Что делать — одно из двух:')
                    print('  1. Ходить в телеграм через свой сайт: строка')
                    print('     telegram_api в config.ini. Пример в')
                    print('     config.example.ini, файл tg.php уже на хостинге.')
                    print('  2. Включить VPN на этом компьютере. MTProto-прокси')
                    print('     (TG WS Proxy и такие же) не подойдёт: он возит')
                    print('     не то, чем ходит бот.')
                print('')
                print('Полный текст ошибки: %s' % e)
                print('Продолжаю пробовать, каждые 15 секунд…')
            elif beda % 20 == 0:
                print('Всё ещё нет связи с телеграмом (попыток: %d).' % beda)
            time.sleep(15)
            continue

        if not r.get('ok'):
            print('Телеграм ответил отказом: %s' % r)
            time.sleep(5)
            continue

        if beda:
            print('Связь с телеграмом восстановлена.')
            beda = 0

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
