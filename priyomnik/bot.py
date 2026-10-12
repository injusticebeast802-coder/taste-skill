#!/usr/bin/env python3
"""Бот-приёмщик заявок на бесплатный разбор.

Зачем он нужен. Разбор мы отдаём только подписчикам канала, а
проверить подписку руками нельзя: списка подписчиков у менеджеров нет
и прав смотреть его тоже. Телеграм умеет ответить на вопрос «состоит
ли вот этот человек в канале», но только боту и только если бот —
администратор канала. Поэтому права нужны один раз боту, а не каждому
менеджеру.

Что делает. Человек приходит с сайта, бот проверяет подписку, задаёт
шесть вопросов и отправляет готовую карточку в рабочий чат. Разбор
по-прежнему считает менеджер своей программой: этот бот ничего не
анализирует и ключей от нейросетей не знает.

Запуск:  python bot.py
Остановка: Ctrl+C.

Бот работает опросом: сам спрашивает у телеграма новые сообщения. Ему
не нужен ни белый адрес, ни сертификат — он запускается на любом
компьютере и на хостинге.
"""

import base64
import configparser
import hashlib
import hmac
import html
import json
import os
import sys
import time
import traceback

import requests

import inn as inn_proverka

# Одно соединение на всю работу вместо нового на каждый запрос.
# Рукопожатие TLS с телеграмом занимает заметно больше, чем сам
# запрос, а бот делает их десятками.
SVYAZ = requests.Session()

# Сколько ждём соединения с телеграмом и сколько — ответа.
#
# Минута на соединение выглядит нелепо: телеграм отвечает за доли
# секунды. Но до него тут не доходит прямая дорога, и рукопожатие
# занимает десятки секунд — медленно, зато работает. Однажды я решил,
# что десяти секунд хватит всякому, и отрезал этим единственный
# рабочий путь: бот замолчал совсем. Больше так не делаем.
#
# Платим мы за это один раз: соединение держится открытым (SVYAZ
# выше), и дальше запросы идут по нему уже без рукопожатия.
ZHDAT_SVYAZ = 60
ZHDAT_OTVET = 60

# Запрос дольше этого времени печатаем в журнал. Иначе «бот тормозит»
# остаётся ощущением, а не цифрой, по которой можно что-то сделать.
DOLGO = 3.0

# Вывод в utf-8: на Windows консоль по умолчанию в cp866, и русские
# сообщения превращались бы в мусор.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TUT = os.path.dirname(os.path.abspath(__file__))
API = 'https://api.telegram.org/bot%s/%s'
ANKETY = os.path.join(TUT, 'anketa.json')

# Сколько ждать ответа телеграма при длинном опросе. Меньше — больше
# пустых запросов, больше — дольше реакция на остановку с клавиатуры.
ZHDAT = 25

# Незаконченная анкета живёт сутки. Человек отвлёкся и вернулся на
# другой день — продолжать с «вопроса четыре» бессмысленно, он уже не
# помнит, о чём речь.
ZHIVET = 24 * 60 * 60


# ------------------------------------------------------------ настройки

def ochistit(tekst):
    """Готовит содержимое config.ini к разбору.

    Файл правят руками в nano прямо на хостинге, и он оттуда выходит
    побитым: длинный комментарий переносится на вторую строку уже без
    точки с запятой, в файл случайно попадает команда запуска из
    буфера. Для разборщика настроек это мусор, и бот падал с
    непонятной ошибкой про отсутствие заголовка секции.

    Поэтому выкидываем всё до первой строки в квадратных скобках и
    всё, в чём нет знака равенства. Настройки от этого не страдают:
    в них всегда есть «=», а пояснения всё равно лежат в
    config.example.ini и в README.
    """
    stroki = tekst.splitlines()
    nachalo = next((i for i, s in enumerate(stroki)
                    if s.strip().startswith('[')), None)
    if nachalo is None:
        return tekst
    godnye = [stroki[nachalo]]
    for s in stroki[nachalo + 1:]:
        golo = s.strip()
        if not golo or golo.startswith((';', '#')) or golo.startswith('[') or '=' in golo:
            godnye.append(s)
    return '\n'.join(godnye) + '\n'


