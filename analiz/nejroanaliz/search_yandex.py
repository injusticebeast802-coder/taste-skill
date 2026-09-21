"""Обычный поиск Яндекса через сервис XML.

Нужен для двух вещей: найти сайт компании по названию и посмотреть,
на каком месте он стоит по запросам ниши. Если сайта нет — считаем
упоминания названия в заголовках и описаниях найденных страниц.
"""

import base64
import xml.etree.ElementTree as ET

import requests

from . import matching

# У поиска Яндекса два входа, и какой из них открыт — зависит от
# того, как подключена услуга в облаке. Пробуем оба: сначала новый
# облачный, потом прежний адрес с параметрами в ссылке. Какой
# сработает, тот и запоминаем на время запуска, чтобы не ходить
# дважды на каждый запрос.
URL_V2 = 'https://searchapi.api.cloud.yandex.net/v2/web/search'
URL_V1 = 'https://yandex.ru/search/xml'

# 20 результатов на страницу: дальше второй десятки место уже не имеет
# смысла — туда не доходят.
GROUPBY = 'attr=d.mode=deep.groups-on-page=20.docs-in-group=1'

_working = {'kind': ''}


class SearchError(Exception):
    pass


def _text(node):
    """Текст узла вместе с вложенными <hlword> — их Яндекс ставит
    вокруг найденных слов, и без них фраза рвётся."""
    return ''.join(node.itertext()) if node is not None else ''


def _parse_xml(data):
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        raise SearchError('Поиск Яндекса вернул не разобранный ответ.')

    err = root.find('.//error')
    if err is not None:
        raise SearchError('Поиск Яндекса: %s' % (err.text or 'ошибка'))

    out = []
    for doc in root.findall('.//doc'):
        url = (doc.findtext('url') or '').strip()
        title = _text(doc.find('title'))
        passages = ' '.join(_text(p) for p in doc.findall('.//passage'))
        out.append({'url': url, 'title': title.strip(), 'text': passages.strip()})
    return out


def _search_v2(query, folder_id, api_key, timeout):
    """Облачный вход. Ответ приходит XML-кой, упакованной в base64."""
    r = requests.post(
        URL_V2,
        headers={'Authorization': 'Api-Key ' + api_key,
                 'Content-Type': 'application/json'},
        json={
            'query': {'searchType': 'SEARCH_TYPE_RU', 'queryText': query, 'page': '0'},
            'folderId': folder_id,
            'responseFormat': 'FORMAT_XML',
            'groupSpec': {'groupMode': 'GROUP_MODE_DEEP',
                          'groupsOnPage': '20', 'docsInGroup': '1'},
        },
        timeout=timeout,
    )
    if r.status_code != 200:
        raise SearchError('облачный вход ответил %d: %s' % (r.status_code, r.text[:300]))

    raw = (r.json() or {}).get('rawData')
    if not raw:
        raise SearchError('облачный вход вернул ответ без данных.')
    return _parse_xml(base64.b64decode(raw))


def _search_v1(query, folder_id, api_key, timeout):
    """Прежний вход: ключ и каталог передаются прямо в ссылке."""
    r = requests.get(
        URL_V1,
        params={'folderid': folder_id, 'apikey': api_key, 'query': query,
                'l10n': 'ru', 'sortby': 'rlv', 'filter': 'none', 'groupby': GROUPBY},
        timeout=timeout,
    )
    if r.status_code != 200:
        raise SearchError('прежний вход ответил %d: %s' % (r.status_code, r.text[:300]))
    return _parse_xml(r.content)


def raw_search(query, folder_id, api_key, timeout=20):
    """Возвращает список найденного: адрес, заголовок, описание."""
    ways = [('v2', _search_v2), ('v1', _search_v1)]
    if _working['kind']:
        ways.sort(key=lambda x: x[0] != _working['kind'])

    problems = []
    for kind, fn in ways:
        try:
            docs = fn(query, folder_id, api_key, timeout)
            _working['kind'] = kind
            return docs
        except SearchError as e:
            problems.append(str(e))
        except requests.exceptions.RequestException as e:
            problems.append('%s: связь оборвалась (%s)' % (kind, str(e)[:120]))

    raise SearchError('Поиск Яндекса не ответил ни по одному адресу.\n' +
                      '\n'.join(problems))


