"""Сбор отчёта и отрисовка картинки."""

import os

from PIL import Image, ImageDraw, ImageFont

# Цвета «ГенИИ»
MINT = (129, 216, 208)
SKY = (166, 214, 230)
LAV = (198, 184, 226)
BLUSH = (240, 204, 210)
TEXT = (255, 255, 255)

# Два оформления одного и того же отчёта: заявка приходит либо с
# genii-ai.ru, либо с prompter-ai.moscow, и клиенту уходит картинка
# того сайта, где он оставил заявку. Цифры в обеих одинаковые —
# отличаются только цвета, название и подпись внизу.
BRANDS = {
    'genii': {
        'kicker': 'ГенИИ · проверка в нейровыдаче',
        'we': '«ГенИИ»',      # подставляется в «Где вы будете с …»
        'foot': 'genii-ai.ru · +7 906 758-77-77',
        'bg': (10, 10, 12),
        'card': (26, 26, 29),
        'line': (58, 54, 70),
        'track': (42, 42, 48),
        'c1': MINT,
        'c2': SKY,
        'c3': LAV,
        'now': BLUSH,          # чем закрашено «сейчас»
        'band': (38, 74, 71),  # куда дорастём — тот же мятный, но приглушённый
        'box': (58, 110, 106),
        'muted': (170, 166, 182),
        'warn': BLUSH,
        'mid': SKY,
        'good': MINT,
    },
    'prompter': {
        'kicker': 'Промптер · проверка в нейровыдаче',
        'we': '«Промптером»',
        'foot': 'prompter-ai.moscow · +7 906 758-77-77',
        'bg': (10, 10, 14),
        'card': (21, 35, 67),
        'line': (46, 66, 110),
        'track': (30, 44, 78),
        'c1': (127, 196, 255),
        'c2': (214, 228, 255),
        'c3': (61, 107, 255),
        'now': (127, 196, 255),
        'band': (34, 60, 112),
        'box': (61, 107, 255),
        'muted': (159, 182, 220),
        'warn': BLUSH,
        'mid': (214, 228, 255),
        'good': (127, 196, 255),
    },
}

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


