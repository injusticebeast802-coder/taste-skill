"""Полный проход: ИНН -> отчёт и картинка."""

import os
import time

from . import ai_gigachat, ai_yandex, company as company_mod, inn as inn_mod
from . import matching, queries, report, search_yandex


class RunError(Exception):
    pass


# Города в том виде, в каком их пишут в заявке: «в Москве», «в Питере».
# Ключ — как встретится в тексте, значение — как надо спрашивать.
#
# Зачем список. Менеджер пишет «барбершоп в Москве», и это и есть
# правда о компании. А в реестре у того же ИП значится посёлок, где он
# прописан, — «Большой Царын» в Калмыкии. Программа брала реестр,
# искала сайт «Britva Большой Царын» и находила рязанский поддомен.
# Слова из заявки должны побеждать реестр и здесь, не только в роде
# занятий.
GORODA = {
    'москве': 'Москва', 'москва': 'Москва', 'мск': 'Москва',
    'петербурге': 'Санкт-Петербург', 'санкт-петербурге': 'Санкт-Петербург',
    'спб': 'Санкт-Петербург', 'питере': 'Санкт-Петербург',
    'новосибирске': 'Новосибирск', 'екатеринбурге': 'Екатеринбург',
    'казани': 'Казань', 'нижнем новгороде': 'Нижний Новгород',
    'челябинске': 'Челябинск', 'красноярске': 'Красноярск',
    'самаре': 'Самара', 'уфе': 'Уфа', 'ростове-на-дону': 'Ростов-на-Дону',
    'краснодаре': 'Краснодар', 'омске': 'Омск', 'воронеже': 'Воронеж',
    'перми': 'Пермь', 'волгограде': 'Волгоград', 'саратове': 'Саратов',
    'тюмени': 'Тюмень', 'тольятти': 'Тольятти', 'ижевске': 'Ижевск',
    'барнауле': 'Барнаул', 'ульяновске': 'Ульяновск', 'иркутске': 'Иркутск',
    'хабаровске': 'Хабаровск', 'владивостоке': 'Владивосток',
    'ярославле': 'Ярославль', 'махачкале': 'Махачкала', 'томске': 'Томск',
    'оренбурге': 'Оренбург', 'кемерове': 'Кемерово', 'рязани': 'Рязань',
    'астрахани': 'Астрахань', 'пензе': 'Пенза', 'липецке': 'Липецк',
    'туле': 'Тула', 'калининграде': 'Калининград', 'сочи': 'Сочи',
}


def vydelit_gorod(kind):
    """Вынимает город из рода занятий: «барбершоп в Москве» -> Москва.

    Возвращает пару: род занятий без города и сам город. Если города
    не узнали, текст остаётся как есть — в вопрос он всё равно попадёт
    и хуже не сделает.
    """
    t = ' '.join((kind or '').split())
    nizhe = t.lower()
    for forma in sorted(GORODA, key=len, reverse=True):
        hvost = ' в ' + forma
        if nizhe.endswith(hvost):
            return t[:len(t) - len(hvost)].strip(' ,'), GORODA[forma]
    return t, ''


# ---------------------------------------------------------------------
# Разбор заявки, вставленной целиком
#
# Менеджер не перепечатывает данные в бота — он пересылает сообщение,
# которое прислал сайт, как есть. С расширенной анкеты в этом сообщении
# приходят город, сайт, конкуренты и запросы клиента, и всё это
# проверке пригодится: город уточняет вопрос, сайт экономит поиск,
# конкуренты попадают на график, а запросы клиента точнее любой нашей
# заготовки.
#
# Ключ — подпись строки в сообщении, значение — наше поле. Значки в
# начале строки не обязательны: при копировании их иногда теряют.
PODPISI = {
    'инн': 'inn',
    'компания': 'brand',
    'род деятельности': 'kind',
    'город и районы': 'city',
    'город': 'city',
    'сайт': 'site',
    'конкуренты': 'rivals',
    'как ищут': 'queries',
}


