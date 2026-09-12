"""Карточка компании по ИНН — справочник DaData.

Нужны название, город и род занятий: из них составляются запросы,
которые потом задаются нейросетям. Бесплатного лимита DaData
(10 000 обращений в сутки) хватает с большим запасом.
"""

import requests

URL = 'https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party'

# Точные коды: они важнее класса, потому что внутри одного класса
# бывают совсем разные занятия.
OKVED_EXACT = {
    '86.23': 'стоматология',
    '47.76': 'цветы',
    '47.91': 'интернет-магазин',
    '56.10': 'ресторан, кафе и доставка еды',
    '56.21': 'доставка еды',
    '43.3': 'ремонт и отделка',
    '45.20': 'автосервис',
    '96.02': 'салон красоты',
    '85.41': 'обучение',
    '93.13': 'спорт и фитнес',
    '49.41': 'грузоперевозки',
    '68.31': 'недвижимость',
}

# Отрасль по коду ОКВЭД. Справочник огромный, поэтому берём только
# первые две цифры — класс. Этого достаточно, чтобы понять, о чём
# спрашивать нейросеть. Чего нет в списке — разбирается по названию
# вида деятельности, которое DaData отдаёт словами.
OKVED_CLASS = {
    '10': 'производство продуктов питания',
    '41': 'строительство',
    '42': 'строительство',
    '43': 'ремонт и отделка',
    '45': 'автосервис',
    '46': 'оптовая торговля',
    '47': 'розничный магазин',
    '49': 'перевозки',
    '52': 'склад и логистика',
    '55': 'гостиница',
    '56': 'ресторан, кафе и доставка еды',
    '62': 'разработка программ',
    '68': 'недвижимость',
    '69': 'юридические услуги',
    '70': 'консалтинг',
    '73': 'реклама и маркетинг',
    '79': 'туризм',
    '85': 'обучение',
    '86': 'медицина',
    '88': 'социальные услуги',
    '93': 'спорт и фитнес',
    '95': 'ремонт техники',
    '96': 'бытовые услуги',
}


class CompanyError(Exception):
    pass


def _clean_name(name):
    """Убирает форму собственности и кавычки: нейросеть и поиск знают
    компанию по имени, а не по «Общество с ограниченной…»."""
    if not name:
        return ''
    s = name
    for junk in ('Общество с ограниченной ответственностью', 'Акционерное общество',
                 'Публичное акционерное общество', 'Индивидуальный предприниматель',
                 'ООО', 'АО', 'ПАО', 'ЗАО', 'ИП', 'НКО', 'ОАО'):
        s = s.replace(junk, ' ')
    return s.replace('"', ' ').replace('«', ' ').replace('»', ' ').strip(' ,-')


def lookup(inn_digits, token, timeout=15):
    """Возвращает словарь с полями name, full_name, city, industry, kind."""
    r = requests.post(
        URL,
        json={'query': inn_digits},
        headers={'Content-Type': 'application/json',
                 'Accept': 'application/json',
                 'Authorization': 'Token ' + token},
        timeout=timeout,
    )
    if r.status_code == 403:
        raise CompanyError('Справочник DaData не принял ключ. Проверьте dadata_token в настройках.')
    if r.status_code != 200:
        raise CompanyError('Справочник DaData ответил ошибкой %d.' % r.status_code)

    items = (r.json() or {}).get('suggestions') or []
    if not items:
        raise CompanyError('По этому ИНН в справочнике ничего нет. Возможно, компания ликвидирована.')

    return parse(items[0])


def parse(item):
    """Разбор ответа вынесен отдельно, чтобы проверять его без сети."""
    data = item.get('data') or {}
    name_block = data.get('name') or {}

    full_name = name_block.get('short_with_opf') or name_block.get('full_with_opf') or item.get('value') or ''
    short = _clean_name(name_block.get('short') or name_block.get('short_with_opf') or item.get('value'))

    address = (data.get('address') or {}).get('data') or {}
    city = address.get('city') or address.get('settlement') or address.get('region') or ''

    okved = str(data.get('okved') or '')
    kind = ''
    for o in (data.get('okveds') or []):
        if o.get('main') and o.get('name'):
            kind = o['name']
            break

    # Сначала точные коды, потом класс из первых двух цифр: класс 47
    # это «розничная торговля» вообще, а 47.76 — именно цветы, и
    # спрашивать надо про цветы, а не про абстрактный магазин.
    industry = ''
    for code, name in OKVED_EXACT.items():
        if okved.startswith(code):
            industry = name
            break
    if not industry:
        industry = OKVED_CLASS.get(okved.split('.')[0], '')
    if not industry:
        industry = kind

    return {
        'name': short or full_name,
        'full_name': full_name,
        'city': city,
        'okved': okved,
        'kind': kind,
        'industry': industry,
        'status': ((data.get('state') or {}).get('status') or ''),
    }