# Слова, по которым видно, что это соседняя контора с тем же
# брендом, а не сам клиент. У барбершопа «Бритва» есть школа барберов
# britva-academy.ru, и она выходит в поиске раньше самого барбершопа:
# бренд в имени тот же, и отличить их можно только по роду занятий.
CHUZHIE = ('academy', 'академи', 'school', 'школ', 'курс', 'обучени',
           'franch', 'франш', 'вакансии', 'работа в', 'оптом', 'b2b',
           'forum', 'форум', 'блог', 'blog', 'wiki')


def _ochki(indeks, host, zagolovok, opisanie, names, kind):
    """Насколько эта ссылка похожа на сайт нашей компании.

    Брать первую попавшуюся нельзя: поиск ставит вперёд то, что чаще
    открывают, а это бывает школа, франшиза или форум. Поэтому
    считаем приметы, а место в выдаче остаётся лишь одной из них.
    """
    h = host.lower()
    zag = (zagolovok or '').lower()
    ves = zag + ' ' + (opisanie or '').lower()
    ochki = 0.0

    # Бренд прямо в имени сайта — самая сильная примета.
    for n in names:
        korotko = matching.fold(n)
        if korotko and korotko in matching.fold(h):
            ochki += 4
            break

    # Род занятий в заголовке или описании: так барбершоп отличается
    # от школы барберов, у которых бренд общий.
    slova = [w for w in (kind or '').lower().replace('-', ' ').split() if len(w) > 4]
    if slova and any(w[:6] in ves for w in slova):
        ochki += 3

    # Название встретилось в тексте страницы.
    if matching.mentioned_any(zag + ' ' + (opisanie or ''), names):
        ochki += 2

    # Соседняя контора с тем же брендом. Ищем приметы только в имени
    # сайта и в заголовке — в описании они врут. Настоящий барбершоп
    # перечисляет филиалы, среди них «Академическая», и слово
    # «академи» находилось внутри названия станции метро: правильный
    # сайт получал штраф, а школа барберов выигрывала.
    kind_low = (kind or '').lower()
    if not any(w in kind_low for w in CHUZHIE):
        if any(w in h for w in CHUZHIE):
            ochki -= 5
        if any(w in zag for w in CHUZHIE):
            ochki -= 3

    # Место в выдаче: важно, но не решает.
    ochki -= indeks * 0.4
    return ochki


def find_site(names, city, folder_id, api_key, kind=''):
    """Ищет официальный сайт компании по названию.

    names — все известные написания. Требовать совпадения названия в
    заголовке нельзя: в реестре «ФЛАУВАУ», а на сайте написано
    Flowwow, и настоящий сайт отбраковывался.

    kind — род занятий. Без него по запросу «Britva Москва
    официальный сайт» первой выходила школа барберов с тем же
    брендом, а не сам барбершоп.
    """
    if isinstance(names, str):
        names = [names]
    names = [n for n in names if n]
    if not names:
        return ''

    query = ' '.join(x for x in (names[0], kind, city, 'официальный сайт') if x)
    # Ошибку не глотаем: «сайт не нашли» и «поиск не работает» —
    # разные вещи, и вторую надо чинить, а не принимать за ответ.
    docs = raw_search(query, folder_id, api_key)

    svoi, luchshij, luchshie_ochki = [], '', None
    for i, d in enumerate(docs[:10]):
        host = matching.domain_of(d['url'])
        if not host or spravochnik(host):
            continue
        svoi.append(host)
        o = _ochki(i, host, d['title'], d['text'], names, kind)
        if luchshie_ochki is None or o > luchshie_ochki:
            luchshij, luchshie_ochki = host, o

    return _glavnyj(luchshij, svoi)


def _glavnyj(host, vse):
    """Сводит найденный адрес к главному сайту сети.

    У сетей бывают областные поддомены: ryazan.britvabarber.ru,
    spb.britvabarber.ru. Поиск отдаёт их вперемешку с главным, и
    однажды по московскому барбершопу нашёлся рязанский поддомен —
    отчёт вышел про чужой город.

    Сводим к главному, только если он сам встретился в выдаче: гадать
    нельзя, потому что у некоторых компаний сайт и правда живёт на
    поддомене, а у доменов вида contora.spb.ru отрезание части имени
    дало бы вообще чужой сайт.
    """
    if not host:
        return ''
    for drugoj in vse:
        if drugoj != host and host.endswith('.' + drugoj):
            return drugoj
    return host


