"""Сбор отчёта и отрисовка картинки."""

import os

from PIL import Image, ImageDraw, ImageFont

# Цвета показаний: плохо, средне, хорошо.
#
# Это не фирменные цвета, а язык прибора — его понимают без подписи.
# Поэтому они одинаковы на обоих сайтах: клиент смотрит на полосу
# соседа и на свою и видит разницу раньше, чем прочтёт числа.
#
# Насыщенность приглушена намеренно: чистый светофор на тёмном фоне
# выглядит аварийной панелью, а не отчётом.
PLOHO = (222, 96, 88)
SREDNE = (226, 174, 74)
HOROSHO = (94, 186, 134)

# Границы. Ниже четверти — плохо, до трёх пятых — средне, дальше
# хорошо. Считаем от того, сколько всего было ответов, а в списке
# конкурентов — от лучшего в списке.
PORAG_PLOHO = 0.25
PORAG_SREDNE = 0.60


def cvet_doli(dolya):
    """Цвет полосы по её заполненности."""
    if dolya < PORAG_PLOHO:
        return PLOHO
    if dolya < PORAG_SREDNE:
        return SREDNE
    return HOROSHO


def cvet_mesta(mesto):
    """Цвет для места в списке. Первая тройка — хорошо, до десятого
    терпимо, дальше плохо: туда уже не смотрят. Места нет вовсе —
    тоже плохо, и это честно."""
    if not mesto:
        return PLOHO
    if mesto <= 3:
        return HOROSHO
    if mesto <= 10:
        return SREDNE
    return PLOHO


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
        'warn': PLOHO,
        'mid': SREDNE,
        'good': HOROSHO,
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
        'warn': PLOHO,
        'mid': SREDNE,
        'good': HOROSHO,
    },
}