def razobrat_zayavku(raw):
    """Разбирает сообщение с сайта. Если это не оно — пустой словарь.

    Признак заявки — две и более знакомых подписи. Одной мало:
    «Сайт: romashka.ru» человек может написать и просто так, а
    разбирать такое как заявку значит потерять название компании.
    """
    import re

    polya = {}
    for stroka in str(raw or '').splitlines():
        s = stroka.strip()
        if ':' not in s:
            continue
        podpis, _, znach = s.partition(':')
        # «🏢 Компания» -> «компания»: значки и знаки убираем.
        klyuch = re.sub(r'[^а-яёa-z ]', ' ', podpis.lower())
        klyuch = ' '.join(klyuch.split())
        znach = znach.strip()
        if klyuch in PODPISI and znach:
            polya.setdefault(PODPISI[klyuch], znach)

    return polya if len(polya) >= 2 else {}


def spisok(znach, predel=5):
    """Список через запятую в перечень: «Дента, Белый клык» -> два имени."""
    out = []
    for x in str(znach or '').replace(';', ',').split(','):
        x = ' '.join(x.split()).strip(' .')
        if x and x.lower() not in [y.lower() for y in out]:
            out.append(x)
    return out[:predel]


def domen_iz(znach):
    """Из любого написания адреса делает голое доменное имя.

    В анкете пишут по-разному: «https://romashka.ru/», «www.romashka.ru»,
    «romashka.ru». Дальше по коду домен сравнивается с тем, что нашлось
    в ответе нейросети, и лишний «https://» ломал бы сравнение.
    """
    t = ' '.join(str(znach or '').split()).strip().lower()
    if not t:
        return ''
    t = t.split('//')[-1].split('/')[0].split('?')[0].strip(' .,')
    if t.startswith('www.'):
        t = t[4:]
    # Минимальная проверка: точка и буквы после неё.
    if '.' not in t or len(t.rsplit('.', 1)[-1]) < 2:
        return ''
    return t


def razdelit_mesto(znach):
    """Из «Москва, ЮЗАО и Одинцово» делает («Москва», ['ЮЗАО', 'Одинцово']).

    Первое — город: он подставляется прямо в вопрос нейросети, и весь
    список там превратил бы вопрос в кашу. Остальное — районы, и они
    нужны отдельно: по ним ищем, кто работает рядом, и задаём часть
    вопросов «стоматология, ЮЗАО Москва».
    """
    chasti = []
    for kusok in str(znach or '').replace(';', ',').split(','):
        for x in kusok.split(' и '):
            x = ' '.join(x.split()).strip(' .')
            if x and x.lower() not in [y.lower() for y in chasti]:
                chasti.append(x)
    if not chasti:
        return '', []
    return chasti[0], chasti[1:4]


def pervyj_gorod(znach):
    """Только город, без районов. Оставлено для простых вызовов."""
    return razdelit_mesto(znach)[0]


def parse_request(raw):
    """Разбирает присланное. ИНН не обязателен.

        7707083893                            только ИНН
        7707083893 Flowwow                    ИНН и бренд
        7707083893 Flowwow, доставка цветов   ИНН, бренд, род занятий
        Flowwow, доставка цветов, Москва      без ИНН

    Два источника дополняют друг друга и потому разрешены оба.
    ИНН даёт то, чего нет в заявке с сайта: город и официальное имя.
    Заявка даёт то, чего нет в ИНН: бренд, под которым компанию знает
    рынок, и род занятий человеческими словами. В реестре «ООО
    ФЛАУВАУ» и код ОКВЭД, а спрашивать нейросеть надо про Flowwow и
    доставку цветов.
    """
    # Сначала пробуем прочесть вставленное сообщение с сайта: там всё
    # разложено по подписям и гадать не нужно.
    zayavka = razobrat_zayavku(raw)
    if zayavka:
        import re
        digits = re.sub(r'\D', '', zayavka.get('inn', ''))
        if len(digits) not in (10, 12):
            digits = ''
        brand = zayavka.get('brand', '')
        kind = zayavka.get('kind', '')
        city, _rajony = razdelit_mesto(zayavka.get('city', ''))
        if not city:
            kind, iz_teksta = vydelit_gorod(kind)
            city = iz_teksta
        return digits, brand, kind, city

    text = str(raw or '').strip()

    # ИНН — только если сообщение с цифр и начинается.
    digits = ''
    i = 0
    while i < len(text) and text[i].isdigit():
        digits += text[i]
        i += 1
    if digits and len(digits) not in (10, 12):
        # Цифры есть, но на ИНН не похоже: пусть будут частью названия.
        digits, i = '', 0

    tail = text[i:].strip(' ,;:-')
    parts = [p.strip() for p in tail.split(',')] if tail else []
    parts = [p for p in parts if p]

    brand = parts[0] if len(parts) > 0 else ''
    kind = parts[1] if len(parts) > 1 else ''
    city = parts[2] if len(parts) > 2 else ''

    # Город бывает вписан прямо в род занятий: «барбершоп в Москве».
    # Так пишут чаще, чем третьим через запятую, и это надёжнее
    # реестра: там адрес прописки, а не место работы.
    if not city:
        kind, iz_teksta = vydelit_gorod(kind)
        if iz_teksta:
            city = iz_teksta

    return digits, brand, kind, city


