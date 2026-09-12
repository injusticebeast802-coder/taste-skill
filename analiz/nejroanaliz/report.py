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


# Ориентиры роста за три месяца работы. Читать так: «если сейчас
# нейросети называют компанию не чаще, чем в 15% ответов, то через
# три месяца — примерно в 40–60%». Чем хуже дела сейчас, тем больше
# прибавка: с нуля расти проще всего, а тому, кого и так называют в
# каждом втором ответе, каждый следующий ответ даётся тяжелее.
# Это ориентир по нашим проектам, а не обещание, и так и подписано
# на картинке.
STEPS = (
    # доля сейчас от | доля через 3 месяца: от, до
    (0.00, 0.35, 0.55),
    (0.15, 0.40, 0.60),
    (0.30, 0.55, 0.75),
    (0.50, 0.70, 0.85),
    (0.70, 0.85, 0.95),
)

HOLD = 0.85  # выше этого расти уже некуда — говорим про удержание


def forecast(data):
    """Куда компания выйдет за три месяца работы.

    Компании, которую нейросети почти не называют, показываем
    прибавку в числах — ради этого отчёт и показывают клиенту.
    Той, что и так в каждом ответе, обещать рост нечестно и незачем:
    для неё разговор про удержание места.
    """
    total = data['ai_total']
    if not total:
        return None

    named = data['ai_named']
    share = named / total

    if share >= HOLD:
        return {
            'hold': True,
            'lo': named, 'hi': total,
            'share_lo': share, 'share_hi': 1.0,
            'line': '',
            'gain': 'вас называют почти в каждом ответе',
        }

    lo_s, hi_s = STEPS[0][1], STEPS[0][2]
    for edge, a, b in STEPS:
        if share >= edge:
            lo_s, hi_s = a, b

    lo = max(named + 1, int(round(total * lo_s)))
    hi = max(lo + 1, int(round(total * hi_s)))
    hi = min(hi, total)
    lo = min(lo, hi)

    if lo == hi:
        line = 'через 3 месяца — примерно %d из %d ответов' % (hi, total)
    else:
        line = 'через 3 месяца — примерно %d\u2013%d из %d ответов' % (lo, hi, total)

    # Во сколько раз чаще. С нуля «в N раз» не считается, там пишем
    # про первые упоминания.
    if named == 0:
        gain = 'сейчас вас не называют ни разу'
    else:
        k = lo / float(named)
        if k >= 1.8:
            gain = 'это примерно в %s раза чаще, чем сейчас' % (
                str(round(k, 1)).replace('.', ',').replace(',0', ''))
        else:
            gain = 'это заметно чаще, чем сейчас'

    return {
        'hold': False,
        'lo': lo, 'hi': hi,
        'share_lo': lo / float(total), 'share_hi': hi / float(total),
        'line': line,
        'gain': gain,
    }


def forecast_search(data):
    """Строчка про обычный поиск — отдельно, у него своя логика."""
    if data.get('search_broken') or not data.get('search_total'):
        return ''
    best = data.get('search_best')
    if not best:
        return 'В поиске Яндекса вас нет в топ-20 — выводим в первую десятку.'
    if best > 10:
        return 'В поиске Яндекса поднимем с %d-го места в первую десятку.' % best
    if best > 3:
        return 'В поиске Яндекса подтянем с %d-го места ближе к первой тройке.' % best
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
    # сейчас» ничего не продают. Числа тут не обещание, а ориентир по
    # нашим проектам, и так и подписано последней строкой.
    f = forecast(data)
    if f:
        y = _draw_forecast(d, data, f, b, y + 16, W, PAD, f_h2, f_xs)

    d.text((PAD, y), b['foot'], font=f_xs, fill=MUTED)
    y += 26

    y += 26
    img = img.crop((0, 0, W, min(H, y + PAD - 20)))
    img.save(path, 'PNG')
    return path


def _draw_forecast(d, data, f, b, top, W, PAD, f_h2, f_xs):
    """Коробка «где вы будете с нами». Высоту считаем по тексту:
    строк бывает от трёх до пяти, и рамка должна их вместить."""
    bar_x = PAD + 24
    bar_w = W - PAD * 2 - 48

    head = ('Место надо удержать' if f['hold']
            else 'Где вы будете с %s' % b['we'])

    if f['hold']:
        body = ('Конкуренты публикуются каждую неделю. Через полгода без '
                'публикаций нейросети начинают называть их вместо вас — '
                'наша работа здесь в том, чтобы не отдать это место.')
    else:
        body = ('Публикации пять дней в неделю на шести площадках. Нейросети '
                'начинают опираться на них, отвечая на запросы клиентов. '
                'Первые сдвиги видно на втором месяце, счёт выше — на третьем.')

    s_line = forecast_search(data)
    body_lines = _wrap(d, body, f_xs, bar_w)[:3]
    n_extra = (1 if f['gain'] else 0) + (1 if s_line else 0) + len(body_lines)

    # Подпись про оценку нужна только там, где стоят числа прогноза:
    # в разговоре про удержание оценивать нечего.
    disclaim = not f['hold']
    height = (186 if disclaim else 162) + n_extra * 24
    d.rounded_rectangle([PAD, top, W - PAD, top + height], radius=20,
                        fill=b['card'], outline=b['box'])
    d.text((bar_x, top + 22), head, font=f_h2, fill=b['c1'])

    # Полоска: закрашено — сколько ответов сейчас, приглушённым
    # продолжением — куда выходим.
    bar_y = top + 82
    total = data['ai_total']
    share = (data['ai_named'] / total) if total else 0
    d.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 18], radius=9, fill=b['track'])
    if f['share_hi'] > 0:
        d.rounded_rectangle([bar_x, bar_y, bar_x + max(18, int(bar_w * f['share_hi'])), bar_y + 18],
                            radius=9, fill=b['band'])
    if share > 0:
        d.rounded_rectangle([bar_x, bar_y, bar_x + max(18, int(bar_w * share)), bar_y + 18],
                            radius=9, fill=b['now'])

    # Подписи под полоской: слева «сейчас», справа «через 3 месяца».
    now_label = 'сейчас — %d из %d ответов' % (data['ai_named'], total)
    d.text((bar_x, bar_y + 28), now_label, font=f_xs, fill=b['now'])
    if not f['hold']:
        rw = d.textlength(f['line'], font=f_xs)
        d.text((bar_x + bar_w - rw, bar_y + 28), f['line'], font=f_xs, fill=b['c1'])

    ty = bar_y + 64
    if f['gain']:
        d.text((bar_x, ty), f['gain'], font=f_xs, fill=b['c1'])
        ty += 24
    if s_line:
        d.text((bar_x, ty), s_line, font=f_xs, fill=b['muted'])
        ty += 24
    for line in body_lines:
        d.text((bar_x, ty), line, font=f_xs, fill=b['muted'])
        ty += 24

    if disclaim:
        d.text((bar_x, top + height - 30), 'Оценка по нашим проектам, не гарантия.',
               font=f_xs, fill=_mix(b['muted'], b['card'], 0.55))

    return top + height + 26
