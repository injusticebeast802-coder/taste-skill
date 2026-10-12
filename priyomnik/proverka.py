#!/usr/bin/env python3
"""Проверка анкеты без телеграма.

Бот разговаривает с живым человеком, и сломанная анкета видна только
на клиенте — то есть поздно. Поэтому ход разговора проверяем здесь:
подставляем ответы и смотрим, что бот спросил бы дальше и что отправил
бы менеджеру. Сеть при этом не нужна, токен тоже.

Запуск:  python proverka.py
"""

import io
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bot as b

oshibki = []


def ravno(bylo, zhdali, chto):
    if bylo != zhdali:
        oshibki.append('%s: ждали %r, вышло %r' % (chto, zhdali, bylo))


# ---------------------------------------------------------- проверки

def proverka_polej():
    """Каждый шаг пропускает верное значение и отвергает мусор."""
    sluchai = [
        ('nazvanie', 'Брусина', True),
        ('nazvanie', 'Б', False),
        ('nisha', 'доставка цветов', True),
        ('nisha', '  ', False),
        ('gorod', 'Одинцово, Заречье', True),
        ('sajt', 'нет', True),
        ('inn', '9702020445', True),
        ('inn', '9702020446', False),          # контрольная цифра не сошлась
        ('inn', '970202044', False),           # девять цифр
        ('inn', 'нет ИНН', False),
        ('telefon', '+7 906 758-77-77', True),
        ('telefon', '12345', False),
    ]
    for pole, tekst, godno in sluchai:
        shag = b.shag_po_imeni(pole)
        znach, oshibka = shag[2](tekst)
        ravno(oshibka is None, godno, 'поле %s на %r' % (pole, tekst))
        if godno:
            ravno(bool(znach), True, 'поле %s вернуло пустое значение' % pole)


def proverka_inn_chistitsya():
    """ИНН из заявки приходит с пробелами и дефисами — их отрезаем."""
    znach, oshibka = b.shag_po_imeni('inn')[2](' 9702-020-445 ')
    ravno(oshibka, None, 'ИНН с пробелами забракован')
    ravno(znach, '9702020445', 'ИНН не очистился')


def proverka_poryadka():
    """Анкета идёт по порядку и заканчивается вопросом про ЛПР."""
    poryadok = [s[0] for s in b.SHAGI]
    ravno(poryadok[0], 'nazvanie', 'первый вопрос')
    ravno(poryadok[-1], 'telefon', 'последний вопрос анкеты')
    ravno(len(set(poryadok)), len(poryadok), 'шаги повторяются')
    for imya in poryadok + [b.SHAG_LPR]:
        if imya not in b.PODPISI:
            oshibki.append('шаг %s без подписи в карточке менеджера' % imya)


def proverka_dlinnogo_otveta():
    """Длинный ответ обрезается до предела, а не уходит в карточку целиком."""
    ravno(len(b.obrezat('А' * 4000)), b.PREDEL, 'длинный ответ не обрезан')
    ravno(b.obrezat('  Брусина   и   сыновья '), 'Брусина и сыновья',
          'лишние пробелы не убраны')
    znach, oshibka = b.shag_po_imeni('nazvanie')[2](b.obrezat('А' * 4000))
    ravno(oshibka, None, 'обрезанное название забраковано')


def proverka_hranilishcha():
    """Незаконченные анкеты переживают перезапуск и протухают за сутки."""
    staroe = b.ANKETY
    b.ANKETY = os.path.join(os.path.dirname(staroe), 'anketa-proverka.json')
    try:
        sostoyanie = {'1': {'shag': 'nisha', 'otvety': {'nazvanie': 'Брусина'},
                            'kogda': __import__('time').time()},
                      '2': {'shag': 'nisha', 'otvety': {}, 'kogda': 0}}
        b.sohranit(sostoyanie)
        snova = b.zagruzit()
        ravno(snova['1']['otvety']['nazvanie'], 'Брусина', 'анкета не пережила запись')

        b.pochistit(snova)
        ravno('2' in snova, False, 'вчерашняя анкета не убрана')
        ravno('1' in snova, True, 'свежую анкету убрали зря')
    finally:
        if os.path.exists(b.ANKETY):
            os.remove(b.ANKETY)
        b.ANKETY = staroe