def analyze(raw_inn, cfg, progress=None):
    """Собирает отчёт. progress — функция, которой шлём строки о ходе:
    проверка занимает минуту-две, и без них бот кажется зависшим."""

    def say(msg):
        if progress:
            try:
                progress(msg)
            except Exception:
                pass

    digits, brand, kind_override, city_override = parse_request(raw_inn)
    # Поля расширенной анкеты, если заявку вставили целиком.
    zayavka = razobrat_zayavku(raw_inn)

    if digits:
        problem = inn_mod.explain(digits)
        if problem:
            raise RunError(problem)

        say('Ищу компанию в справочнике…')
        try:
            c = company_mod.lookup(digits, cfg['dadata_token'])
        except company_mod.CompanyError as e:
            raise RunError(str(e))
        except Exception as e:
            # Сюда попадают обрывы связи и таймауты. Показывать человеку
            # внутренности питона незачем: ему нужно понять, что делать.
            raise RunError('Не получилось связаться со справочником DaData.\n'
                           'Проверьте интернет и ключ dadata_token.\n\n%s' % e)
        c['inn'] = digits
    else:
        # Без ИНН работаем по тому, что прислали. Справочник не
        # спрашиваем: по названию он отдаёт десятки однофамильцев,
        # и выбирать за менеджера, который из них клиент, нельзя.
        if not brand or not kind_override:
            raise RunError('Без ИНН нужны название и род занятий через запятую:\n'
                           'Flowwow, доставка цветов, Москва\n\n'
                           'Или пришлите ИНН — тогда достаточно одних цифр.')
        c = {'name': brand, 'full_name': brand, 'inn': '', 'okved': '',
             'kind': kind_override, 'industry': kind_override,
             'kind_from_lead': True,
             'city': city_override, 'status': 'ACTIVE'}

    if brand:
        c['brand'] = brand
    if kind_override:
        # Пометка важна для составления вопросов. Слова из заявки —
        # это слова клиента, ими и надо спрашивать. Строчка ОКВЭД из
        # реестра — казённая, её в вопрос ставить нельзя.
        c['industry'] = kind_override
        c['kind'] = kind_override
        c['kind_from_lead'] = True
    if city_override:
        c['city'] = city_override

    # Все написания, под которыми компанию могут назвать.
    c['names'] = [n for n in (c.get('brand'), c.get('name')) if n]

    # Из расширенной анкеты. Запросы клиента — самое ценное: это его
    # собственные слова, и спрашивать нейросеть надо именно ими, а не
    # нашей заготовкой по отрасли. Конкурентов держим отдельно, чтобы
    # проверить каждого поимённо, даже если в ответах его не назвали
    # ни разу: «вашего конкурента тоже не знают» — это тоже ответ.
    own_q = spisok(zayavka.get('queries'), 8)
    if own_q:
        c['own_queries'] = own_q
        say('Спрошу словами из анкеты: %s' % ', '.join(own_q))
    known_rivals = spisok(zayavka.get('rivals'), 5)
    if known_rivals:
        say('Конкуренты из анкеты: %s' % ', '.join(known_rivals))

    # Районы работы. Если человек назвал конкретный район, конкурентов
    # можно не угадывать по ответам нейросетей, а прямо спросить
    # поиск: «стоматология ЮЗАО Москва». Выдача по такому запросу —
    # это и есть те, к кому уходит клиент, когда его не называют.
    _gorod_iz_ankety, rajony = razdelit_mesto(zayavka.get('city', ''))
    if rajony:
        c['rajony'] = rajony
    sosedi = []
    if rajony and cfg.get('yandex_folder_id') and cfg.get('yandex_search_key'):
        kind_dlya_poiska = c.get('kind') or c.get('industry') or ''
        say('Смотрю, кто работает рядом: %s, %s…' % (kind_dlya_poiska, rajony[0]))
        sosedi = search_yandex.sosedi(
            kind_dlya_poiska, rajony[0], c.get('city', ''),
            cfg['yandex_folder_id'], cfg['yandex_search_key'],
            svoi=c['names'], limit=5)
        if sosedi:
            say('Рядом нашлись: %s' % ', '.join(sosedi))
        else:
            say('Рядом никого не нашли — проверю только по ответам нейросетей.')

    # Названные клиентом идут первыми: он знает, с кем себя сравнивает.
    vse_rivals = list(known_rivals)
    for imya in sosedi:
        if imya.lower() not in [x.lower() for x in vse_rivals]:
            vse_rivals.append(imya)
    if vse_rivals:
        c['known_rivals'] = vse_rivals[:6]

    if c.get('status') and c['status'] != 'ACTIVE':
        say('Внимание: по справочнику компания не действующая.')

    say('Компания: %s · %s · %s' % (c.get('full_name') or c.get('name'),
                                    c.get('city') or 'город не указан',
                                    c.get('industry') or 'род занятий не определён'))

    # --- сайт ---
    # Если сайт указан в анкете, поиск не нужен: своё доменное имя
    # клиент знает точнее, чем его угадает поисковая выдача.
    site = domen_iz(zayavka.get('site'))
    search_broken = ''
    if site:
        say('Сайт из анкеты: %s' % site)
        word = site.split('.')[0]
        if len(word) > 3 and word not in ('www', 'shop', 'site'):
            c['names'].append(word)
    elif cfg.get('yandex_folder_id') and cfg.get('yandex_search_key'):
        say('Ищу сайт компании…')
        try:
            site = search_yandex.find_site(c['names'], c.get('city', ''),
                                           cfg['yandex_folder_id'], cfg['yandex_search_key'],
                                           kind=c.get('kind') or c.get('industry') or '')
        except Exception as e:
            site = ''
            search_broken = str(e)[:400]
            say('Поиск Яндекса не работает:\n%s' % search_broken)
            say('Мест в выдаче в отчёте не будет. Упоминания в нейросетях '
                'считаются как обычно.')
        if site:
            # Домен — ещё одно написание бренда: flowwow.com даёт
            # «flowwow», и его нейросети называют чаще реестрового имени.
            word = site.split('.')[0]
            if len(word) > 3 and word not in ('www', 'shop', 'site'):
                c['names'].append(word)
            say('Сайт: %s' % site)
        elif not search_broken:
            say('Сайт не нашли — дальше проверяю по названию.')

    # --- вопросы нейросетям ---
    qs = queries.build(c, limit=int(cfg.get('questions', 12)))
    if not qs:
        raise RunError('Не понял род занятий компании: в справочнике ОКВЭД %s, '
                       'а по нему тему запроса не составить.\n\n'
                       'Пришлите так: %s Название, чем занимается\n'
                       'Например: %s Flowwow, доставка цветов'
                       % (c.get('okved') or '—', digits or 'ИНН', digits or 'ИНН'))

    if not c.get('city'):
        say('Город неизвестен — спрашиваю без него, по всей стране. '
            'Город можно дописать третьим через запятую.')
    # Показываем все темы, а не первый вопрос: так сразу видно, если
    # узкие слова из заявки потерялись и спрашиваем не о том.
    _narrow, _wide = queries.subjects_for(c)
    say('Спрашиваю про: %s' % ', '.join(_narrow + _wide))

    engines = nejroseti(cfg)
    if not engines:
        raise RunError('Не заданы ключи ни одной нейросети. Загляните в config.ini.')

    ai_results = []
    total = len(qs) * len(engines)
    done = 0
    say('Спрашиваю нейросети: %d вопросов × %d — это минута-две…' % (len(qs), len(engines)))

    for q in qs:
        for name, ask in engines:
            item = {'engine': name, 'query': q, 'answer': '', 'mentioned': False,
                    'position': None, 'error': ''}
            try:
                item['answer'] = ask(q + queries.ASK_TAIL)
                item['mentioned'] = matching.mentioned_any(item['answer'], c['names'])
                if not item['mentioned'] and site:
                    item['mentioned'] = matching.domain_of(site) in item['answer'].lower()
                item['position'] = matching.position_any(item['answer'], c['names'])
            except Exception as e:
                item['error'] = str(e)
            ai_results.append(item)
            done += 1
            if done % 6 == 0:
                say('…%d из %d' % (done, total))
            # Пауза, чтобы не упереться в ограничение по частоте
            time.sleep(float(cfg.get('pause', 0.4)))

    # --- обычный поиск ---
    search_results = []
    if cfg.get('yandex_folder_id') and cfg.get('yandex_search_key') and not search_broken:
        say('Смотрю выдачу Яндекса…')
        for q in queries.search_queries(c, limit=int(cfg.get('search_queries', 5))):
            item = {'query': q, 'position': None, 'url': '', 'error': ''}
            try:
                pos, url = search_yandex.position_of(
                    q, site, c['names'], cfg['yandex_folder_id'], cfg['yandex_search_key'])
                item['position'], item['url'] = pos, url
            except Exception as e:
                item['error'] = str(e)
            search_results.append(item)
            time.sleep(float(cfg.get('pause', 0.4)))

    data = report.build(c, site, ai_results, search_results)
    data['search_broken'] = search_broken

    # Рисуем сразу две картинки — в цветах «ГенИИ» и «Промптера».
    # Заявки приходят с двух сайтов, и менеджер отправляет клиенту ту,
    # на сайте которого тот оставил заявку. Проверка одна и та же,
    # цифры в обеих одинаковые, спрашивать у менеджера нечего.
    out_dir = cfg.get('out_dir', 'otchety')
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M')
    pngs = {}
    for brand in ('genii', 'prompter'):
        path = os.path.join(out_dir, 'otchet-%s-%s-%s.png' % (digits, stamp, brand))
        report.draw_png(data, path, brand=brand)
        pngs[brand] = path
    data['sosedi'] = sosedi
    data['rajony'] = rajony
    data['png'] = pngs['genii']          # для старых вызовов
    data['pngs'] = pngs
    return data