def nastrojki():
    put = os.path.join(TUT, 'config.ini')
    if not os.path.exists(put):
        print('Нет файла config.ini рядом с ботом.')
        print('Скопируйте config.example.ini в config.ini и впишите токен.')
        sys.exit(1)

    razbor = configparser.ConfigParser()
    razbor.read_string(ochistit(open(put, encoding='utf-8').read()))
    cfg = dict(razbor['keys']) if razbor.has_section('keys') else {}

    cherez_sajt = bool((cfg.get('telegram_api') or '').strip())
    nuzhno = ['kanal', 'chat_zayavok'] + ([] if cherez_sajt else ['telegram_token'])
    net = [k for k in nuzhno if not (cfg.get(k) or '').strip()]
    if net:
        print('В config.ini не заполнено: %s' % ', '.join(net))
        sys.exit(1)

    if not (cfg.get('sajt_anketa') or '').strip():
        cfg['sajt_anketa'] = 'https://genii-ai.ru/analiz'

    kanal = cfg['kanal'].strip()
    if not kanal.startswith('@') and not kanal.lstrip('-').isdigit():
        kanal = '@' + kanal
    cfg['kanal'] = kanal
    if not (cfg.get('kanal_ssylka') or '').strip():
        cfg['kanal_ssylka'] = 'https://t.me/' + kanal.lstrip('@')
    return cfg


def tg_url(cfg, metod):
    """Адрес, по которому обращаемся к телеграму.

    Обычно это api.telegram.org. Если он с этой машины закрыт — а у
    российских провайдеров он закрыт, — в config.ini вписывают
    telegram_api: адрес посредника, файла tg.php на нашем хостинге или
    работника Cloudflare. Туда ход есть, а оттуда есть ход в телеграм.

    Посредник один на двух ботов: отчёты шлёт один, заявки принимает
    другой, токены у них разные. Чей токен подставить, говорит
    b=priyom — без него посредник возьмёт токен бота отчётов, и
    человек получит ответ не от того бота, в котором спрашивал.
    """
    relay = (cfg.get('telegram_api') or '').strip()
    if relay:
        return '%s%sm=%s&b=priyom' % (relay, '&' if '?' in relay else '?', metod)
    return API % (cfg['telegram_token'], metod)


def tg_proxy(cfg):
    url = (cfg.get('telegram_proxy') or '').strip()
    return {'http': url, 'https': url} if url else None


def api(cfg, metod, popytok=3, **params):
    """Один вызов телеграма. Сетевые сбои здесь обычны, поэтому ошибку
    не роняем наружу: бот должен пережить обрыв связи, а не упасть.

    Число попыток разное не от настроения: потерять сообщение человеку
    нельзя, а снять кружок ожидания с нажатой кнопки — мелочь, ради
    которой человек не должен ждать. Поэтому у мелочей попытка одна.
    """
    for popytka in range(1, popytok + 1):
        nachalo = time.time()
        try:
            r = SVYAZ.post(tg_url(cfg, metod), data=params,
                           proxies=tg_proxy(cfg),
                           timeout=(ZHDAT_SVYAZ, ZHDAT_OTVET))
            proshlo = time.time() - nachalo
            if proshlo > DOLGO:
                print('долгий ответ телеграма: %s — %.1f с' % (metod, proshlo))
            return r.json()
        except requests.exceptions.RequestException as e:
            if popytka == popytok:
                print('Телеграм не ответил (%s): %s' % (metod, e))
                return {'ok': False, 'description': str(e)}
            time.sleep(1)


# ------------------------------------------------------------ подписка

def podpisan(cfg, user_id):
    """Состоит ли человек в канале.

    Возвращает True, False или None, если проверить не удалось: бота
    забыли сделать администратором, канал переименовали, телеграм не
    ответил. Три разных случая, и путать их нельзя — отказать человеку
    из-за своей же ошибки настройки хуже, чем пропустить лишнего.
    """
    r = api(cfg, 'getChatMember', chat_id=cfg['kanal'], user_id=user_id)
    if not r.get('ok'):
        print('Не смог проверить подписку: %s' % r.get('description'))
        return None

    status = (r.get('result') or {}).get('status')
    if status in ('creator', 'administrator', 'member'):
        return True
    # «restricted» — человек в канале, но ограничен в правах. Для нас
    # он подписчик, если не вышел.
    if status == 'restricted':
        return bool(r['result'].get('is_member'))
    return False