def proverka_bitogo_fajla():
    """config.ini, побитый при правке в nano, всё равно читается.

    Так он выглядел на хостинге: первая строка комментария перенеслась
    без точки с запятой, а сверху ещё и команда запуска из буфера.
    """
    bityj = (
        'sh ~/priyomnik/hosting/bot.sh start\n'
        '; Настройки бота. Скопируйте этот файл в config.ini и впишите\n'
        'значения вместо многоточий. ; config.ini в репозиторий не попадает\n'
        '[keys]\n'
        'telegram_token = 123:ABC\n'
        'случайная строка без равенства\n'
        'kanal = @geniimoscow\n'
        'chat_zayavok = -5376497048\n'
    )
    import configparser
    razbor = configparser.ConfigParser()
    razbor.read_string(b.ochistit(bityj))
    ravno(razbor['keys']['kanal'], '@geniimoscow', 'канал не прочитался')
    ravno(razbor['keys']['chat_zayavok'], '-5376497048', 'чат не прочитался')
    ravno(razbor['keys']['telegram_token'], '123:ABC', 'токен не прочитался')


def proverka_kanala():
    """Название канала приводится к виду @имя, ссылка собирается сама."""
    cfg = {'kanal': 'geniimoscow', 'kanal_ssylka': ''}
    kanal = cfg['kanal'].strip()
    if not kanal.startswith('@') and not kanal.lstrip('-').isdigit():
        kanal = '@' + kanal
    ravno(kanal, '@geniimoscow', 'собачка не добавилась')
    ravno('https://t.me/' + kanal.lstrip('@'), 'https://t.me/geniimoscow',
          'ссылка на канал собралась неверно')


