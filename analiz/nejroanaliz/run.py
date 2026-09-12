"""Полный проход: ИНН -> отчёт и картинка."""

import os
import time

from . import ai_gigachat, ai_yandex, company as company_mod, inn as inn_mod
from . import matching, queries, report, search_yandex


class RunError(Exception):
    pass


def parse_request(raw):
    """Разбирает присланное: ИНН, а за ним — необязательные уточнения.

        7707083893
        7707083893 Flowwow
        7707083893 Flowwow, доставка цветов

    Уточнения нужны, потому что в реестре компания записана
    по-русски — «ФЛАУВАУ», — а нейросети и поиск знают бренд
    латиницей: Flowwow. Совпадений по реестровому имени не будет
    никогда, и проверка покажет ноль на пустом месте.
    """
    text = str(raw or '').strip()
    digits = ''
    for ch in text:
        if ch.isdigit():
            digits += ch
        elif digits:
            break

    tail = text[text.find(digits) + len(digits):].strip(' ,;:-') if digits else text

    brand, kind = '', ''
    if tail:
        parts = [p.strip() for p in tail.split(',', 1)]
        brand = parts[0]
        if len(parts) > 1:
            kind = parts[1]
    return digits, brand, kind


def analyze(raw_inn, cfg, progress=None):
    """Собирает отчёт. progress — функция, которой шлём строки о ходе:
    проверка занимает минуту-две, и без них бот кажется зависшим."""

    def say(msg):
        if progress:
            try:
                progress(msg)
            except Exception:
                pass

    digits, brand, kind_override = parse_request(raw_inn)
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

    if brand:
        c['brand'] = brand
    if kind_override:
        c['industry'] = kind_override
        c['kind'] = kind_override

    # Все написания, под которыми компанию могут назвать.
    c['names'] = [n for n in (c.get('brand'), c.get('name')) if n]

    if c.get('status') and c['status'] != 'ACTIVE':
        say('Внимание: по справочнику компания не действующая.')

    say('Компания: %s · %s · %s' % (c.get('full_name') or c.get('name'),
                                    c.get('city') or 'город не указан',
                                    c.get('industry') or 'род занятий не определён'))

    # --- сайт ---
    site = ''
    if cfg.get('yandex_folder_id') and cfg.get('yandex_search_key'):
        say('Ищу сайт компании…')
        site = search_yandex.find_site(c['names'], c.get('city', ''),
                                       cfg['yandex_folder_id'], cfg['yandex_search_key'])
        if site:
            # Домен — ещё одно написание бренда: flowwow.com даёт
            # «flowwow», и его нейросети называют чаще реестрового имени.
            word = site.split('.')[0]
            if len(word) > 3 and word not in ('www', 'shop', 'site'):
                c['names'].append(word)
            say('Сайт: %s' % site)
        else:
            say('Сайт не нашли — дальше проверяю по названию.')

    # --- вопросы нейросетям ---
    qs = queries.build(c, limit=int(cfg.get('questions', 12)))
    if not qs:
        raise RunError('Не понял род занятий компании: в справочнике ОКВЭД %s, '
                       'а по нему тему запроса не составить.\n\n'
                       'Пришлите так: %s Название, чем занимается\n'
                       'Например: %s Flowwow, доставка цветов'
                       % (c.get('okved') or '—', digits, digits))

    say('Спрашиваю про: %s' % qs[0])

    engines = []
    if cfg.get('yandex_api_key') and cfg.get('yandex_folder_id'):
        engines.append(('YandexGPT', lambda q: ai_yandex.ask(
            q, cfg['yandex_folder_id'], cfg['yandex_api_key'], cfg.get('yandex_model', 'yandexgpt-lite'))))
    if cfg.get('gigachat_auth_key'):
        engines.append(('GigaChat', lambda q: ai_gigachat.ask(
            q, cfg['gigachat_auth_key'], cfg.get('gigachat_scope', 'GIGACHAT_API_PERS'),
            verify=cfg.get('gigachat_verify', True))))
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
                item['answer'] = ask(q)
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
    if cfg.get('yandex_folder_id') and cfg.get('yandex_search_key'):
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

    out_dir = cfg.get('out_dir', 'otchety')
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, 'otchet-%s-%s.png' % (digits, time.strftime('%Y%m%d-%H%M')))
    report.draw_png(data, png)
    data['png'] = png
    return data


def as_text(data):
    """Короткая выжимка текстом — идёт подписью к картинке."""
    c = data['company']
    head = report.verdict(data)[0]
    lines = [
        '%s' % (c.get('full_name') or c.get('name')),
        'ИНН %s · %s · %s' % (c.get('inn', ''), c.get('city') or '—', c.get('industry') or '—'),
        'Сайт: %s' % (data['site'] or 'не нашли, проверяли по названию'),
        '',
        head + '.',
        'Нейросети назвали компанию в %d ответах из %d.' % (data['ai_named'], data['ai_total']),
    ]
    if data['ai_best_position']:
        lines.append('Лучшее место в списке нейросети — %d-е.' % data['ai_best_position'])
    if data['search_best']:
        lines.append('В поиске Яндекса лучшее место — %d-е.' % data['search_best'])
    else:
        lines.append('В поиске Яндекса в первой двадцатке не нашли.')
    if data['rivals']:
        lines.append('Чаще называют: ' + ', '.join(n for n, _ in data['rivals'][:3]) + '.')

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