def _mix(a, b, t):
    """Цвет между a и b: t=0 — это a, t=1 — это b. Нужен для
    приглушённых подписей: прозрачности в RGB-картинке нет."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# Шрифты возим с собой, а не ищем в системе.
#
# На хостинге системных шрифтов может не быть вовсе, либо в них не быть
# кириллицы: латиница нарисуется, а русские буквы выйдут пустыми
# квадратиками. Так и случилось при первом запуске на хостинге.
#
# Здесь те же гарнитуры, что на сайтах: Unbounded для крупных чисел и
# названия, Inter для остального. Отчёт из-за этого читается как
# продолжение сайта, а не как чужая бумага.
SVOI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shrifty')

NACHERTANIYA = {
    'reg':  ('Inter-Regular.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    'med':  ('Inter-Medium.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    'semi': ('Inter-SemiBold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    'bold': ('Inter-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    'disp': ('Unbounded-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    'disp2': ('Unbounded-SemiBold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
}

_kesh = {}


def _font(size, nach='reg'):
    """Шрифт нужного начертания. Системный — только как запасной."""
    klyuch = (size, nach)
    if klyuch in _kesh:
        return _kesh[klyuch]

    imya, zapas = NACHERTANIYA.get(nach, NACHERTANIYA['reg'])
    for path in (os.path.join(SVOI, imya), zapas):
        if os.path.exists(path):
            try:
                _kesh[klyuch] = ImageFont.truetype(path, size)
                return _kesh[klyuch]
            except Exception:
                continue

    # Досюда доходить не должно. Встроенный шрифт кириллицы не знает, и
    # отчёт выйдет из квадратиков — это хуже, чем отсутствие отчёта,
    # потому что такую картинку менеджер отправит клиенту не глядя.
    raise RuntimeError(
        'Не нашёлся шрифт для картинки отчёта.\n'
        'Он должен лежать здесь: %s\n'
        'Запустите установку заново — она положит его на место.' % SVOI)


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

    # Нейросеть, не ответившая ни разу, в engines не попадает вовсе —
    # и на картинке её просто нет. Клиент видит «0 из 12» вместо
    # «0 из 24» и не понимает, почему счёт вдвое меньше обещанного.
    # Считаем отказы отдельно и показываем их наравне с ответами.
    otkazy = {}
    for r in ai_results:
        if r.get('error'):
            otkazy[r['engine']] = otkazy.get(r['engine'], 0) + 1

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
        'ai_otkazy': otkazy,
        'ai_best_position': min(positions) if positions else None,
        'search_total': len(s_ok),
        'search_found': len(s_found),
        'search_best': min(s_positions) if s_positions else None,
        # По какому запросу нашлось лучшее место. Без этого число не
        # проверить руками: место в поиске гуляет от запроса к запросу
        # сильнее, чем кажется.
        'search_best_query': (min(s_found, key=lambda r: r['position'])['query']
                              if s_found else ''),
        # Сколько запросов вывели сайт в первую десятку. Честная
        # картина по поиску: одно лучшее место из пяти запросов ничего
        # не говорит об остальных четырёх.
        'search_v_top10': len([p for p in s_positions if p <= 10]),
        # Сколько компаний нейросеть называет в одном ответе.
        'nazyvayut_v_otvete': skolko_nazyvayut(ai_results),
        'ai_results': ai_results,
        'search_results': search_results,
        'rivals': _rivals(ai_results, company.get('names') or [company.get('name', '')],
                          company.get('known_rivals'), company.get('sosedi')),
        # Соседи — отдельно от «кого называют вместо вас». Там имена из
        # ответов нейросети, то есть крупные на всю страну. Здесь —
        # найденные поиском по району: того же размера и того же места.
        'sosedi': upominaniya(ai_results, company.get('sosedi')),
        'sosedi_gde': company.get('sosedi_gde', ''),
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


def upominaniya(ai_results, imena):
    """Сколько ответов назвали каждое из имён. Ноль тоже считаем.

    Ноль здесь не пустая строка, а самое важное, что можно сказать
    клиенту: рядом с ним работают вот эти пятеро, и их тоже не
    называют — значит, место свободно.
    """
    from . import matching

    out = []
    for imya in (imena or []):
        n = sum(1 for r in ai_results
                if matching.mentioned_any(r.get("answer") or "", [imya]))
        out.append((imya, n))
    return out

def imena_v_otvete(text):
    """Названия компаний из одного ответа нейросети.

    Берём строки нумерованных списков: в них нейросеть и перечисляет
    компании. Это не точный разбор, а подсказка — но её хватает и
    чтобы понять, кого называют, и чтобы сосчитать, сколько мест в
    ответе вообще бывает.
    """
    import re

    out = []
    for line in (text or '').splitlines():
        # Разделяем только по длинному тире и двоеточию: обычный
        # дефис — часть названия, «Дента-Люкс» по нему рвать нельзя.
        m = re.match(r'^\s*\d+[.)]\s*([^—–:\n]{3,60})', line)
        if not m:
            continue
        cand = m.group(1).strip(' *«»"\'.,')
        # Закрывающая кавычка обрезается вместе с точкой, а открывающая
        # остаётся внутри строки: «ООО «Главстрой». Возвращаем пару.
        if cand.count('«') > cand.count('»'):
            cand += '»'
        if _looks_like_name(cand):
            out.append(cand)
    return out


def skolko_nazyvayut(ai_results):
    """Сколько компаний нейросеть называет в одном ответе — обычно.

    Это число заменило в отчёте место в поиске Яндекса. Прежнее число
    было лучшим местом из всех запросов, и рядом с «нейросети не
    называют вас ни разу» оно читалось как «да всё у меня хорошо»:
    клиент видел единицу и успокаивался. Хотя смысл разбора ровно
    обратный — поиск и нейросеть это два разных списка, и место в
    одном ничего не говорит о втором.

    Сколько мест в ответе — число честное и бьёт в ту же точку: вот
    столько компаний нейросеть назовёт вашему клиенту, и вас среди
    них нет.

    Берём середину ряда, а не среднее: один ответ на двадцать позиций
    перекосил бы среднее и обещал бы клиенту больше мест, чем бывает.
    """
    dliny = sorted(len(imena_v_otvete(r.get('answer') or ''))
                   for r in ai_results if not r.get('error'))
    dliny = [n for n in dliny if n]
    if not dliny:
        return 0
    return dliny[len(dliny) // 2]


def _rivals(ai_results, own_names, known=None, krome=None):
    """Кого нейросети называют вместо компании.

    Берём строки нумерованных списков: в них нейросеть и перечисляет
    компании. Это не точный разбор, а подсказка менеджеру, о ком
    говорить с клиентом.
    """
    import re
    from . import matching

    counts = {}
    for r in ai_results:
        for cand in imena_v_otvete(r.get('answer') or ''):
            if matching.mentioned_any(cand, own_names):
                continue
            key = matching.fold(cand)
            if key:
                counts[key] = counts.get(key, [0, cand])
                counts[key][0] += 1
                counts[key][1] = cand
    # Конкуренты, названные в анкете, попадают в список всегда —
    # даже с нулём упоминаний. Ноль здесь не пустое место, а довод:
    # клиент видит, что названного им конкурента тоже не знают.
    izvestnye = []
    for imya in (known or []):
        key = matching.fold(imya)
        if not key:
            continue
        counts.pop(key, None)
        n = sum(1 for r in ai_results
                if matching.mentioned_any(r.get('answer') or '', [imya]))
        izvestnye.append((imya, n))

    # Соседей по району в этом списке не показываем: у них свой блок
    # ниже. Иначе одна и та же компания стоит в отчёте дважды, и
    # кажется, что её назвали вдвое чаще.
    for imya in (krome or []):
        counts.pop(matching.fold(imya), None)

    mest = max(0, 6 - len(izvestnye))
    top = sorted(counts.values(), key=lambda x: -x[0])[:mest]
    return izvestnye + [(name, n) for n, name in top]


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
    'интернет-магазин': 'На общий вопрос нейросеть называет маркетплейсы и сети. '
                        'Мы поднимаем вас в вашей теме, а не в торговле целиком.',
    'розничный магазин': 'На общий вопрос нейросеть называет крупные сети. Мы поднимаем '
                         'вас в вашей теме, а не в торговле целиком.',
    'оптовая торговля': 'На общий вопрос нейросеть называет крупных поставщиков. Мы '
                        'поднимаем вас в вашей теме, а не в отрасли целиком.',
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
        'body': 'Автопубликация: готовый материал сам уходит на площадки по расписанию. '
                'Нейросети начинают опираться на эти публикации, отвечая на запросы '
                'клиентов. Первые сдвиги видно на втором месяце работы.',
    }


def why_line(company):
    """Почему в этой отрасли компанию не называют. Пустая строка —
    отрасль обычная, объяснять нечего."""
    from . import queries

    topic = (queries.topic_of(company.get('industry'))
             or queries.topic_of(company.get('kind')))
    return CROWDED.get(topic, '')


def sklonenie(n, odna, dve, mnogo):
    """Число со словом в нужном падеже: 1 компанию, 2 компании, 5 компаний.

    Без этого в отчёте выходило «называет 4 компаний». Мелочь, но
    отчёт уходит клиенту, и по таким мелочам судят обо всём остальном.
    """
    n = abs(int(n))
    if n % 100 in (11, 12, 13, 14):
        return mnogo
    ost = n % 10
    if ost == 1:
        return odna
    if ost in (2, 3, 4):
        return dve
    return mnogo

def sosedi_line(data):
    """Одна фраза под списком соседей — то, ради чего он показан.

    Три случая, и все три клиенту полезны: соседей называют, а его
    нет; не называют никого, и место свободно; называют и его тоже,
    и тогда речь про то, чтобы не потерять место.
    """
    sosedi = data.get("sosedi") or []
    if not sosedi:
        return ''
    nazvany = [x for x in sosedi if x[1]]
    svoi = data.get("ai_named", 0)

    if not nazvany and not svoi:
        return ("Рядом нейросети не называют никого. Место свободно: "
                "займёт тот, кто начнёт публиковаться первым.")
    if nazvany and not svoi:
        return ("Из тех, кто работает рядом, нейросети называют %d %s, "
                "а вас — ни разу." % (len(nazvany), sklonenie(
                    len(nazvany), "компанию", "компании", "компаний")))
    if nazvany:
        return ("Рядом называют не только вас — эти компании занимают "
                "те же места в ответах.")
    return "Рядом называют только вас."

def search_line(data):
    """Строчка про обычный поиск.

    Раньше здесь стояло лучшее место из всех запросов, и при хорошем
    месте выходило «в поиске вы наверху — эту позицию удерживаем».
    Клиент читал это рядом с «нейросети не называют вас ни разу» и
    делал вывод, что у него и так всё в порядке.

    Поэтому теперь строка не хвалит место, а объясняет разницу между
    двумя списками: в выдаче Яндекса двадцать строк и человек выбирает
    сам, в ответе нейросети — несколько названий, и выбор уже сделан
    за него. Место в первом списке ничего не даёт во втором.
    """
    if data.get('search_broken') or not data.get('search_total'):
        return ''

    vsego = data['search_total']
    v_top10 = data.get('search_v_top10') or 0
    naideno = data.get('search_found') or 0
    skolko = data.get('nazyvayut_v_otvete') or 0

    if not data.get('search_best'):
        return 'В поиске Яндекса вас пока нет в топ-20 — поднимаем и там.'

    skolko_zaprosov = v_top10 if v_top10 else naideno
    slovo = sklonenie(skolko_zaprosov, 'запросу', 'запросам', 'запросам')
    gde = '%s по %d %s из %d' % (
        'в первой десятке' if v_top10 else 'в топ-20',
        skolko_zaprosov, slovo, vsego)

    if data.get('ai_named'):
        return 'В поиске Яндекса сайт %s — эти места удерживаем.' % gde

    if skolko:
        return ('В поиске Яндекса сайт %s. Но выдачу человек листает сам, а нейросеть сразу называет %d %s — и выбирает за него.'
                % (gde, skolko, sklonenie(skolko, 'компанию', 'компании', 'компаний')))
    return ('В поиске Яндекса сайт %s. Но выдачу человек листает сам, а нейросеть сразу называет несколько компаний — и выбирает за него.' % gde)


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


def _podlozhka(W, H, bg, ottenok):
    """Фон с едва заметным переходом сверху вниз.

    Ровная заливка выглядит пустой заготовкой, и по совету
    оформителей сюда просилось зерно. Зерно пробовали: картинка
    раздувается втрое, потому что сжатие живёт на ровных участках. А
    картинка идёт через телеграм по связи, которая на длинных посылках
    и так рвётся, — так что цена оказалась выше пользы, тем более что
    на телефоне зерна всё равно не видно.
    Переход даёт ту же глубину и не стоит почти ничего: строки
    сжимаются одна относительно другой.
    """
    img = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(img)
    vysota = min(H, 700)
    for i in range(vysota):
        k = (1 - i / float(vysota)) ** 2
        d.line([(0, i), (W, i)], fill=_mix(bg, ottenok, 0.5 * k))
    return img


def _razryadka(d, xy, text, font, fill, shag=1.6):
    """Текст с разрядкой — лишний воздух между буквами.

    Мелкие подписи набраны заглавными, а заглавные без разрядки
    слипаются в плотный кирпич. Разрядки в рисовалке нет, поэтому
    ведём буквы по одной.
    """
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + shag


def _polosa(d, x, y, shirina, vysota, dolya, cvet, fon, radius=None):
    """Полоса заполнения. Ею показываем доли: глазом сравнивать длины
    куда быстрее, чем читать «7 из 12» и «4 из 12» подряд."""
    r = radius if radius is not None else vysota // 2
    d.rounded_rectangle([x, y, x + shirina, y + vysota], radius=r, fill=fon)
    if dolya > 0:
        zanyato = max(vysota, int(shirina * min(dolya, 1.0)))
        d.rounded_rectangle([x, y, x + zanyato, y + vysota], radius=r, fill=cvet)


def draw_png(data, path, brand='genii'):
    """Рисует картинку отчёта. Ширина 1200 — читается и в телеграме,
    и при пересылке клиенту.

    brand — 'genii' или 'prompter': та же проверка в цветах того
    сайта, с которого пришла заявка.
    """
    b = BRANDS.get(brand, BRANDS['genii'])
    BG, LINE, MUTED = b['bg'], b['line'], b['muted']

    W, PAD = 1200, 64
    SHIR = W - PAD * 2

    c = data['company']
    head, tone = _verdict(data)
    head_color = b[tone]
    rivals = data['rivals']
    total, named = data['ai_total'], data['ai_named']
    dolya = (named / total) if total else 0

    H = 2400
    img = _podlozhka(W, H, BG, b['card'])
    d = ImageDraw.Draw(img)

    # ---------- шапка ----------
    y = PAD
    # Название набираем как есть: «ГенИИ» заглавными превращается в
    # «ГЕНИИ» и перестаёт быть фирменным написанием.
    _razryadka(d, (PAD, y), b['kicker'], _font(16, 'semi'), b['c1'], 0.8)
    y += 34

    # Название подгоняем кеглем, а не обрезаем. Длинное имя
    # застройщика раньше рвалось на полуслове и без многоточия —
    # выходило «ООО СПЕЦИАЛИЗИРОВАННЫЙ ЗАСТРОЙЩИК ЖИЛЫХ», и клиент
    # видел в отчёте о себе обрубок.
    # В заголовок ставим бренд, а не строчку из реестра. У
    # предпринимателя там фамилия владельца — «ИП Кормильцев Дмитрий
    # Евгеньевич», — и отчёт с таким заголовком неловко отправлять
    # самому клиенту: он знает свой барбершоп «Britva», а не паспорт
    # хозяина. Реестровое имя не теряем, оно уходит строкой ниже.
    nazvanie = c.get('brand') or c.get('full_name') or c.get('name') or ''
    for kegl in (44, 38, 33, 29, 25, 22):
        f_naz = _font(kegl, 'disp')
        stroki = _wrap(d, nazvanie, f_naz, SHIR)
        if len(stroki) <= 2:
            break
    for line in stroki[:3]:
        d.text((PAD, y), line, font=f_naz, fill=TEXT)
        y += int(kegl * 1.3)
    y += 6

    chasti = []
    reestr = c.get('full_name') or c.get('name') or ''
    if reestr and reestr.strip().lower() != nazvanie.strip().lower():
        chasti.append(reestr)
    if c.get('inn'):
        chasti.append('ИНН %s' % c['inn'])
    if c.get('city'):
        chasti.append(c['city'])
    if c.get('industry'):
        chasti.append(c['industry'])
    sub = '  ·  '.join(chasti)
    for line in _wrap(d, sub, _font(19), SHIR)[:2]:
        d.text((PAD, y), line, font=_font(19), fill=MUTED)
        y += 26
    d.text((PAD, y), (data['site'] or 'сайта не нашли — проверяли по названию'),
           font=_font(19, 'med'), fill=b['c2'] if data['site'] else MUTED)
    y += 46

    d.rectangle([PAD, y, W - PAD, y + 1], fill=LINE)
    y += 44

    # ---------- главное: одно число, а не три одинаковых ----------
    # Раньше здесь стояли три равные карточки. Так главное число — доля
    # ответов, где компанию называют, — весило ровно столько же, сколько
    # второстепенные места в списках. Читающий не понимал, куда смотреть.
    for line in _wrap(d, head, _font(31, 'semi'), int(SHIR * 0.62)):
        d.text((PAD, y), line, font=_font(31, 'semi'), fill=head_color)
        y += 40
    y += 18

    verh = y
    f_ogr = _font(104, 'disp')
    chislo = '%d' % named
    d.text((PAD, y - 12), chislo, font=f_ogr, fill=cvet_doli(dolya))
    shirina_ch = d.textlength(chislo, font=f_ogr)

    f_iz = _font(30, 'disp2')
    d.text((PAD + shirina_ch + 14, y + 48), 'из %d' % total, font=f_iz, fill=MUTED)

    y += 118
    d.text((PAD, y), 'ответов нейросетей, где вас назвали',
           font=_font(19), fill=MUTED)
    y += 34
    _polosa(d, PAD, y, int(SHIR * 0.58), 10, dolya, cvet_doli(dolya), b['track'])
    y += 34

    # Два второстепенных числа — справа, без рамок, мельче: они
    # поясняют главное, а не спорят с ним.
    px = PAD + int(SHIR * 0.66)
    py = verh
    # Второе число — сколько компаний нейросеть называет в одном
    # ответе. Раньше здесь стояло лучшее место сайта в поиске Яндекса,
    # и рядом с «не называют ни разу» оно читалось как «да всё у меня
    # хорошо»: клиент видел единицу и успокаивался. Смысл разбора
    # ровно обратный — поиск и нейросеть это два разных списка, и
    # место в одном ничего не говорит о втором. Число мест в ответе
    # бьёт в ту же точку и не требует оговорок: вот столько компаний
    # услышит ваш клиент, и вас среди них нет.
    skolko = data.get('nazyvayut_v_otvete') or 0
    pары = [
        (('%d-е' % data['ai_best_position']) if data['ai_best_position'] else '—',
         'место в списке нейросети', cvet_mesta(data['ai_best_position']),
         38 if data['ai_best_position'] else 24),
        (str(skolko) if skolko else '—',
         '%s нейросеть называет в одном ответе'
         % sklonenie(skolko, 'компанию', 'компании', 'компаний'),
         TEXT if skolko else MUTED, 38 if skolko else 24),
    ]
    for i, (bolshoe, podpis, cvet, kegl) in enumerate(pары):
        if i:
            d.rectangle([px, py, W - PAD, py + 1], fill=LINE)
            py += 26
        # Числу — крупный кегль, фразе — поменьше. Прочерк тем же
        # размером, что «3-е», занимает всю колонку и кричит, хотя
        # это не показатель, а его отсутствие.
        d.text((px, py), bolshoe, font=_font(kegl, 'disp2'), fill=cvet)
        py += kegl + 12
        for line in _wrap(d, podpis, _font(17), W - PAD - px)[:3]:
            d.text((px, py), line, font=_font(17), fill=MUTED)
            py += 23
        py += 22

    y = max(y, py) + 28

    # ---------- по нейросетям: полосами ----------
    _razryadka(d, (PAD, y), 'ПО НЕЙРОСЕТЯМ', _font(14, 'semi'), _mix(MUTED, BG, 0.15))
    y += 32

    otkazy = data.get('ai_otkazy') or {}
    stroki = [(n, e['named'], e['total']) for n, e in data['ai_by_engine'].items()]
    for imya, n, t in stroki:
        d.text((PAD, y), imya, font=_font(20, 'med'), fill=TEXT)
        d_e = (n / t) if t else 0
        _polosa(d, PAD + 190, y + 7, 380, 10, d_e, cvet_doli(d_e), b['track'])
        d.text((PAD + 600, y), '%d из %d' % (n, t), font=_font(19), fill=MUTED if not n else TEXT)
        y += 38
    for imya in otkazy:
        if imya in data['ai_by_engine']:
            continue
        d.text((PAD, y), imya, font=_font(20, 'med'), fill=MUTED)
        d.text((PAD + 190, y), 'не ответил, проверка шла без него',
               font=_font(19), fill=b['warn'])
        y += 38
    if not stroki and not otkazy:
        d.text((PAD, y), 'ответов нет', font=_font(20), fill=MUTED)
        y += 38
    y += 22

    # ---------- конкуренты: полосами, и вы в том же списке ----------
    # Своя строка в конце — самое сильное место отчёта. Пока компания
    # была просто не упомянута, разрыв надо было воображать. Теперь он
    # виден в одном столбце: у соседей полосы, у вас пусто.
    # Своя строка рисуется один раз и внизу последнего блока: когда
    # она стояла под обоими графиками, отчёт читался как повтор.
    sosedi = data.get('sosedi') or []
    if rivals:
        _razryadka(d, (PAD, y), 'КОГО НАЗЫВАЮТ ВМЕСТО ВАС', _font(14, 'semi'), _mix(MUTED, BG, 0.15))
        y += 32
        maks = max([n for _, n in rivals] + [named]) or 1
        for imya, n in rivals:
            for line in _wrap(d, imya, _font(20), 320)[:1]:
                d.text((PAD, y), line, font=_font(20), fill=TEXT)
            _polosa(d, PAD + 340, y + 7, 420, 10, n / maks, cvet_doli(n / maks), b['track'])
            d.text((PAD + 790, y), str(n), font=_font(19), fill=MUTED)
            y += 36

        if not sosedi:
            y += 6
            d.rectangle([PAD, y, PAD + 810, y + 1], fill=LINE)
            y += 18
            svoe = c.get('brand') or c.get('name') or 'ваша компания'
            d.text((PAD, y), _wrap(d, svoe, _font(20, 'semi'), 320)[0],
                   font=_font(20, 'semi'), fill=head_color)
            _polosa(d, PAD + 340, y + 7, 420, 10, named / maks,
                    cvet_doli(named / maks), b['track'])
            d.text((PAD + 790, y), str(named), font=_font(19, 'semi'), fill=head_color)
        y += 48

    # ---------- соседи: кто работает рядом ----------
    # Нейросеть на общий вопрос называет имена на всю страну, и
    # сравнение с ними клиента только расстраивает: он не «Теремъ» и
    # не станет им. А вот пятеро из его же района и его же размера —
    # это и есть та конкуренция, которую он чувствует каждый день.
    if sosedi:
        y += 14
        gde = data.get('sosedi_gde') or ''
        shapka = ('КТО РАБОТАЕТ РЯДОМ С ВАМИ' if not gde
                  else 'КТО РАБОТАЕТ РЯДОМ: %s' % gde.upper())
        _razryadka(d, (PAD, y), shapka, _font(14, 'semi'), _mix(MUTED, BG, 0.15))
        y += 32
        maks_s = max([n for _, n in sosedi] + [named]) or 1
        for imya, n in sosedi:
            for line in _wrap(d, imya, _font(20), 320)[:1]:
                d.text((PAD, y), line, font=_font(20), fill=TEXT)
            _polosa(d, PAD + 340, y + 7, 420, 10, n / maks_s,
                    cvet_doli(n / maks_s), b['track'])
            d.text((PAD + 790, y), str(n), font=_font(19), fill=MUTED)
            y += 36

        y += 6
        d.rectangle([PAD, y, PAD + 810, y + 1], fill=LINE)
        y += 18
        svoe = c.get('brand') or c.get('name') or 'ваша компания'
        d.text((PAD, y), _wrap(d, svoe, _font(20, 'semi'), 320)[0],
               font=_font(20, 'semi'), fill=head_color)
        _polosa(d, PAD + 340, y + 7, 420, 10, named / maks_s,
                cvet_doli(named / maks_s), b['track'])
        d.text((PAD + 790, y), str(named), font=_font(19, 'semi'), fill=head_color)
        y += 44

        itog = sosedi_line(data)
        if itog:
            for line in _wrap(d, itog, _font(19), SHIR)[:3]:
                d.text((PAD, y), line, font=_font(19), fill=MUTED)
                y += 26
            y += 16

    # ---------- что изменится ----------
    p = promise(data)
    if p:
        y = _draw_promise(d, data, p, b, y + 10, W, PAD, _font(27, 'semi'), _font(18))

    d.text((PAD, y), b['foot'], font=_font(17), fill=_mix(MUTED, BG, 0.35))
    y += 30

    img = img.crop((0, 0, W, min(H, y + PAD - 14)))
    img.save(path, 'PNG', optimize=True)
    return path


def _stupeni(d, b, right, base, n=5, rovno=False):
    """Столбики лесенкой — знак роста без единой цифры.

    Раньше здесь была полоска с долями, и это было обещание в числах.
    Лесенка говорит то же самое про направление и ничего не обещает.

    rovno — столбики вровень: там, где речь про удержание места,
    лесенка вверх противоречила бы тексту.
    """
    w, gap, verh = 14, 9, 42
    x = right - (n * w + (n - 1) * gap)
    for i in range(n):
        k = i / float(n - 1)
        h = int(verh * (0.78 if rovno else 0.20 + 0.80 * k))
        col = b['c1'] if rovno else _mix(b['band'], b['c1'], k)
        d.rounded_rectangle([x, base - h, x + w, base], radius=4, fill=col)
        x += w + gap


def _draw_promise(d, data, p, b, top, W, PAD, f_h2, f_xs):
    """Коробка «что изменится с нами». Высоту считаем по тексту:
    строк бывает от трёх до шести, и рамка должна их вместить."""
    pad_x = PAD + 28
    box_w = W - PAD * 2 - 56

    head = ('Это место надо удержать' if p['hold']
            else 'Что изменится с %s' % b['we'])

    lines = []
    lines += [(l, b['c1'], 'med') for l in _wrap(d, p['lead'], f_xs, box_w - 150)[:2]]
    why = why_line(data['company'])
    if why:
        lines += [(l, b['c2'], 'reg') for l in _wrap(d, why, f_xs, box_w)[:2]]
    s_line = search_line(data)
    if s_line:
        lines += [(l, b['muted'], 'reg') for l in _wrap(d, s_line, f_xs, box_w)[:2]]
    lines += [(l, b['muted'], 'reg') for l in _wrap(d, p['body'], f_xs, box_w)[:3]]

    height = 108 + len(lines) * 26
    d.rounded_rectangle([PAD, top, W - PAD, top + height], radius=24,
                        fill=b['card'], outline=b['box'])
    d.text((pad_x, top + 30), head, font=f_h2, fill=b['c1'])
    _stupeni(d, b, W - PAD - 28, top + 62, rovno=p['hold'])

    ty = top + 84
    for line, col, nach in lines:
        d.text((pad_x, ty), line, font=_font(18, nach), fill=col)
        ty += 26

    return top + height + 30