def proverka_razgovora():
    """Весь путь человека: /start, подписка, кнопка «Прямо здесь», ответы.

    Кнопки — самое хрупкое место: нажатие приходит не сообщением, а
    отдельным запросом, и ошибка в разборе выглядит как «бот не
    отвечает». Поэтому проходим разговор целиком, подменив телеграм
    записной книжкой: что бот отправил бы, то и проверяем.
    """
    poslano = []

    def pritvorno(cfg, metod, **params):
        poslano.append((metod, params))
        if metod == 'getChatMember':
            return {'ok': True, 'result': {'status': 'member'}}
        if metod == 'getMe':
            return {'ok': True, 'result': {'id': 1}}
        return {'ok': True, 'result': {'message_id': len(poslano)}}

    nastoyashchij = b.api
    staroe = b.ANKETY
    b.api = pritvorno
    b.ANKETY = os.path.join(os.path.dirname(staroe), 'anketa-razgovor.json')
    cfg = {'kanal': '@geniimoscow', 'kanal_ssylka': 'https://t.me/geniimoscow',
           'sajt_anketa': 'https://genii-ai.ru/analiz', 'sekret_ssylki': '',
           'chat_zayavok': '-100500'}
    kto = {'id': 777, 'first_name': 'Иван', 'username': 'ivanov'}
    chat = {'id': 777}
    sostoyanie = {}

    def teksty():
        return [p.get('text', '') for m, p in poslano if m == 'sendMessage']

    def knopki_poslednego():
        for metod, params in reversed(poslano):
            if metod == 'sendMessage' and params.get('reply_markup'):
                razbor = __import__('json').loads(params['reply_markup'])
                return [k for ryad in razbor['inline_keyboard'] for k in ryad]
        return []

    try:
        # 1. /start с меткой сайта: подписка есть — предлагаем два пути.
        b.obrabotat_soobshchenie(cfg, sostoyanie, {
            'chat': chat, 'from': kto, 'text': '/start sajt-glavnaya'})
        ravno(sostoyanie['777']['shag'], 'vybor', 'после /start не спросили о пути')
        ravno(sostoyanie['777']['metka'], 'sajt-glavnaya', 'метка источника потерялась')
        imena = [k['text'] for k in knopki_poslednego()]
        ravno(imena, ['Прямо здесь', 'На сайте, одной формой'], 'кнопки выбора пути')
        tut = knopki_poslednego()[0]
        ravno(tut.get('callback_data'), 'anketa_tut', 'у кнопки нет данных для нажатия')

        # 2. Нажатие «Прямо здесь» — то самое место, где бот молчал.
        b.obrabotat_knopku(cfg, sostoyanie, {
            'id': 'a1', 'from': kto, 'message': {'chat': chat},
            'data': tut['callback_data']})
        ravno(sostoyanie['777']['shag'], b.SHAGI[0][0],
              'кнопка «Прямо здесь» не начала анкету')
        ravno('1 из 7' in teksty()[-1], True,
              'после кнопки не задан первый вопрос: %r' % teksty()[-1])

        # 3. Шесть ответов подряд.
        for otvet in ('Брусина', 'строительство домов', 'Одинцово',
                      'brusina.ru', '9702020445', '+7 906 758-77-77'):
            b.obrabotat_soobshchenie(cfg, sostoyanie, {
                'chat': chat, 'from': kto, 'text': otvet})
        ravno(sostoyanie['777']['shag'], b.SHAG_LPR, 'не дошли до вопроса про ЛПР')

        # 4. Кнопка про ЛПР, сводка и отправка менеджеру.
        b.obrabotat_knopku(cfg, sostoyanie, {
            'id': 'a2', 'from': kto, 'message': {'chat': chat}, 'data': 'lpr:sam'})
        ravno(sostoyanie['777']['shag'], 'itog', 'после ЛПР не показали сводку')

        b.obrabotat_knopku(cfg, sostoyanie, {
            'id': 'a3', 'from': kto, 'message': {'chat': chat}, 'data': 'otpravit'})
        ravno('777' in sostoyanie, False, 'отправленная анкета осталась в памяти')

        kartochka = [p for m, p in poslano
                     if m == 'sendMessage' and str(p.get('chat_id')) == '-100500']
        ravno(len(kartochka), 1, 'карточка менеджеру не ушла')
        if kartochka:
            telo = kartochka[0]['text']
            for kusok in ('Брусина', '9702020445', 'sajt-glavnaya', 'ivanov'):
                if kusok not in telo:
                    oshibki.append('в карточке менеджеру нет %r' % kusok)

        # 5. Нажатие на старую кнопку, когда анкеты уже нет, не роняет бота.
        b.obrabotat_knopku(cfg, sostoyanie, {
            'id': 'a4', 'from': kto, 'message': {'chat': chat}, 'data': 'anketa_tut'})
        ravno('/start' in teksty()[-1], True, 'на старую кнопку бот не ответил')

        # 6. Нет подписки — анкету не начинаем, зовём подписаться.
        def nepodpisan(cfg, metod, **params):
            if metod == 'getChatMember':
                poslano.append((metod, params))
                return {'ok': True, 'result': {'status': 'left'}}
            return pritvorno(cfg, metod, **params)

        b.api = nepodpisan
        b.obrabotat_soobshchenie(cfg, sostoyanie, {
            'chat': chat, 'from': kto, 'text': '/start'})
        ravno(sostoyanie['777']['shag'], 'podpiska', 'неподписанного пустили в анкету')
        ravno([k['text'] for k in knopki_poslednego()],
              ['Подписаться на канал', 'Я подписался'], 'кнопки подписки')
    finally:
        b.api = nastoyashchij
        if os.path.exists(b.ANKETY):
            os.remove(b.ANKETY)
        b.ANKETY = staroe


