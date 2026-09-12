"""Сбор отчёта и отрисовка картинки."""

import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

# Цвета сайта: картинка должна выглядеть как продолжение genii-ai.ru
BG = (10, 10, 12)
CARD = (26, 26, 29)
LINE = (58, 54, 70)
TEXT = (255, 255, 255)
MUTED = (170, 166, 182)
MINT = (129, 216, 208)
SKY = (166, 214, 230)
LAV = (198, 184, 226)
BLUSH = (240, 204, 210)

# Шрифт ищем среди тех, что есть в системе. Первый найденный и берём:
# на сервере обычно DejaVu, на компьютере менеджера — Arial.
FONT_CANDIDATES = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    'C:/Windows/Fonts/segoeui.ttf',
    'C:/Windows/Fonts/arial.ttf',
    '/System/Library/Fonts/Supplemental/Arial.ttf',
]
FONT_BOLD_CANDIDATES = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    'C:/Windows/Fonts/segoeuib.ttf',
    'C:/Windows/Fonts/arialbd.ttf',
    '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
]


def _font(size, bold=False):
    for path in (FONT_BOLD_CANDIDATES if bold else FONT_CANDIDATES):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def build(company, site, ai_results, search_results):
    """Сводит сырые ответы в понятные числа.

    ai_results: [{'engine','query','mentioned','position','error'}]
    search_results: [{'query','position','url','error'}]
    """
    ok = [r for r in ai_results if not r.get('error')]
    named = [r for r in ok if r.get('mentioned')]

    engines = {}
    for r in ok:
        e = engines.setdefault(r['engine'], {'total': 0, 'named': 0})
        e['total'] += 1
        if r.get('mentioned'):
            e['named'] += 1

    positions = [r['position'] for r in named if r.get('position')]

    s_ok = [r for r in search_results if not r.get('error')]
    s_found = [r for r in s_ok if r.get('position')]
    s_positions = [r['position'] for r in s_found]

    return {
        'company': company,
        'site': site,
        'ai_total': len(ok),
        'ai_named': len(named),
        'ai_by_engine': engines,
        'ai_best_position': min(positions) if positions else None,
        'search_total': len(s_ok),
        'search_found': len(s_found),
        'search_best': min(s_positions) if s_positions else None,
        'ai_results': ai_results,
        'search_results': search_results,
        'rivals': _rivals(ai_results, company.get('names') or [company.get('name', '')]),
    }


# Слова, по которым видно, что в нумерованной строке не название
# компании, а совет или пояснение. Без этого в «кого называют вместо
# вас» попадали «Рекомендации друзей и знакомых» и «Вы можете
# использовать поисковые системы».
NOT_A_NAME = (
    'вы ', 'вам ', 'ваш', 'если ', 'можно ', 'можете', 'стоит ', 'нужно ',
    'рекоменд', 'поиск', 'отзыв', 'уточн', 'обратит', 'посмотр', 'спрос',
    'департамент', 'министерств', 'портал', 'справочник', 'каталог',
    'официальный сайт', 'сайт ', 'приложени', 'сервис', 'карт',
)


def _looks_like_name(cand):
    """Название компании — короткое и без глаголов.

    Нейросеть в нумерованных списках даёт и советы, и пояснения:
    отличаем по длине и по словам-приметам.
    """
    c = cand.strip()
    if len(c) < 3 or len(c) > 42:
        return False
    if len(c.split()) > 4:
        return False
    low = c.lower()
    return not any(w in low for w in NOT_A_NAME)


def _rivals(ai_results, own_names):
    """Кого нейросети называют вместо компании.

    Берём строки нумерованных списков: в них нейросеть и перечисляет
    компании. Это не точный разбор, а подсказка менеджеру, о ком
    говорить с клиентом.
    """
    import re
    from . import matching

    counts = {}
    for r in ai_results:
        for line in (r.get('answer') or '').splitlines():
            # Разделяем только по длинному тире и двоеточию: обычный
            # дефис — часть названия, «Дента-Люкс» по нему рвать нельзя.
            m = re.match(r'^\s*\d+[.)]\s*([^—–:\n]{3,60})', line)
            if not m:
                continue
            cand = m.group(1).strip(' *«»"\'.,')
            if not _looks_like_name(cand):
                continue
            if matching.mentioned_any(cand, own_names):
                continue
            key = matching.fold(cand)
            if key:
                counts[key] = counts.get(key, [0, cand])
                counts[key][0] += 1
                counts[key][1] = cand
    top = sorted(counts.values(), key=lambda x: -x[0])[:5]
    return [(name, n) for n, name in top]