# --------------------------------------------------- ссылка на анкету

# Сколько живёт ссылка. Сутки — чтобы человек успел вернуться вечером,
# но подписка при этом оставалась свежей: отписался и пришёл через
# неделю по старой ссылке — так не пойдёт.
KLYUCH_ZHIVET = 24 * 3600


def klyuch_dlya(cfg, user_id):
    """Подписанный ключ: сайт по нему узнаёт, что подписка проверена.

    Общей базы у бота и сайта нет и не нужно. Ключ подписан секретом,
    который лежит в двух местах — в config.ini бота и в config.php
    сайта. Сайт проверяет подпись арифметикой, а не запросом к боту:
    подделать её, не зная секрета, нельзя, а бот при этом может лежать.
    """
    sekret = (cfg.get('sekret_ssylki') or '').strip()
    if not sekret:
        return ''
    telo = '%d.%d' % (user_id, int(time.time()) + KLYUCH_ZHIVET)
    syroe = hmac.new(sekret.encode('utf-8'), telo.encode('utf-8'),
                     hashlib.sha256).digest()
    podpis = base64.urlsafe_b64encode(syroe).decode('ascii').rstrip('=')[:27]
    return '%s.%s' % (telo, podpis)


def ssylka_na_anketu(cfg, user_id, metka):
    k = klyuch_dlya(cfg, user_id)
    adres = cfg['sajt_anketa']
    hvost = 'from=%s' % (metka or 'bot')
    if k:
        hvost += '&k=' + k
    return '%s%s%s' % (adres, '&' if '?' in adres else '?', hvost)


# ------------------------------------------------------------ анкета

def _inn_ok(tekst):
    if inn_proverka.is_valid(tekst):
        return inn_proverka.normalize(tekst), None
    return None, inn_proverka.explain(tekst)


def _ne_pusto(minimum, chto):
    def proverka(tekst):
        t = ' '.join(tekst.split())
        if len(t) < minimum:
            return None, chto
        return t, None
    return proverka


# Телеграм пропускает сообщения до четырёх тысяч знаков. В поле
# анкеты столько не нужно: это либо случайная вставка из буфера, либо
# попытка завалить карточку менеджера простынёй.
PREDEL = 300


def obrezat(tekst):
    return ' '.join(tekst.split())[:PREDEL]


def _telefon(tekst):
    cifry = ''.join(c for c in tekst if c.isdigit())
    if len(cifry) < 10:
        return None, 'Похоже на неполный номер. Напишите телефон с кодом, например +7 906 758-77-77.'
    return ' '.join(tekst.split()), None


# Шаги анкеты. Порядок не случаен: сначала то, что человек назовёт не
# задумываясь, телефон — последним. Если бросит на полпути, у нас
# останется хотя бы название и ниша.
SHAGI = [
    ('nazvanie', 'Как называется компания? Напишите так, как её знают клиенты, а не как в реестре.',
     _ne_pusto(2, 'Слишком коротко. Напишите название компании.')),
    ('nisha', 'Чем занимаетесь? Одной строкой, например «доставка цветов» или «ремонт квартир».',
     _ne_pusto(3, 'Напишите род занятий одной строкой.')),
    ('gorod', 'Город и районы, где работаете. Например: Москва, ЦАО и ЮЗАО. Или: Одинцово, Заречье.',
     _ne_pusto(3, 'Напишите город и районы работы.')),
    ('sajt', 'Адрес сайта. Если сайта нет — так и напишите: нет.',
     _ne_pusto(2, 'Напишите адрес сайта или слово «нет».')),
    ('inn', 'ИНН компании: 10 цифр у ООО, 12 у ИП. По нему мы находим компанию в реестре и не путаем с однофамильцами.',
     _inn_ok),
    ('telefon', 'Телефон для связи.', _telefon),
]

# Вопрос про ЛПР идёт кнопками, а не текстом: вариантов ровно два, и
# свободный ответ здесь только мешает.
SHAG_LPR = 'lpr'