def proverka_dvuh_sajtov():
    """Человека возвращают на тот сайт, с которого он пришёл.

    Бот и канал у сайтов общие, а анкеты разные. Отправить клиента
    «Промптера» доделывать анкету на «ГенИИ» — значит потерять его на
    первом же незнакомом логотипе.
    """
    cfg = {'sajt_anketa': 'https://genii-ai.ru/analiz',
           'sajt_anketa_prompter': 'https://prompter-ai.moscow/analiz',
           'sekret_ssylki': 'sekret-dlya-proverki-40-znakov-abcdefgh'}

    ravno(b.adres_ankety(cfg, 'prompter-glavnaya'),
          'https://prompter-ai.moscow/analiz', 'клиента промптера увели на чужой сайт')
    ravno(b.adres_ankety(cfg, 'prompter'), 'https://prompter-ai.moscow/analiz',
          'короткая метка промптера не узнана')
    ravno(b.adres_ankety(cfg, 'sajt-glavnaya'), 'https://genii-ai.ru/analiz',
          'клиента ГенИИ увели на чужой сайт')
    ravno(b.adres_ankety(cfg, 'бот'), 'https://genii-ai.ru/analiz',
          'без метки берём адрес по умолчанию')
    ravno(b.adres_ankety(cfg, ''), 'https://genii-ai.ru/analiz',
          'пустая метка уронила выбор адреса')

    # Второй адрес не заполнен — ведём на тот, что есть, а не в никуда.
    ravno(b.adres_ankety({'sajt_anketa': 'https://genii-ai.ru/analiz',
                          'sajt_anketa_prompter': ''}, 'prompter-glavnaya'),
          'https://genii-ai.ru/analiz', 'пустой второй адрес не подменился первым')

    # В ссылке едут и метка, и ключ подписки: по метке менеджер видит
    # источник, по ключу сайт понимает, что подписка проверена.
    ssylka = b.ssylka_na_anketu(cfg, 777000123, 'prompter-anketa')
    ravno(ssylka.startswith('https://prompter-ai.moscow/analiz?'), True,
          'ссылка собралась не на тот сайт: %s' % ssylka)
    ravno('from=prompter-anketa' in ssylka, True, 'метка потерялась: %s' % ssylka)
    ravno('&k=777000123.' in ssylka, True, 'ключ подписки потерялся: %s' % ssylka)