# Справочники, соцсети и агрегаторы: компания там есть почти всегда,
# но это не её сайт и не её позиция.
AGGREGATORS = (
    # поисковики и карты
    'yandex.', 'ya.ru', 'google.', '2gis.', 'maps.',
    # справочники и отзывы
    'zoon.', 'yell.', 'flamp.', 'orgpage.', 'spr.ru', 'blizko.',
    'otzovik.', 'irecommend.', 'tripadvisor.', 'restoclub.', 'prodoctorov.',
    # соцсети. Именно тут пряталась ошибка: стоял только vk.com, а
    # ВКонтакте давно живёт ещё и на vk.ru — и страница группы
    # становилась «сайтом компании».
    'vk.com', 'vk.ru', 'vk.me', 'ok.ru', 't.me', 'telegram.',
    'instagram.', 'facebook.', 'dzen.ru', 'youtube.', 'pinterest.',
    # маркетплейсы и доски
    'avito.', 'youla.', 'ozon.', 'wildberries.', 'market.', 'aliexpress.',
    # записи и бронирования: у салонов и барбершопов выходят вперёд
    # собственного сайта
    'yclients.', 'dikidi.', 'n-a-p.ru', 'sbereats.', 'delivery-club.',
    # реестры и работа
    'rusprofile.', 'list-org.', 'checko.', 'sbis.ru', 'zachestnyibiznes.',
    'audit-it.', 'hh.ru', 'rabota.', 'superjob.',
)


def spravochnik(host):
    """Справочник, карта, соцсеть или маркетплейс, а не сайт компании.

    Сравнивать простым вхождением подстроки нельзя. В списке есть
    «ya.ru», и по нему в справочники попадал zubfeya.ru — сайт
    детской стоматологии «Зубная фея». Так же терялся бы любой домен,
    внутри которого случайно оказалось чужое имя.

    Поэтому: записи с точкой на конце («yandex.») — это имя одного
    уровня домена, ищем его среди частей. Записи без точки
    («vk.com») — полное имя, годится оно само или его поддомен.
    """
    h = (host or '').lower().strip('.')
    if h.startswith('www.'):
        h = h[4:]
    if not h:
        return False
    chasti = h.split('.')
    for a in AGGREGATORS:
        if a.endswith('.'):
            if a[:-1] in chasti:
                return True
        elif h == a or h.endswith('.' + a):
            return True
    return False


def position_of(query, site, names, folder_id, api_key):
    """На каком месте компания по этому запросу.

    Если известен сайт — ищем его домен. Если нет — ищем упоминание
    названия в заголовке или описании: для компании без сайта это
    единственный доступный признак присутствия.
    """
    docs = raw_search(query, folder_id, api_key)
    site = matching.domain_of(site)

    for i, d in enumerate(docs, 1):
        if site:
            # Поддомен — тоже наш сайт. Яндекс нередко показывает
            # m.сайт.ру или shop.сайт.ру, и по строгому равенству
            # компания выпадала из выдачи, хотя стояла в ней.
            host = matching.domain_of(d['url'])
            if host == site or host.endswith('.' + site):
                return i, d['url']
        else:
            if matching.mentioned_any(d['title'] + ' ' + d['text'], names):
                return i, d['url']
    return None, ''

# ---------------------------------------------------------------------
# Кто ещё работает рядом
#
# Когда в анкете указан не только город, но и конкретный район, мы
# можем не гадать о конкурентах, а просто спросить поиск: «стоматология
# ЮЗАО Москва». Выдача по такому запросу — это и есть список тех, к
# кому клиент уходит, когда его самого не называют.
#
# Дальше эти названия проверяются по ответам нейросетей наравне с
# теми, что клиент вписал сам.

# Слова, по которым видно, что в заголовке не название компании, а
# подпись к списку: «Стоматологии в ЮЗАО — 45 клиник, цены, отзывы».
# Если после вычёркивания таких слов не осталось ничего своего, это
# не компания.
OBSHIE = (
    'цена', 'цены', 'ценам', 'стоимость', 'отзыв', 'отзывы', 'отзывам',
    'рейтинг', 'лучший', 'лучшие', 'лучших', 'топ', 'каталог', 'список',
    'адрес', 'адреса', 'адресам', 'официальный', 'сайт', 'сайты',
    'запись', 'записаться', 'онлайн', 'услуга', 'услуги', 'услуг',
    'недорого', 'дёшево', 'дешево', 'круглосуточно', 'телефон', 'телефоны',
    'акция', 'акции', 'скидка', 'скидки', 'рядом', 'метро', 'район',
    'районе', 'районы', 'округ', 'округе', 'город', 'городе',
    'все', 'всё', 'где', 'как', 'что', 'купить', 'заказать', 'выбрать',
    'обзор', 'сравнение', 'подбор', 'найти', 'поиск', 'бесплатно',
    'отзывов', 'фото', 'карте', 'карта', 'ближайший', 'ближайшие',
    'москва', 'москве', 'спб', 'питер', 'россии', 'года', 'год',
)

