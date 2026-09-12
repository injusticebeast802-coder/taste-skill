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


def find_site(names, city, folder_id, api_key):
    """Ищет официальный сайт компании по названию.

    Берём первую ссылку, которая не ведёт на справочник или соцсеть:
    там компания тоже есть, но это не её сайт.

    names — все известные написания. Требовать совпадения названия в
    заголовке нельзя: в реестре «ФЛАУВАУ», а на сайте написано
    Flowwow, и настоящий сайт отбраковывался. Поэтому имя проверяем,
    но если ни одна ссылка не подошла — берём первую подходящую
    не-справочную: по запросу с названием и словами «официальный
    сайт» она почти всегда и есть искомая.
    """
    if isinstance(names, str):
        names = [names]
    names = [n for n in names if n]
    if not names:
        return ''

    query = ('%s %s официальный сайт' % (names[0], city)).strip()
    # Ошибку не глотаем: «сайт не нашли» и «поиск не работает» —
    # разные вещи, и вторую надо чинить, а не принимать за ответ.
    docs = raw_search(query, folder_id, api_key)

    fallback = ''
    for d in docs[:10]:
        host = matching.domain_of(d['url'])
        if not host or any(bad in host for bad in AGGREGATORS):
            continue
        if not fallback:
            fallback = host
        if matching.mentioned_any(d['title'] + ' ' + d['text'], names):
            return host
    return fallback


# Справочники, соцсети и агрегаторы: компания там есть почти всегда,
# но это не её сайт и не её позиция.
AGGREGATORS = (
    'yandex.', 'ya.ru', 'google.', '2gis.', 'zoon.', 'yell.', 'flamp.',
    'vk.com', 'ok.ru', 't.me', 'telegram.', 'instagram.', 'facebook.',
    'avito.', 'youla.', 'ozon.', 'wildberries.', 'dzen.ru', 'rusprofile.',
    'list-org.', 'checko.', 'sbis.ru', 'zachestnyibiznes.', 'prodoctorov.',
    'otzovik.', 'irecommend.', 'hh.ru', 'rabota.',
)


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
            if matching.domain_of(d['url']) == site:
                return i, d['url']
        else:
            if matching.mentioned_any(d['title'] + ' ' + d['text'], names):
                return i, d['url']
    return None, ''