def proverka_chata_zayavok():
    """Бот сам называет номер чата и записывает его себе в настройки.

    Это то место, на котором всё и встало: номер чата переписали у
    другого бота, он оказался верным — а телеграм всё равно ответил
    «chat not found», потому что право писать он выдаёт не номеру, а
    участнику. Команда приходит из того самого чата, где бот уже
    состоит, поэтому ошибиться там нечем.
    """
    import tempfile
    poslano = []
    nachalnik = {'id': 1, 'first_name': 'Хозяин'}
    prohozhij = {'id': 2, 'first_name': 'Гость'}

    def pritvorno(cfg, metod, **params):
        poslano.append((metod, params))
        if metod == 'getChatMember':
            status = 'creator' if params.get('user_id') == 1 else 'member'
            return {'ok': True, 'result': {'status': status}}
        return {'ok': True, 'result': {'message_id': len(poslano)}}

    nastoyashchij, staryj_tut = b.api, b.TUT
    staroe_hranilishche = b.ANKETY
    papka = tempfile.mkdtemp()
    b.api = pritvorno
    b.TUT = papka
    b.ANKETY = os.path.join(papka, 'anketa.json')
    ini = os.path.join(papka, 'config.ini')
    io.open(ini, 'w', encoding='utf-8').write(
        '; пояснение, которое нельзя потерять\n'
        '[keys]\n'
        'telegram_token = 123:ABC\n'
        '; номер чата подскажет @userinfobot\n'
        'chat_zayavok = -111\n'
        'kanal = @k\n')

    cfg = {'kanal': '@k', 'kanal_ssylka': 'https://t.me/k',
           'chat_zayavok': '-111', 'sajt_anketa': '', 'sekret_ssylki': ''}
    gruppa = {'id': -5376497048, 'type': 'supergroup'}
    sostoyanie = {}

    def posledneye():
        return [p for m, p in poslano if m == 'sendMessage'][-1]['text']

    try:
        # 1. Номер чата бот называет кому угодно: это не секрет.
        b.obrabotat_soobshchenie(cfg, sostoyanie, {
            'chat': gruppa, 'from': prohozhij, 'text': '/chat'})
        ravno('-5376497048' in posledneye(), True,
              'бот не назвал номер чата: %r' % posledneye())

        # 2. А менять настройку из группы может только администратор:
        #    иначе любой, кого позвали в чат, уведёт заявки себе.
        b.obrabotat_soobshchenie(cfg, sostoyanie, {
            'chat': gruppa, 'from': prohozhij, 'text': '/zayavki_syuda'})
        ravno(cfg['chat_zayavok'], '-111', 'посторонний сменил чат заявок')
        ravno('администратор' in posledneye(), True,
              'постороннему не объяснили отказ: %r' % posledneye())

        # 3. Администратор — меняет, и настройка работает сразу.
        b.obrabotat_soobshchenie(cfg, sostoyanie, {
            'chat': gruppa, 'from': nachalnik, 'text': '/zayavki_syuda'})
        ravno(cfg['chat_zayavok'], '-5376497048', 'чат заявок не сменился в памяти')

        stalo = io.open(ini, encoding='utf-8').read()
        ravno('chat_zayavok = -5376497048' in stalo, True,
              'номер не записан в config.ini')
        ravno('пояснение, которое нельзя потерять' in stalo, True,
              'правка настройки съела комментарии')
        ravno('telegram_token = 123:ABC' in stalo, True,
              'правка настройки потеряла токен')
        ravno(stalo.count('chat_zayavok ='), 1,
              'строка чата задвоилась: %r' % stalo)
    finally:
        b.api = nastoyashchij
        b.TUT = staryj_tut
        b.ANKETY = staroe_hranilishche
        shutil.rmtree(papka, ignore_errors=True)