def nejroseti(cfg):
    """Какие нейросети заведены ключами. Список пар: имя и как спросить."""
    out = []
    if cfg.get('yandex_api_key') and cfg.get('yandex_folder_id'):
        out.append(('YandexGPT', lambda q: ai_yandex.ask(
            q, cfg['yandex_folder_id'], cfg['yandex_api_key'],
            cfg.get('yandex_model', 'yandexgpt-lite'))))
    if cfg.get('gigachat_auth_key'):
        out.append(('GigaChat', lambda q: ai_gigachat.ask(
            q, cfg['gigachat_auth_key'], cfg.get('gigachat_scope', 'GIGACHAT_API_PERS'),
            verify=cfg.get('gigachat_verify', True),
            model=cfg.get('gigachat_model') or 'GigaChat',
            url=cfg.get('gigachat_url') or '')))
    return out


def spisok_modelej(cfg):
    """Список моделей GigaChat, доступных нашему ключу.

    Название модели в запросе и название выпуска в рекламе — разные
    вещи: у Сбера выпуск зовётся «Ultra 3.5», а модель в примере
    подписана иначе. Подбирать наугад дорого, сервер скажет точно.
    """
    if not cfg.get('gigachat_auth_key'):
        return 'Ключ GigaChat не заведён — спрашивать не у кого.'

    try:
        spisok = ai_gigachat.modeli(
            cfg['gigachat_auth_key'],
            cfg.get('gigachat_scope', 'GIGACHAT_API_PERS'),
            verify=cfg.get('gigachat_verify', True),
            url=cfg.get('gigachat_url') or '')
    except Exception as e:
        return 'Не вышло спросить список: %s' % str(e)[:400]

    if not spisok:
        return 'Сервер ответил, но список моделей пуст.'

    seychas = cfg.get('gigachat_model') or 'GigaChat'
    lines = ['Модели, доступные вашему ключу:', '']
    for m in spisok:
        lines.append(('> %s  — стоит сейчас' % m) if m == seychas else ('  %s' % m))

    if seychas not in spisok:
        lines.append('')
        lines.append('Внимание: в config.ini стоит «%s», а в списке её нет. '
                     'Впишите в gigachat_model название из списка.' % seychas)
    return '\n'.join(lines)


