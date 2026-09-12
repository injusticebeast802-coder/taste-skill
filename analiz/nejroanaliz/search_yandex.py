"""Обычный поиск Яндекса через сервис XML.

Нужен для двух вещей: найти сайт компании по названию и посмотреть,
на каком месте он стоит по запросам ниши. Если сайта нет — считаем
упоминания названия в заголовках и описаниях найденных страниц.
"""

import re
import xml.etree.ElementTree as ET

import requests

from . import matching

URL = 'https://yandex.ru/search/xml'
# 20 результатов на страницу: дальше второй десятки место уже не имеет
# смысла — туда не доходят.
GROUPBY = 'attr=d.mode=deep.groups-on-page=20.docs-in-group=1'


class SearchError(Exception):
    pass


def _text(node):
    """Текст узла вместе с вложенными <hlword> — их Яндекс ставит
    вокруг найденных слов, и без них фраза рвётся."""
    return ''.join(node.itertext()) if node is not None else ''


def raw_search(query, folder_id, api_key, timeout=20):
    """Возвращает список найденного: адрес, заголовок, описание."""
    r = requests.get(
        URL,
        params={'folderid': folder_id, 'apikey': api_key, 'query': query,
                'l10n': 'ru', 'sortby': 'rlv', 'filter': 'none', 'groupby': GROUPBY},
        timeout=timeout,
    )
    if r.status_code != 200:
        raise SearchError('Поиск Яндекса ответил ошибкой %d.' % r.status_code)

    try:
        root = ET.fromstring(r.content)
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


def find_site(company_name, city, folder_id, api_key):
    """Ищет официальный сайт компании по названию.

    Берём первую ссылку, которая не ведёт на справочник или соцсеть:
    там компания тоже есть, но это не её сайт.
    """
    query = ('%s %s официальный сайт' % (company_name, city)).strip()
    try:
        docs = raw_search(query, folder_id, api_key)
    except SearchError:
        return ''

    for d in docs[:10]:
        host = matching.domain_of(d['url'])
        if not host or any(bad in host for bad in AGGREGATORS):
            continue
        # Название должно встречаться в заголовке — иначе это чужой сайт
        if matching.mentioned(d['title'] + ' ' + d['text'], company_name):
            return host
    return ''


# Справочники, соцсети и агрегаторы: компания там есть почти всегда,
# но это не её сайт и не её позиция.
AGGREGATORS = (
    'yandex.', 'ya.ru', 'google.', '2gis.', 'zoon.', 'yell.', 'flamp.',
    'vk.com', 'ok.ru', 't.me', 'telegram.', 'instagram.', 'facebook.',
    'avito.', 'youla.', 'ozon.', 'wildberries.', 'dzen.ru', 'rusprofile.',
    'list-org.', 'checko.', 'sbis.ru', 'zachestnyibiznes.', 'prodoctorov.',
    'otzovik.', 'irecommend.', 'hh.ru', 'rabota.',
)


def position_of(query, site, company_name, folder_id, api_key):
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
            if matching.mentioned(d['title'] + ' ' + d['text'], company_name):
                return i, d['url']
    return None, ''