def proverka_poteri_zayavki():
    """Чат менеджеров не принял заявку — ответы человека не пропадают.

    Шесть вопросов о своей компании человек отвечает один раз. Если в
    этот момент у нас не вышло с рабочим чатом, предлагать ему /start
    нельзя: /start стирает анкету, и он набирал бы всё заново из-за
    нашей беды, а не своей.
    """
    poslano = []
    chat_menedzherov = '-100500'

    def pritvorno(cfg, metod, **params):
        poslano.append((metod, params))
        if metod == 'getChatMember':
            return {'ok': True, 'result': {'status': 'member'}}
        if (metod == 'sendMessage'
                and str(params.get('chat_id')) == chat_menedzherov):
            return {'ok': False, 'description': 'Bad Request: chat not found'}
        return {'ok': True, 'result': {'message_id': len(poslano)}}

    nastoyashchij = b.api
    staroe = b.ANKETY
    b.api = pritvorno
    b.ANKETY = os.path.join(os.path.dirname(staroe), 'anketa-poterya.json')
    cfg = {'kanal': '@k', 'kanal_ssylka': 'https://t.me/k',
           'sajt_anketa': 'https://genii-ai.ru/analiz', 'sekret_ssylki': '',
           'chat_zayavok': chat_menedzherov}
    kto = {'id': 777, 'first_name': 'Иван'}
    chat = {'id': 777}
    sostoyanie = {}

    try:
        b.obrabotat_soobshchenie(cfg, sostoyanie, {
            'chat': chat, 'from': kto, 'text': '/start'})
        b.obrabotat_knopku(cfg, sostoyanie, {
            'id': 'a1', 'from': kto, 'message': {'chat': chat},
            'data': 'anketa_tut'})
        for otvet in ('Брусина', 'стройка', 'Одинцово', 'brusina.ru',
                      '9702020445', '+7 906 758-77-77'):
            b.obrabotat_soobshchenie(cfg, sostoyanie, {
                'chat': chat, 'from': kto, 'text': otvet})
        b.obrabotat_knopku(cfg, sostoyanie, {
            'id': 'a2', 'from': kto, 'message': {'chat': chat}, 'data': 'lpr:sam'})

        b.obrabotat_knopku(cfg, sostoyanie, {
            'id': 'a3', 'from': kto, 'message': {'chat': chat}, 'data': 'otpravit'})

        ravno('777' in sostoyanie, True, 'анкета стёрлась, хотя заявка не ушла')
        ravno(sostoyanie['777']['otvety'].get('nazvanie'), 'Брусина',
              'ответы пропали после неудачной отправки')

        posledneye = [p for m, p in poslano
                      if m == 'sendMessage' and str(p.get('chat_id')) == '777'][-1]
        ravno('/start' in posledneye['text'], False,
              'человека отправили на /start, а он стирает анкету')
        knopki = __import__('json').loads(posledneye.get('reply_markup') or '{}')
        imena = [k['text'] for ryad in knopki.get('inline_keyboard', [])
                 for k in ryad]
        ravno(imena, ['Отправить ещё раз'], 'нет кнопки повторной отправки')

        # Со второго раза чат отвечает — заявка уходит, анкета стирается.
        def teper_prinimaet(cfg, metod, **params):
            if (metod == 'sendMessage'
                    and str(params.get('chat_id')) == chat_menedzherov):
                poslano.append((metod, params))
                return {'ok': True, 'result': {'message_id': 1}}
            return pritvorno(cfg, metod, **params)

        b.api = teper_prinimaet
        b.obrabotat_knopku(cfg, sostoyanie, {
            'id': 'a4', 'from': kto, 'message': {'chat': chat}, 'data': 'otpravit'})
        ravno('777' in sostoyanie, False, 'после удачной отправки анкета осталась')
    finally:
        b.api = nastoyashchij
        if os.path.exists(b.ANKETY):
            os.remove(b.ANKETY)
        b.ANKETY = staroe


def proverka_posrednika():
    """Через посредника бот ходит со своим токеном, а не с чужим.

    Посредник общий с ботом отчётов, и токены у них разные. Забыть
    сказать, чей брать, — значит отвечать человеку от имени не того
    бота, в котором он спрашивал: такое не поймаешь глазами, оно
    выглядит как «бот ответил», только бот другой.
    """
    cherez_sajt = {'telegram_api': 'https://genii-ai.ru/tg.php?k=parol'}
    adres = b.tg_url(cherez_sajt, 'getChatMember')
    ravno('m=getChatMember' in adres, True, 'метод не попал в адрес: %s' % adres)
    ravno('b=priyom' in adres, True, 'посреднику не сказано, чей токен: %s' % adres)

    rabotnik = {'telegram_api': 'https://tg.l.workers.dev/?k=parol'}
    ravno('&m=sendMessage&b=priyom' in b.tg_url(rabotnik, 'sendMessage'), True,
          'адрес работника собрался неверно')

    pryamo = b.tg_url({'telegram_token': '123:ABC'}, 'getMe')
    ravno(pryamo, 'https://api.telegram.org/bot123:ABC/getMe',
          'прямой адрес собрался неверно')

    # Методы, без которых приёмщик не работает, должны быть разрешены
    # у обоих посредников: закрытый список — ровно то место, где
    # второй бот молча упирается в «команда не разрешена».
    nuzhno = ('getUpdates', 'sendMessage', 'getChatMember',
              'getChatAdministrators', 'answerCallbackQuery')
    ryadom = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Файлы посредников читаем, только когда рядом лежит весь проект.
    #
    # Смотреть на «а есть ли рядом папка priyomnik» было нельзя: на
    # хостинге бот и живёт в папке priyomnik, рядом с ним стоит
    # analiz — и проверка добралась до развёрнутой копии работника,
    # сказав «анкета сломана» про файл, который к анкете отношения не
    # имеет. Признаком проекта берём то, чего на хостинге не бывает:
    # исходники сайта лежат там развёрнутыми, а не папкой genii.
    if not os.path.exists(os.path.join(ryadom, 'genii', 'hosting-ru', 'tg.php')):
        return

    posredniki = [
        os.path.join(ryadom, 'genii', 'hosting-ru', 'tg.php'),
        os.path.join(ryadom, 'analiz', 'cloudflare', 'tg-worker.js'),
    ]
    for put in posredniki:
        if not os.path.exists(put):
            continue
        ishodnik = open(put, encoding='utf-8').read()
        spisok = ishodnik.split('MOZHNO', 1)[-1] if 'MOZHNO' in ishodnik else \
            ishodnik.split('$mozhno', 1)[-1]
        spisok = spisok[:spisok.index(';')]
        for metod in nuzhno:
            if "'%s'" % metod not in spisok:
                oshibki.append('%s не разрешает %s'
                               % (os.path.basename(put), metod))
        if 'TG_TOKEN_PRIYOM' not in ishodnik:
            oshibki.append('%s не знает токена приёмщика'
                           % os.path.basename(put))


