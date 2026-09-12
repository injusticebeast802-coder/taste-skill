"""Полный проход: ИНН -> отчёт и картинка."""

import os
import time

from . import ai_gigachat, ai_yandex, company as company_mod, inn as inn_mod
from . import matching, queries, report, search_yandex


class RunError(Exception):
    pass


def analyze(raw_inn, cfg, progress=None):
    """Собирает отчёт. progress — функция, которой шлём строки о ходе:
    проверка занимает минуту-две, и без них бот кажется зависшим."""

    def say(msg):
        if progress:
            try:
                progress(msg)
            except Exception:
                pass

    digits = inn_mod.normalize(raw_inn)
    problem = inn_mod.explain(digits)
    if problem:
        raise RunError(problem)

    say('Ищу компанию в справочнике…')
    c = company_mod.lookup(digits, cfg['dadata_token'])
    c['inn'] = digits

    if c.get('status') and c['status'] != 'ACTIVE':
        say('Внимание: по справочнику компания не действующая.')

    # --- сайт ---
    site = ''
    if cfg.get('yandex_folder_id') and cfg.get('yandex_search_key'):
        say('Ищу сайт компании…')
        site = search_yandex.find_site(c['name'], c.get('city', ''),
                                       cfg['yandex_folder_id'], cfg['yandex_search_key'])

    # --- вопросы нейросетям ---
    qs = queries.build(c, limit=int(cfg.get('questions', 12)))
    if not qs:
        raise RunError('Не смог понять род занятий компании — по ОКВЭД %s ничего не подобралось. '
                       'Проверьте вручную.' % c.get('okved'))

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
                item['mentioned'] = matching.mentioned(item['answer'], c['name'])
                if not item['mentioned'] and site:
                    item['mentioned'] = matching.domain_of(site) in item['answer'].lower()
                item['position'] = matching.position(item['answer'], c['name'])
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
                    q, site, c['name'], cfg['yandex_folder_id'], cfg['yandex_search_key'])
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

    errs = [r['error'] for r in data['ai_results'] if r.get('error')]
    if errs:
        lines.append('')
        lines.append('Часть вопросов не прошла (%d из %d): %s' % (
            len(errs), len(data['ai_results']), errs[0][:120]))
    return '\n'.join(lines)