# Заголовок режем по этим знакам: дальше идёт приписка поисковика.
RAZDELY = ('—', '–', '|', '·', ':', '»', '/', ' - ', ' — ')


# Слова, с которых заголовок начинается, когда это не компания, а
# подборка: «Цены на имплантацию…», «Рейтинг клиник…». Название так
# не начинается никогда, и одно это правило отсекает почти все
# страницы-списки.
NACHALA = ('цена', 'цены', 'стоимость', 'рейтинг', 'лучший', 'лучшие',
           'лучших', 'топ', 'все', 'всё', 'где', 'как', 'что', 'сколько',
           'каталог', 'список', 'обзор', 'сравнение', 'подбор', 'отзывы')


def _golova(zagolovok):
    """Первая часть заголовка — обычно там и стоит название."""
    t = ' '.join((zagolovok or '').split())
    for znak in RAZDELY:
        if znak in t:
            t = t.split(znak)[0]
    t = t.strip(' .,;"\'')
    # Закрывающая кавычка обрезается вместе с точкой, а открывающая
    # остаётся внутри: «Стоматология «Дента-Люкс». Возвращаем пару.
    t = t.strip('»').strip()
    if t.count('«') > t.count('»'):
        t += '»'
    return t.strip(' .,;')


def _pohozhe_na_nazvanie(golova, kind, mesta):
    """Осталось ли в заголовке хоть одно своё слово.

    Вычёркиваем общие слова, род занятий и названия мест. Если после
    этого ничего не осталось — перед нами подпись к списку, а не
    компания.
    """
    if not (2 <= len(golova) <= 50):
        return False
    slova = golova.lower().replace('«', ' ').replace('»', ' ').split()
    if not slova or len(slova) > 6:
        return False

    # Подборка, а не компания.
    pervoe = slova[0].strip('.,:;()"\'')
    if any(pervoe.startswith(n[:5]) for n in NACHALA):
        return False

    lishnee = set(OBSHIE)
    for istochnik in [kind] + list(mesta or []):
        for w in (istochnik or '').lower().replace(',', ' ').split():
            if len(w) > 2:
                lishnee.add(w)

    for w in slova:
        w = w.strip('.,:;()"\'0123456789')
        if len(w) < 3 or w.isdigit():
            continue
        # Слово считаем своим, если оно не общее и не однокоренное
        # с родом занятий: «стоматология» и «стоматологии» — одно и то же.
        if any(w.startswith(l[:5]) or l.startswith(w[:5]) for l in lishnee):
            continue
        return True
    return False


def sosedi(kind, rajon, gorod, folder_id, api_key, svoi=(), limit=5):
    """Кто работает в этой же нише в указанном районе.

    Возвращает список названий. Ошибку поиска наружу не пускаем:
    соседи — приятное дополнение к отчёту, но ради них ронять всю
    проверку незачем.
    """
    kind = ' '.join((kind or '').split())
    rajon = ' '.join((rajon or '').split())
    if not kind or not rajon:
        return []

    query = ' '.join(x for x in (kind, rajon, gorod) if x)
    try:
        docs = raw_search(query, folder_id, api_key)
    except (SearchError, requests.exceptions.RequestException):
        return []

    mesta = [rajon, gorod]
    out, vzyato = [], set()
    for d in docs[:20]:
        host = matching.domain_of(d['url'])
        if not host or spravochnik(host):
            continue
        imya = _golova(d['title'])
        if not _pohozhe_na_nazvanie(imya, kind, mesta):
            continue
        # Себя в список конкурентов не пишем.
        if svoi and matching.mentioned_any(imya, [x for x in svoi if x]):
            continue
        klyuch = matching.fold(imya)
        if not klyuch or klyuch in vzyato:
            continue
        vzyato.add(klyuch)
        out.append(imya)
        if len(out) >= limit:
            break
    return out