PODPISI = {
    'nazvanie': 'Компания',
    'nisha': 'Ниша',
    'gorod': 'Город и районы',
    'sajt': 'Сайт',
    'inn': 'ИНН',
    'telefon': 'Телефон',
    'lpr': 'Решение принимает',
}


def shag_po_imeni(imya):
    for sh in SHAGI:
        if sh[0] == imya:
            return sh
    return None


# ------------------------------------------------------------ хранилище

def zagruzit():
    """Незаконченные анкеты переживают перезапуск бота.

    Без этого любое обновление на хостинге обрывало бы разговор на
    середине, и человек получал бы «начнём сначала» без объяснений.
    """
    try:
        with open(ANKETY, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def sohranit(sostoyanie):
    vremenno = ANKETY + '.tmp'
    with open(vremenno, 'w', encoding='utf-8') as f:
        json.dump(sostoyanie, f, ensure_ascii=False, indent=1)
    os.replace(vremenno, ANKETY)


def pochistit(sostoyanie):
    teper = time.time()
    starye = [k for k, v in sostoyanie.items() if teper - v.get('kogda', 0) > ZHIVET]
    for k in starye:
        del sostoyanie[k]
    return bool(starye)


# ------------------------------------------------------------ сообщения

def knopki(ryady):
    return json.dumps({'inline_keyboard': ryady})


def napisat(cfg, chat_id, tekst, klaviatura=None):
    params = dict(chat_id=chat_id, text=tekst, parse_mode='HTML',
                  disable_web_page_preview=True)
    if klaviatura:
        params['reply_markup'] = klaviatura
    return api(cfg, 'sendMessage', **params)


def poprosit_podpisku(cfg, chat_id):
    napisat(cfg,
            chat_id,
            'Разбор мы делаем бесплатно, но только для подписчиков канала: '
            'его готовит живой человек, а не робот.\n\n'
            'Подпишитесь и нажмите «Я подписался» — проверю и задам '
            'шесть вопросов о компании. Это минута.',
            knopki([
                [{'text': 'Подписаться на канал', 'url': cfg['kanal_ssylka']}],
                [{'text': 'Я подписался', 'callback_data': 'proverit'}],
            ]))


def sprosit(cfg, chat_id, sostoyanie):
    """Задаёт текущий вопрос анкеты."""
    anketa = sostoyanie[str(chat_id)]
    shag = anketa['shag']

    if shag == SHAG_LPR:
        napisat(cfg, chat_id,
                'Вы сами принимаете решение по продвижению или нужно с кем-то согласовывать?',
                knopki([
                    [{'text': 'Решаю сам', 'callback_data': 'lpr:sam'}],
                    [{'text': 'Нужно согласовать', 'callback_data': 'lpr:soglasovanie'}],
                ]))
        return

    if shag == 'itog':
        pokazat_itog(cfg, chat_id, sostoyanie)
        return

    nomer = [s[0] for s in SHAGI].index(shag) + 1
    vsego = len(SHAGI) + 1
    napisat(cfg, chat_id, '<b>%d из %d.</b> %s'
            % (nomer, vsego, html.escape(shag_po_imeni(shag)[1])))


def pokazat_itog(cfg, chat_id, sostoyanie):
    anketa = sostoyanie[str(chat_id)]
    stroki = ['Проверьте, всё ли верно:', '']
    for imya in [s[0] for s in SHAGI] + [SHAG_LPR]:
        znach = anketa['otvety'].get(imya)
        if znach:
            stroki.append('<b>%s:</b> %s' % (PODPISI[imya], html.escape(str(znach))))
    stroki += ['', 'Если всё так — отправляю менеджеру.']
    napisat(cfg, chat_id, '\n'.join(stroki),
            knopki([
                [{'text': 'Отправить', 'callback_data': 'otpravit'}],
                [{'text': 'Заполнить заново', 'callback_data': 'zanovo'}],
            ]))


def predlozhit_put(cfg, chat_id, sostoyanie, metka, kto):
    """Подписка есть — спрашиваем, где человеку удобнее отвечать.

    В боте быстрее: один вопрос за раз, без набора в браузере. На сайте
    привычнее тем, кто пришёл с компьютера и не хочет прыгать между
    окнами. Какой путь выберут чаще — заранее не угадать, поэтому
    показываем оба и смотрим по заявкам.
    """
    sostoyanie[str(chat_id)] = {
        'shag': 'vybor',
        'otvety': {},
        'metka': metka,
        'kto': kto,
        'kogda': time.time(),
    }
    sohranit(sostoyanie)
    napisat(cfg, chat_id,
            'Подписка есть, спасибо. Осталось рассказать о компании — '
            'шесть коротких вопросов.\n\n'
            'Где удобнее ответить?',
            knopki([
                [{'text': 'Прямо здесь', 'callback_data': 'anketa_tut'}],
                [{'text': 'На сайте, одной формой',
                  'url': ssylka_na_anketu(cfg, (kto or {}).get('id', 0), metka)}],
            ]))


def nachat_anketu(cfg, chat_id, sostoyanie, metka, kto):
    sostoyanie[str(chat_id)] = {
        'shag': SHAGI[0][0],
        'otvety': {},
        'metka': metka,
        'kto': kto,
        'kogda': time.time(),
    }
    sohranit(sostoyanie)
    napisat(cfg, chat_id,
            'Подписка есть, спасибо. Шесть коротких вопросов — и менеджер '
            'пришлёт разбор: что отвечают GigaChat и YandexGPT по запросам '
            'вашей ниши и кого называют вместо вас.\n\n'
            'Передумали — напишите /otmena.')
    sprosit(cfg, chat_id, sostoyanie)


def otpravit_menedzheru(cfg, chat_id, sostoyanie):
    anketa = sostoyanie[str(chat_id)]
    kto = anketa.get('kto') or {}

    imya = ' '.join(x for x in (kto.get('first_name'), kto.get('last_name')) if x)
    kontakt = ('@' + kto['username']) if kto.get('username') else 'без имени пользователя'

    stroki = ['<b>Заявка на разбор</b>', '']
    for pole in [s[0] for s in SHAGI] + [SHAG_LPR]:
        znach = anketa['otvety'].get(pole)
        if znach:
            stroki.append('%s: %s' % (PODPISI[pole], html.escape(str(znach))))
    stroki += [
        '',
        'Телеграм: %s %s' % (html.escape(kontakt), html.escape(imya)),
        'Подписка на канал: подтверждена',
        'Источник: %s' % html.escape(anketa.get('metka') or 'бот'),
    ]

    otvet = napisat(cfg, cfg['chat_zayavok'], '\n'.join(stroki))
    if not otvet.get('ok'):
        print('Заявка не ушла в рабочий чат: %s' % otvet.get('description'))
        napisat(cfg, chat_id,
                'Не получилось отправить заявку. Напишите, пожалуйста, ещё раз '
                'через минуту: /start')
        return

    napisat(cfg, chat_id,
            'Заявка у менеджера. Разбор занимает немного времени — ответим '
            'в этом же чате или позвоним.\n\n'
            'Пока ждёте, загляните в канал: каждую неделю разбираем новую '
            'нишу Москвы — кого нейросети называют, а кого не знают вовсе.',
            knopki([[{'text': 'Открыть канал', 'url': cfg['kanal_ssylka']}]]))
    del sostoyanie[str(chat_id)]
    sohranit(sostoyanie)


# ------------------------------------------------------------ обработка

def obrabotat_soobshchenie(cfg, sostoyanie, msg):
    chat_id = msg['chat']['id']
    kluch = str(chat_id)
    tekst = (msg.get('text') or '').strip()
    kto = msg.get('from') or {}

    if not tekst:
        return

    if tekst.startswith('/otmena'):
        sostoyanie.pop(kluch, None)
        sohranit(sostoyanie)
        napisat(cfg, chat_id, 'Отменил. Захотите вернуться — напишите /start.')
        return

    if tekst.startswith('/start'):
        # Метка источника приходит из ссылки на сайте:
        # t.me/бот?start=sajt-glavnaya — по ней видно, какая кнопка
        # привела человека.
        chasti = tekst.split(maxsplit=1)
        metka = chasti[1].strip()[:64] if len(chasti) > 1 else 'бот'
        sostoyanie.pop(kluch, None)

        est = podpisan(cfg, kto.get('id'))
        if est is True:
            predlozhit_put(cfg, chat_id, sostoyanie, metka, kto)
        elif est is False:
            sostoyanie[kluch] = {'shag': 'podpiska', 'otvety': {}, 'metka': metka,
                                 'kto': kto, 'kogda': time.time()}
            sohranit(sostoyanie)
            poprosit_podpisku(cfg, chat_id)
        else:
            napisat(cfg, chat_id,
                    'Не получается проверить подписку — это у нас на стороне. '
                    'Напишите /start через пару минут, уже должно работать.')
        return

    anketa = sostoyanie.get(kluch)
    if not anketa:
        napisat(cfg, chat_id, 'Чтобы получить разбор, напишите /start.')
        return

    shag = anketa['shag']
    # На этих шагах ждём нажатия кнопки, а не текста: человек написал
    # что-то своё — повторяем вопрос вместе с кнопками.
    if shag == 'podpiska':
        poprosit_podpisku(cfg, chat_id)
        return
    if shag == 'vybor':
        predlozhit_put(cfg, chat_id, sostoyanie, anketa.get('metka', 'бот'),
                       anketa.get('kto') or kto)
        return
    if shag in (SHAG_LPR, 'itog'):
        sprosit(cfg, chat_id, sostoyanie)
        return

    opisanie = shag_po_imeni(shag)
    if not opisanie:
        sostoyanie.pop(kluch, None)
        sohranit(sostoyanie)
        napisat(cfg, chat_id, 'Что-то сбилось. Начнём сначала: /start')
        return

    znachenie, oshibka = opisanie[2](obrezat(tekst))
    if oshibka:
        napisat(cfg, chat_id, html.escape(oshibka))
        return

    anketa['otvety'][shag] = znachenie
    anketa['kogda'] = time.time()

    poryadok = [s[0] for s in SHAGI]
    sled = poryadok.index(shag) + 1
    anketa['shag'] = poryadok[sled] if sled < len(poryadok) else SHAG_LPR
    sohranit(sostoyanie)
    sprosit(cfg, chat_id, sostoyanie)


def obrabotat_knopku(cfg, sostoyanie, call):
    dannye = call.get('data') or ''
    soob = call.get('message') or {}
    chat_id = (soob.get('chat') or {}).get('id')
    kto = call.get('from') or {}
    kluch = str(chat_id)

    # Кружок на кнопке снимаем одной попыткой. Раньше этот вызов стоял
    # первым с тремя попытками по минуте: при неладах со связью человек
    # нажимал «Прямо здесь» и три минуты смотрел в тишину — бот ещё
    # даже не дошёл до первого вопроса. Не сняли кружок — не беда,
    # телеграм погасит его сам.
    api(cfg, 'answerCallbackQuery', popytok=1, callback_query_id=call['id'])

    if dannye == 'proverit':
        est = podpisan(cfg, kto.get('id'))
        if est is True:
            metka = (sostoyanie.get(kluch) or {}).get('metka', 'бот')
            predlozhit_put(cfg, chat_id, sostoyanie, metka, kto)
        elif est is False:
            napisat(cfg, chat_id,
                    'Пока не вижу вас среди подписчиков. Подпишитесь и нажмите '
                    '«Я подписался» ещё раз.',
                    knopki([
                        [{'text': 'Подписаться на канал', 'url': cfg['kanal_ssylka']}],
                        [{'text': 'Я подписался', 'callback_data': 'proverit'}],
                    ]))
        else:
            napisat(cfg, chat_id,
                    'Не получается проверить подписку — это у нас на стороне. '
                    'Напишите /start через пару минут.')
        return

    anketa = sostoyanie.get(kluch)
    if not anketa:
        napisat(cfg, chat_id, 'Чтобы получить разбор, напишите /start.')
        return

    if dannye == 'anketa_tut':
        nachat_anketu(cfg, chat_id, sostoyanie, anketa.get('metka', 'бот'),
                      anketa.get('kto') or kto)
        return

    if dannye.startswith('lpr:'):
        anketa['otvety'][SHAG_LPR] = ('сам' if dannye.endswith('sam')
                                      else 'нужно согласование')
        anketa['shag'] = 'itog'
        anketa['kogda'] = time.time()
        sohranit(sostoyanie)
        pokazat_itog(cfg, chat_id, sostoyanie)
        return

    if dannye == 'zanovo':
        anketa['otvety'] = {}
        anketa['shag'] = SHAGI[0][0]
        anketa['kogda'] = time.time()
        sohranit(sostoyanie)
        sprosit(cfg, chat_id, sostoyanie)
        return

    if dannye == 'otpravit':
        otpravit_menedzheru(cfg, chat_id, sostoyanie)
        return


# ------------------------------------------------------------ запуск

def proverit_prava(cfg):
    """Бот должен быть администратором канала.

    Проверяем на запуске, а не на первом клиенте: без этих прав
    телеграм отвечает отказом на любой вопрос о подписке, и бот молча
    отшивал бы всех подряд. Лучше увидеть это в окне запуска.
    """
    nachalo = time.time()
    ya = api(cfg, 'getMe')
    # Время первого запроса печатаем всегда. Оно же и время рукопожатия
    # с телеграмом: дальше бот говорит по той же линии, и если здесь
    # вышло полминуты, значит и каждый ответ человеку будет таким.
    print('Связь с телеграмом: %.1f с.' % (time.time() - nachalo))
    if not ya.get('ok'):
        print('ВНИМАНИЕ: телеграм не принял токен — %s' % ya.get('description'))
        return

    moj_id = ya['result']['id']
    spisok = api(cfg, 'getChatAdministrators', chat_id=cfg['kanal'])
    if not spisok.get('ok'):
        print('ВНИМАНИЕ: не вижу канал %s — %s'
              % (cfg['kanal'], spisok.get('description')))
        print('Проверьте название канала в config.ini и добавьте бота '
              'в его администраторы.')
        print()
        return

    svoi = any((a.get('user') or {}).get('id') == moj_id
               for a in spisok.get('result', []))
    if not svoi:
        print('ВНИМАНИЕ: бот не администратор канала %s.' % cfg['kanal'])
        print('Подписку он проверять не сможет. Добавьте его в '
              'администраторы — права публиковать не нужны.')
        print()


def glavnoe():
    cfg = nastrojki()
    sostoyanie = zagruzit()

    print('Бот-приёмщик запущен.')
    print('Канал: %s' % cfg['kanal'])
    print('Заявки уходят в чат: %s' % cfg['chat_zayavok'])
    if (cfg.get('telegram_api') or '').strip():
        print('Телеграм через свой сайт.')
    print('Остановить: Ctrl+C')
    print()

    proverit_prava(cfg)

    offset = None
    posle_chistki = time.time()
    sboev_podryad = 0

    while True:
        try:
            r = SVYAZ.get(tg_url(cfg, 'getUpdates'),
                          params={'timeout': ZHDAT, 'offset': offset},
                          proxies=tg_proxy(cfg),
                          timeout=(ZHDAT_SVYAZ, ZHDAT + ZHDAT_OTVET))
            dannye = r.json()
        except requests.exceptions.RequestException:
            sboev_podryad += 1
            print('Телеграм не отвечает, пробую снова через 5 секунд…')
            # Долгое молчание — повод не гадать, а посмотреть журнал:
            # там видно, сколько занимает рукопожатие.
            if sboev_podryad == 10:
                print('Телеграм молчит десять раз подряд. Если так и '
                      'останется — смотрите README, раздел про связь.')
            time.sleep(5)
            continue

        sboev_podryad = 0

        if not dannye.get('ok'):
            print('Телеграм ответил отказом: %s' % dannye.get('description'))
            time.sleep(5)
            continue

        for upd in dannye.get('result', []):
            offset = upd['update_id'] + 1
            vzyato = time.time()
            try:
                if 'message' in upd:
                    obrabotat_soobshchenie(cfg, sostoyanie, upd['message'])
                elif 'callback_query' in upd:
                    obrabotat_knopku(cfg, sostoyanie, upd['callback_query'])
            except Exception:
                traceback.print_exc()
            proshlo = time.time() - vzyato
            if proshlo > DOLGO:
                print('обработка заняла %.1f с' % proshlo)

        if time.time() - posle_chistki > 3600:
            if pochistit(sostoyanie):
                sohranit(sostoyanie)
            posle_chistki = time.time()


if __name__ == '__main__':
    try:
        glavnoe()
    except KeyboardInterrupt:
        print('\nОстановлен.')