def zhivy_li(cfg):
    """Задаёт каждой нейросети один пустяковый вопрос и говорит, кто
    ответил. Нужна, чтобы не гадать после проверки, почему счёт вдвое
    меньше: молчащую нейросеть видно сразу и отдельно от результата.
    """
    seti = nejroseti(cfg)
    if not seti:
        return 'Ни одна нейросеть не заведена ключами. Загляните в config.ini.'

    lines = []
    for name, ask in seti:
        try:
            otvet = (ask('Назови два города России. Коротко.') or '').strip()
            if otvet:
                lines.append('%s — отвечает. Сказал: %s' % (name, otvet[:80]))
            else:
                lines.append('%s — ответил пустотой. Ключ принят, но ответа нет.' % name)
        except Exception as e:
            lines.append('%s — не отвечает.\n%s' % (name, str(e)[:300]))

    if len(seti) == 1:
        lines.append('Вторая нейросеть не заведена ключами — проверка идёт '
                     'по одной, и ответов будет вдвое меньше.')
    return '\n\n'.join(lines)


def as_text(data):
    """Короткая выжимка текстом — идёт подписью к картинке."""
    c = data['company']
    head = report.verdict(data)[0]
    # Первой строкой бренд, как и на картинке: подпись и картинка
    # уходят клиенту вместе, и расходиться им нельзя. Реестровое имя
    # идёт следом — оно нужно менеджеру, но не клиенту в заголовке.
    zagolovok = c.get('brand') or c.get('full_name') or c.get('name') or ''
    reestr = c.get('full_name') or c.get('name') or ''
    vtoraya = []
    if reestr and reestr.strip().lower() != zagolovok.strip().lower():
        vtoraya.append(reestr)
    if c.get('inn'):
        vtoraya.append('ИНН %s' % c['inn'])
    vtoraya.append(c.get('city') or 'город не указан')
    vtoraya.append(c.get('industry') or '—')

    lines = [
        zagolovok,
        ' · '.join(vtoraya),
        ('Сайт: %s' % data['site']) if data['site'] else
        ('Сайт: не проверял — поиск Яндекса недоступен' if data.get('search_broken')
         else 'Сайт: не нашли, проверяли по названию'),
        '',
        head + '.',
        'Нейросети назвали компанию в %d ответах из %d.' % (data['ai_named'], data['ai_total']),
    ]
    if data['ai_best_position']:
        lines.append('Лучшее место в списке нейросети — %d-е.' % data['ai_best_position'])
    if data['search_best']:
        stroka = 'В поиске Яндекса лучшее место — %d-е' % data['search_best']
        if data.get('search_best_query'):
            stroka += ' по запросу «%s»' % data['search_best_query']
        lines.append(stroka + '.')
    elif data.get('search_broken'):
        lines.append('Место в поиске Яндекса не смотрел: поиск недоступен.')
    else:
        lines.append('В поиске Яндекса в первой двадцатке не нашли.')
    mesta = [r for r in data['search_results'] if not r.get('error')]
    if mesta:
        lines.append('')
        lines.append('Места в поиске по каждому запросу:')
        for r in mesta:
            lines.append('  %s — %s' % (
                r['query'], ('%d-е' % r['position']) if r.get('position') else 'нет в топ-20'))

    # Кого нашли рядом по указанному району. Отдельной строкой, потому
    # что это не догадка из ответов, а живая выдача поиска: с этими
    # компаниями клиент и делит район.
    if data.get('sosedi'):
        lines.append('')
        gde = ', '.join(data.get('rajony') or []) or 'рядом'
        lines.append('Работают там же (%s): %s.' % (gde, ', '.join(data['sosedi'])))

    if data['rivals']:
        lines.append('')
        chasto = [n for n, k in data['rivals'] if k > 0][:3]
        if chasto:
            lines.append('Чаще называют: ' + ', '.join(chasto) + '.')
        # Конкурент из анкеты, которого не назвали ни разу, — это
        # не пустая строка, а довод в разговоре: их тоже не знают.
        molchat = [n for n, k in data['rivals'] if k == 0]
        if molchat:
            lines.append('Не назвали ни разу: ' + ', '.join(molchat[:3]) + '.')

    # По каждой нейросети отдельно: если одна не ответила совсем,
    # общее число «0 из 12» вводит в заблуждение — кажется, что
    # спросили дважды, а спросили один раз.
    if data['ai_by_engine']:
        lines.append('')
        for name, e in data['ai_by_engine'].items():
            lines.append('%s: назвали в %d из %d ответов.' % (name, e['named'], e['total']))

    failed = {}
    for r in data['ai_results']:
        if r.get('error'):
            failed.setdefault(r['engine'], [0, r['error']])
            failed[r['engine']][0] += 1
    for name, (n, err) in failed.items():
        lines.append('')
        lines.append('%s не ответил на %d вопросов.' % (name, n))
        lines.append(err[:400])

    return '\n'.join(lines)