def _mix(a, b, t):
    """Цвет между a и b: t=0 — это a, t=1 — это b. Нужен для
    приглушённых подписей: прозрачности в RGB-картинке нет."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


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
        'search_broken': '',
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
            # Закрывающая кавычка обрезается вместе с точкой, а
            # открывающая остаётся внутри строки: «ООО «Главстрой».
            # Возвращаем пару на место.
            if cand.count('«') > cand.count('»'):
                cand += '»'
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


def _verdict(data):
    """Одна фраза, с которой менеджер начинает разговор, и её тон."""
    named, total = data['ai_named'], data['ai_total']
    if total == 0:
        return 'Нейросети опросить не удалось', 'warn'
    if named == 0:
        return 'Нейросети не называют компанию ни разу', 'warn'
    share = named / total
    if share < 0.3:
        return 'Компанию называют редко', 'warn'
    if share < 0.6:
        return 'Компанию называют иногда', 'mid'
    if share < 0.85:
        return 'Компанию называют часто', 'good'
    return 'Компанию называют почти всегда', 'good'


def verdict(data, brand='genii'):
    text, tone = _verdict(data)
    return text, BRANDS.get(brand, BRANDS['genii'])[tone]


# Отрасли, где на общий вопрос нейросеть отвечает именами федеральных
# компаний: ПИК и «Главстрой» в стройке, «Леруа Мерлен» в товарах для
# дома, «Детский мир» в детских. Небольшую компанию там не назовут, и
# менеджеру это надо объяснить клиенту до того, как тот спросит сам.
# Темы берутся из queries.TRIGGERS.
CROWDED = {
    'строительство': 'В строительстве на общий вопрос нейросеть называет крупных '
                     'застройщиков. Мы поднимаем вас в вашей теме, а не в отрасли целиком.',
    'товары для дома': 'В товарах для дома на общий вопрос нейросеть называет сети. '
                       'Мы поднимаем вас в вашей теме, а не в отрасли целиком.',
    'детские товары': 'В детских товарах на общий вопрос нейросеть называет сети. '
                      'Мы поднимаем вас в вашей теме, а не в отрасли целиком.',
    'интернет-магазин': 'На общий вопрос нейросеть называет маркетплейсы. Мы поднимаем '
                        'вас в вашей теме, а не в торговле целиком.',
}

HOLD = 0.85  # выше этого место не поднимают, а удерживают


def promise(data):
    """Что меняется с нами. Главная строчка блока.

    Чисел здесь нет намеренно. Обещать «через три месяца будет столько-то
    ответов» — значит называть цифру, за которую потом спросят, и она
    всё равно разная в каждой отрасли. Обещаем направление: компания
    начинает попадать в списки нейросети и подниматься в них.
    """
    total = data['ai_total']
    if not total:
        return None

    share = data['ai_named'] / total
    if share >= HOLD:
        return {
            'hold': True,
            'head': 'Это место надо удержать',
            'lead': 'Вас называют почти в каждом ответе — задача не потерять это место.',
            'body': 'Конкуренты публикуются каждую неделю. Через полгода без публикаций '
                    'нейросети начинают называть их вместо вас.',
        }

    if data['ai_named'] == 0:
        lead = 'Вы начнёте появляться в списках, которые нейросеть выдаёт вашему клиенту.'
    else:
        lead = 'Вы будете подниматься выше в списках, которые нейросеть выдаёт вашему клиенту.'

    return {
        'hold': False,
        'head': '',   # подставляется с названием сайта при отрисовке
        'lead': lead,
        'body': 'Публикации пять дней в неделю на шести площадках. Нейросети начинают '
                'опираться на них, отвечая на запросы клиентов. Первые сдвиги видно '
                'на втором месяце работы.',
    }


def why_line(company):
    """Почему в этой отрасли компанию не называют. Пустая строка —
    отрасль обычная, объяснять нечего."""
    from . import queries

    topic = (queries.topic_of(company.get('industry'))
             or queries.topic_of(company.get('kind')))
    return CROWDED.get(topic, '')


def search_line(data):
    """Строчка про обычный поиск — про направление, не про место."""
    if data.get('search_broken') or not data.get('search_total'):
        return ''
    best = data.get('search_best')
    if not best:
        return 'В поиске Яндекса вас пока нет в топ-20 — поднимаем и там.'
    if best > 10:
        return 'В поиске Яндекса вы на %d-м месте — поднимаем выше.' % best
    if best > 3:
        return 'В поиске Яндекса вы на %d-м месте — подтягиваем ближе к первым.' % best
    return 'В поиске Яндекса вы наверху — эту позицию удерживаем.'


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


def draw_png(data, path, brand='genii'):
    """Рисует картинку отчёта. Ширина 1200 — читается и в телеграме,
    и при пересылке клиенту.

    brand — 'genii' или 'prompter': та же проверка в цветах того
    сайта, с которого пришла заявка.
    """
    b = BRANDS.get(brand, BRANDS['genii'])
    BG, CARD, LINE, MUTED = b['bg'], b['card'], b['line'], b['muted']

    W, PAD = 1200, 56
    f_h1 = _font(46, True)
    f_h2 = _font(27, True)
    f_big = _font(72, True)
    f_t = _font(22)
    f_s = _font(19)
    f_xs = _font(17)

    c = data['company']
    head, tone = _verdict(data)
    head_color = b[tone]
    rivals = data['rivals']

    # Рисуем с запасом по высоте и в конце обрезаем по последней
    # строке. Считать высоту заранее — значит держать в двух местах
    # одну и ту же раскладку: стоит добавить строку, и подпись внизу
    # наезжает на текст.
    H = 2200
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    y = PAD
    d.text((PAD, y), b['kicker'], font=f_s, fill=b['c1'])
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
           font=f_s, fill=b['c2'] if data['site'] else MUTED)
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
         'ответов нейросетей, где вас назвали', b['c1']),
        (('%d-е' % data['ai_best_position']) if data['ai_best_position'] else '—',
         'лучшее место в списке нейросети', b['c2']),
        (('%d-е' % data['search_best']) if data['search_best']
         else ('не смотрели' if data.get('search_broken') else 'нет в топ-20'),
         'лучшее место в поиске Яндекса', b['c3']),
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

    # --- Что будет с нами ---
    # Ради этого блока отчёт и показывают клиенту: одни цифры «как
    # сейчас» ничего не продают.
    p = promise(data)
    if p:
        y = _draw_promise(d, data, p, b, y + 16, W, PAD, f_h2, f_xs)

    d.text((PAD, y), b['foot'], font=f_xs, fill=MUTED)
    y += 26

    y += 26
    img = img.crop((0, 0, W, min(H, y + PAD - 20)))
    img.save(path, 'PNG')
    return path


def _steps(d, b, right, base, n=5, flat=False):
    """Столбики лесенкой — знак роста вместо полоски с долями.

    Полоска показывала, сколько ответов будет через три месяца, и это
    было обещание в числах. Лесенка говорит то же самое про
    направление и ничего не обещает в цифрах.

    flat — столбики вровень: там, где речь про удержание места,
    лесенка вверх противоречила бы тексту.
    """
    w, gap, top_h = 16, 10, 46
    total_w = n * w + (n - 1) * gap
    x = right - total_w
    for i in range(n):
        k = i / float(n - 1)
        h = int(top_h * (0.78 if flat else 0.22 + 0.78 * k))
        col = b['c1'] if flat else _mix(b['band'], b['c1'], k)
        d.rounded_rectangle([x, base - h, x + w, base], radius=5, fill=col)
        x += w + gap


def _draw_promise(d, data, p, b, top, W, PAD, f_h2, f_xs):
    """Коробка «что изменится с нами». Высоту считаем по тексту:
    строк бывает от трёх до шести, и рамка должна их вместить."""
    pad_x = PAD + 24
    box_w = W - PAD * 2 - 48

    head = p['head'] or 'Что изменится с %s' % b['we']

    lines = []
    lines += [(l, b['c1']) for l in _wrap(d, p['lead'], f_xs, box_w)[:2]]
    why = why_line(data['company'])
    if why:
        lines += [(l, b['c2']) for l in _wrap(d, why, f_xs, box_w)[:2]]
    s_line = search_line(data)
    if s_line:
        lines += [(l, b['muted']) for l in _wrap(d, s_line, f_xs, box_w)[:2]]
    lines += [(l, b['muted']) for l in _wrap(d, p['body'], f_xs, box_w)[:3]]

    height = 96 + len(lines) * 24
    d.rounded_rectangle([PAD, top, W - PAD, top + height], radius=20,
                        fill=b['card'], outline=b['box'])
    d.text((pad_x, top + 24), head, font=f_h2, fill=b['c1'])
    _steps(d, b, W - PAD - 24, top + 58, flat=p['hold'])

    ty = top + 82
    for line, col in lines:
        d.text((pad_x, ty), line, font=f_xs, fill=col)
        ty += 24

    return top + height + 26