def proverka_dorogi():
    """Разбор ответа посредника: наш бот, чужой бот, отказ, мусор.

    Это та проверка, которой вчера не хватило. Посредник ответил
    исправно, команда сказала «дорога рабочая» — и была неправа:
    ответил бот отчётов, потому что старый работник Cloudflare на
    пометку b=priyom не смотрит. Клиент спросил бы у приёмщика, а
    написал бы ему другой бот, тот, что разговаривает только с
    менеджерами. Глазами такое не ловится.
    """
    ryadom = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hosting')
    if not os.path.exists(os.path.join(ryadom, 'proverit_dorogu.py')):
        print('proverit_dorogu.py рядом нет — эту проверку пропускаю')
        return
    sys.path.insert(0, ryadom)
    import proverit_dorogu as d

    nash = '8946754103:AAHtestovyj'
    svoj = '{"ok":true,"result":{"id":8946754103,"username":"Priyomshchik"}}'
    chuzhoj = '{"ok":true,"result":{"id":111222333,"username":"Otchetnyj"}}'

    ravno(d.razobrat(svoj, nash), 'ДА: Priyomshchik', 'свой бот не узнан')
    ravno(d.razobrat(chuzhoj, nash), 'ЧУЖОЙ: Otchetnyj',
          'чужой бот прошёл как свой — ровно вчерашняя ошибка')

    otkaz = '{"ok":false,"description":"Команда не разрешена: getMe"}'
    ravno(d.razobrat(otkaz, nash), 'НЕТ: Команда не разрешена: getMe',
          'отказ посредника не разобран')

    for musor in ('<html>404</html>', '', 'ok'):
        otvet = d.razobrat(musor, nash)
        ravno(otvet.startswith('НЕТ:'), True,
              'мусор %r разобран как %r' % (musor, otvet))

    # Бот без имени пользователя — редкость, но падать на нём нельзя.
    ravno(d.razobrat('{"ok":true,"result":{"id":8946754103}}', nash),
          'ДА: 8946754103', 'бот без имени не разобран')


if __name__ == '__main__':
    for proverka in (proverka_polej, proverka_inn_chistitsya, proverka_poryadka,
                     proverka_dlinnogo_otveta, proverka_hranilishcha,
                     proverka_bitogo_fajla, proverka_kanala,
                     proverka_razgovora,
                     proverka_dvuh_sajtov, proverka_chata_zayavok,
                     proverka_poteri_zayavki, proverka_posrednika, proverka_dorogi):
        proverka()

    if oshibki:
        print('ОШИБКИ:')
        for o in oshibki:
            print('  -', o)
        sys.exit(1)
    print('анкета в порядке')