def verdict(data):
    """Одна фраза, с которой менеджер начинает разговор."""
    named, total = data['ai_named'], data['ai_total']
    if total == 0:
        return 'Нейросети опросить не удалось', BLUSH
    if named == 0:
        return 'Нейросети не называют компанию ни разу', BLUSH
    share = named / total
    if share < 0.3:
        return 'Компанию называют редко', BLUSH
    if share < 0.6:
        return 'Компанию называют иногда', SKY
    if share < 0.85:
        return 'Компанию называют часто', MINT
    return 'Компанию называют почти всегда', MINT


def _wrap(draw, text, font, width):
    words, lines, cur = (text or '').split(), [], ''
    for w in words:
        probe = (cur + ' ' + w).strip()
        if draw.textlength(probe, font=font) <= width:
            cur = probe
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_png(data, path):
    """Рисует картинку отчёта. Ширина 1200 — читается и в телеграме,
    и при пересылке клиенту."""
    W, PAD = 1200, 56
    f_h1 = _font(46, True)
    f_h2 = _font(27, True)
    f_big = _font(72, True)
    f_t = _font(22)
    f_s = _font(19)
    f_xs = _font(17)

    c = data['company']
    head, head_color = verdict(data)
    rivals = data['rivals']

    # Рисуем с запасом по высоте и в конце обрезаем по последней
    # строке. Считать высоту заранее — значит держать в двух местах
    # одну и ту же раскладку: стоит добавить строку, и подпись внизу
    # наезжает на текст.
    H = 2200
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    y = PAD
    d.text((PAD, y), 'ГенИИ · проверка в нейровыдаче', font=f_s, fill=MINT)
    y += 40

    for line in _wrap(d, c.get('full_name') or c.get('name'), f_h1, W - PAD * 2)[:2]:
        d.text((PAD, y), line, font=f_h1, fill=TEXT)
        y += 54

    sub = 'ИНН %s' % c.get('inn', '')
    if c.get('city'):
        sub += ' · %s' % c['city']
    if c.get('industry'):
        sub += ' · %s' % c['industry']
    d.text((PAD, y), sub, font=f_s, fill=MUTED)
    y += 30
    d.text((PAD, y), ('Сайт: ' + data['site']) if data['site'] else 'Сайта не нашли — проверяли по названию',
           font=f_s, fill=SKY if data['site'] else MUTED)
    y += 46

    # Главная строка
    d.rectangle([PAD, y, W - PAD, y + 2], fill=LINE)
    y += 30
    for line in _wrap(d, head, f_h2, W - PAD * 2):
        d.text((PAD, y), line, font=f_h2, fill=head_color)
        y += 36
    y += 14

    # Три числа в ряд
    cards = [
        ('%d из %d' % (data['ai_named'], data['ai_total']),
         'ответов нейросетей, где вас назвали', MINT),
        (('%d-е' % data['ai_best_position']) if data['ai_best_position'] else '—',
         'лучшее место в списке нейросети', SKY),
        (('%d-е' % data['search_best']) if data['search_best'] else 'нет в топ-20',
         'лучшее место в поиске Яндекса', LAV),
    ]
    cw = (W - PAD * 2 - 24 * 2) // 3
    for i, (big, cap, col) in enumerate(cards):
        x = PAD + i * (cw + 24)
        d.rounded_rectangle([x, y, x + cw, y + 150], radius=18, fill=CARD, outline=LINE)
        d.text((x + 22, y + 26), big, font=f_big if len(big) < 8 else _font(44, True), fill=col)
        ty = y + 104
        for line in _wrap(d, cap, f_xs, cw - 44)[:2]:
            d.text((x + 22, ty), line, font=f_xs, fill=MUTED)
            ty += 22
    y += 150 + 34

    # По нейросетям отдельно
    d.text((PAD, y), 'По нейросетям', font=f_h2, fill=TEXT)
    y += 40
    if data['ai_by_engine']:
        for name, e in data['ai_by_engine'].items():
            d.text((PAD, y), '%s — назвали в %d из %d ответов' % (name, e['named'], e['total']),
                   font=f_t, fill=MUTED if not e['named'] else TEXT)
            y += 32
    else:
        d.text((PAD, y), 'Ответов нет', font=f_t, fill=MUTED)
        y += 32
    y += 12

    if rivals:
        d.text((PAD, y), 'Кого называют вместо вас', font=f_h2, fill=TEXT)
        y += 40
        for name, n in rivals:
            d.text((PAD, y), '· %s — в %d ответах' % (name[:60], n), font=f_t, fill=MUTED)
            y += 34

    y += 18
    d.text((PAD, y), 'genii-ai.ru · +7 906 758-77-77', font=f_xs, fill=MUTED)
    y += 26

    img = img.crop((0, 0, W, min(H, y + PAD - 10)))
    img.save(path, 'PNG')
    return path
