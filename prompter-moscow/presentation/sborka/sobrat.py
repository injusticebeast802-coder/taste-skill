# -*- coding: utf-8 -*-
"""Короткая общая презентация «Промптер. Москва» — восемь слайдов.

Это презентация, а не сайт в слайдах. Разница простая: на сайте
человек читает сам, поэтому там плотные карточки и абзацы. На слайде
говорит человек, а слайд только показывает, о чём речь. Отсюда правила
этой сборки:

  - одна мысль на слайд;
  - крупный шрифт и много воздуха;
  - слов ровно столько, сколько нельзя не написать;
  - вместо плотных абзацев — большие цифры, значки и фотографии.

Палитра, шрифты и значки взяты с сайта prompter-ai.moscow: цвета из
style.css, шрифты те же файлы, значки вырезаны из спрайта index.html.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from kit import *
from ikonki import ikonka

UB  = ('Unbounded', True)      # начертания для измерения ширины
UBS = ('Unbounded', False)
IR  = ('Inter', 'r')
IM  = ('Inter', 'm')
IS  = ('Inter', 's')

VSEGO = 8
SAJT    = 'https://prompter-ai.moscow'
ZAYAVKA = SAJT + '/zayavka.html?from=presentation-obshchaya'
ANALIZ  = SAJT + '/zayavka.html?from=presentation-analiz'

# Контакты стоят в одном месте: их подставляют и на обложку, и на
# последний слайд. Презентацию ведут менеджеры, поэтому телефон, почту
# и аккаунт меняют здесь и пересобирают — либо правят прямо в
# PowerPoint, это обычные надписи.
TELEFON = '+7 906 758-77-77'
POCHTA  = 'prompter.moscow@mail.ru'
AKKAUNT = '@Prompter_mos'

MALO = []     # сюда попадает всё, что не влезло: печатаем в конце сборки


def novyj(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    fon(sl)
    return sl


def nomer(sl, n):
    """Только номер страницы. Адрес сайта на каждом слайде — признак
    сайта, а не презентации; он есть на обложке и в контактах."""
    tf = nadpis(sl, W - PAD - 2.0, H - 0.56, 2.0, 0.26)
    abzac(tf, '%d / %d' % (n, VSEGO), 10, font=BODY, color=MUTED2, lead=1.0,
          align=PP_ALIGN.RIGHT, first=True)


def _plain(x):
    if isinstance(x, str):
        return x
    return ''.join(k if isinstance(k, str) else k[0] for k in x)


def blok(sl, x, y, w, text, key, size, font=BODY, color=WHITE, bold=False,
         lead=1.42, align=PP_ALIGN.LEFT, kegli=None, max_strok=None,
         max_h=None, chto=''):
    """Абзац с посчитанной высотой. Возвращает координату низа.

    Ширину строки считаем по файлу шрифта, поэтому кегль подбирается
    самый крупный из тех, при которых текст влезает в отведённое место.
    """
    plain = _plain(text)
    if kegli is None and max_h is not None:
        kegli = [round(size * k, 1) for k in (1, .96, .92, .88, .84, .8, .76, .72)]
    if kegli:
        size, lines = podobrat(plain, key, kegli, w, max_h if max_h else 99,
                               lead, max_strok)
    else:
        lines = perenos(plain, key, size, w * 0.96)
    h = len(lines) * size * lead / 72.0
    if max_h is not None and h > max_h + 0.02:
        MALO.append('%s: надо %.2f″, есть %.2f″ — %s'
                    % (chto or 'блок', h, max_h, plain[:60]))
    tf = nadpis(sl, x, y, w, h + 0.08)
    abzac(tf, text, size, font=font, color=color, bold=bold, lead=lead,
          align=align, first=True)
    return y + h


def cherta(sl, x, y, w, h, cvet=LINE):
    s = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                            Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = cvet
    s.line.fill.background(); s.shadow.inherit = False
    return s


def znak(sl, x, y, d, imya, cvet='7FC4FF', fill=None, pad=0.22):
    """Значок сайта, при желании в круглой подложке."""
    if fill is not None:
        plitka(sl, x, y, d, d, fill=fill, line=None, radius=d / 2)
    kartinka(sl, ikonka(imya, cvet), x + pad, y + pad, d - pad * 2, d - pad * 2)


def strelka(sl, x, y, h, nazad=False, cvet=LINE2):
    """Шеврон между карточками: показывает, куда идёт поток."""
    tf = nadpis(sl, x, y, 0.3, h, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, '\u2039' if nazad else '\u203a', 19, font=BODY, color=cvet,
          bold=True, lead=1.0, align=PP_ALIGN.CENTER, first=True)


def knopka(sl, x, y, w, h, tekst, url, pt=15):
    k = plitka(sl, x, y, w, h, fill=BLUE, line=None, radius=h / 2)
    ssylka(k, url)
    tf = nadpis(sl, x, y, w, h, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, tekst, pt, font=BODY, color=WHITE, bold=True, lead=1.0,
          align=PP_ALIGN.CENTER, first=True)
    ssylka(tf._parent, url)


# ============================================================ 1. ОБЛОЖКА

def slajd_1(prs):
    sl = novyj(prs)
    kartinka(sl, kadr(IMG + '/hero-bg.jpg', W, H, 'oblozhka.png',
                      dark=0.28, left_wash=0.84), 0, 0, W, H)

    kartinka(sl, ASSETS + '/logo.png', PAD, 0.62, 0.46, 0.46)
    tf = nadpis(sl, PAD + 0.64, 0.7, 5.0, 0.38)
    abzac(tf, [('Prompter ', {}), ('Moscow', {'bold': True})],
          16, font=DISP, color=WHITE, lead=1.1, first=True)

    y = blok(sl, PAD, 3.3, 10.4,
             'Продвижение бизнеса там, где его теперь ищут',
             UB, 42, font=DISP, color=WHITE, bold=True, lead=1.14,
             kegli=[42, 38, 34], max_strok=2)
    blok(sl, PAD, y + 0.52, 8.6,
         'GEO- и SEO-продвижение на автономной AI-платформе «Промптер»',
         IR, 18, color=MUTED, lead=1.4)

    # Партнёрство — одной строкой, без плашки: на обложке нужен воздух.
    blok(sl, PAD, H - 1.42, 10.0,
         [('Официальный партнёр IT-компании «Промптер» по Москве и МО', {'color': MUTED2}),
          ('     ЛД № 54-ПРТ', {'color': LBLUE, 'bold': True})],
         IR, 12, font=BODY, lead=1.3)
    blok(sl, PAD, H - 0.96, 11.0,
         [('prompter-ai.moscow', {'color': WHITE, 'bold': True}),
          ('     %s     %s' % (TELEFON, POCHTA), {'color': MUTED2})],
         IS, 13, font=BODY, lead=1.3)


# ====================================================== 2. РЫНОК ИЗМЕНИЛСЯ

def slajd_2(prs):
    sl = novyj(prs); nomer(sl, 2)

    # Картинка уходит в край слайда — так это читается как слайд,
    # а не как блок на странице сайта.
    iw = 5.5
    kartinka(sl, kadr(IMG + '/neurons.jpg', iw, H, 'nejrony.png', dark=0.12),
             W - iw, 0, iw, H)

    tw = W - iw - PAD - 0.9
    y = blok(sl, PAD, 1.75, tw, 'Клиентов теперь ищут нейросети',
             UB, 38, font=DISP, color=WHITE, bold=True, lead=1.16,
             kegli=[38, 34, 30], max_strok=3)
    y = blok(sl, PAD, y + 0.44, tw,
             'Человек не листает десять синих ссылок. Он спрашивает нейросеть '
             'и получает готовый ответ с двумя-тремя названиями компаний.',
             IR, 16, color=MUTED, lead=1.55)

    cherta(sl, PAD, y + 0.62, 1.5, 0.026, LBLUE)
    blok(sl, PAD, y + 0.92, tw, 'Кого назвали — к тому и пошли.',
         UB, 21, font=DISP, color=LBLUE, bold=True, lead=1.25,
         kegli=[21, 19, 17], max_strok=2)


# ================================================= 3. ПЯТЬ ИИ-АГЕНТОВ

# Три числа с бывшего слайда «Что это даёт бизнесу»: он ушёл, а выгода
# осталась — полосой под карточками агентов, мельче и без третьей
# строки-пояснения.
VYGODY = [
    ('в 4 раза',  'меньше вашего времени'),
    ('в 3 раза',  'ниже расходы на СММ'),
    ('0 человек', 'нанимать не нужно'),
]


# Те же пять агентов, что и на сайте, и в том же порядке. На слайде от
# каждого остаётся одна строка: роль и что человек перестаёт делать
# руками. Пятый — сценарист с оператором — появился в платформе
# последним, поэтому он отмечен зелёным, как и всё новое в этой сборке.
AGENTY = [
    ('pencil',  'AI-копирайтер',  'Тексты и посты в стиле бренда для всех площадок'),
    ('target',  'AI-маркетолог',  'Ниша, конкуренты и запросы, по которым вас ищут'),
    ('send',    'AI СММ-менеджер', 'Проверка, публикация и контроль выдачи'),
    ('palette', 'AI-дизайнер',    'Визуал под требования каждой площадки'),
    ('video',   'AI-сценарист и оператор',
     'Сценарий и готовый ролик по описанию сцены'),
]


def slajd_3(prs):
    sl = novyj(prs); nomer(sl, 3)
    y = blok(sl, PAD, 0.72, CW, '5 ИИ-агентов вместо digital-агентства',
             UB, 32, font=DISP, color=WHITE, bold=True, lead=1.18,
             kegli=[32, 29, 26], max_strok=1)
    blok(sl, PAD, y + 0.26, 9.6,
         'Каждый закрывает роль, за которую в агентстве платят отдельному '
         'человеку с отдельной зарплатой.',
         IR, 15, color=MUTED, lead=1.5, max_strok=2, max_h=0.7)

    y = 2.36
    zaz = 0.22
    cw = (CW - zaz * (len(AGENTY) - 1)) / len(AGENTY)
    ch = 3.0
    pad_v = 0.26

    for i, (ik, t, d) in enumerate(AGENTY):
        novoe = i == len(AGENTY) - 1
        cvet = '4ADE80' if novoe else '7FC4FF'
        cx = PAD + i * (cw + zaz)
        plitka(sl, cx, y, cw, ch, fill=CARD,
               line=(GREEN if novoe else LINE), radius=0.16,
               lw=(1.4 if novoe else 1.0))
        znak(sl, cx + pad_v, y + 0.28, 0.72, ik, cvet, fill=CARD2, pad=0.19)

        if novoe:
            # Метка «новое» — тем же зелёным, что и выгода на слайде цены.
            bw, bh = 0.82, 0.28
            plitka(sl, cx + cw - pad_v - bw, y + 0.5, bw, bh,
                   fill=GREEN, line=None, radius=bh / 2)
            tf = nadpis(sl, cx + cw - pad_v - bw, y + 0.5, bw, bh,
                        anchor=MSO_ANCHOR.MIDDLE)
            abzac(tf, 'новое', 9, font=BODY, color=BG, bold=True, lead=1.0,
                  align=PP_ALIGN.CENTER, first=True)

        gnezdo = 0.72                    # место под название, у всех одно
        blok(sl, cx + pad_v, y + 1.08, cw - pad_v * 2, t, UB, 13.5, font=DISP,
             color=(GREEN if novoe else WHITE), bold=True, lead=1.22,
             max_strok=2, max_h=gnezdo, chto='агент %s' % t)
        blok(sl, cx + pad_v, y + 1.08 + gnezdo + 0.16, cw - pad_v * 2, d,
             IR, 12, color=MUTED, lead=1.5, max_strok=4, max_h=0.92,
             chto='агент, подпись %s' % t)

    # Выгода стоит здесь же, под агентами: отдельный слайд с тремя
    # числами только оттягивал ответ на вопрос «и что мне с этого».
    vy = y + ch + 0.46
    vzaz = 0.7
    vw = (CW - vzaz * 2) / 3
    for i, (v, t) in enumerate(VYGODY):
        cx = PAD + i * (vw + vzaz)
        if i:
            cherta(sl, cx - vzaz / 2, vy + 0.04, 0.012, 0.66)
        blok(sl, cx, vy, vw, v, UB, 23, font=DISP, color=LBLUE, bold=True,
             lead=1.12, max_strok=1, max_h=0.42, chto='выгода %s' % v)
        blok(sl, cx, vy + 0.46, vw, t, IR, 12.5, color=MUTED, lead=1.4,
             max_strok=2, max_h=0.52, chto='выгода, подпись %s' % v)


# ==================================================== 4. АВТОПУБЛИКАЦИЯ

# Площадки перечислены плитками, без фирменных значков: рисовать чужие
# логотипы от руки нельзя, а похожие «почти логотипы» на слайде
# выглядят хуже, чем честное название.
PLOSHCHADKI = ['Telegram', 'Instagram*', 'VK', 'Яндекс Дзен',
               'Одноклассники', 'Max']

GRAFIK = [
    'Публикации 5 дней в неделю',
    '2 экспертные статьи в месяц',
    'Формат и размер — под каждую площадку',
]


def slajd_4(prs):
    sl = novyj(prs); nomer(sl, 4)
    y = blok(sl, PAD, 0.72, CW, 'Платформа публикует сама',
             UB, 32, font=DISP, color=WHITE, bold=True, lead=1.18,
             kegli=[32, 29], max_strok=1)
    blok(sl, PAD, y + 0.26, 9.6,
         'Готовый материал уходит на площадки по расписанию. '
         'Ни выгрузок, ни ручного постинга, ни напоминаний.',
         IR, 15, color=MUTED, lead=1.5, max_strok=2, max_h=0.7)

    y = 2.5
    lw = 3.9
    vy = blok(sl, PAD, y - 0.16, lw, '6', UB, 96, font=DISP, color=LBLUE,
              bold=True, lead=1.0, max_strok=1, max_h=1.5)
    vy = blok(sl, PAD, vy + 0.08, lw, 'площадок в одной подписке',
              UB, 17, font=DISP, color=WHITE, bold=True, lead=1.25,
              max_strok=2, max_h=0.62)
    vy += 0.46
    for t in GRAFIK:
        n = len(perenos(t, IR, 13, (lw - 0.36) * 0.96))
        vys = n * 13 * 1.45 / 72.0
        kartinka(sl, ikonka('check', '4ADE80'), PAD, vy + 0.05, 0.2, 0.2)
        tf = nadpis(sl, PAD + 0.36, vy, lw - 0.36, vys + 0.08)
        abzac(tf, t, 13, font=BODY, color=MUTED, lead=1.45, first=True)
        vy += vys + 0.24

    rx = PAD + lw + 0.7
    rw = W - PAD - rx
    zaz = 0.24
    cw = (rw - zaz) / 2
    ch = 1.05
    # Две колонки, а не три: «Одноклассники» — длинное слово, и в узкой
    # плитке оно либо разрывается посередине, либо мельчает до нечитаемого.
    for i, p in enumerate(PLOSHCHADKI):
        cx = rx + (i % 2) * (cw + zaz)
        cy = y + (i // 2) * (ch + zaz)
        plitka(sl, cx, cy, cw, ch, fill=CARD, line=LINE, radius=0.16)
        pt, lines = podobrat(p, UB, [19, 18, 17, 16, 15], cw - 0.4, 0.7, 1.2, 1)
        vys = len(lines) * pt * 1.2 / 72.0
        tf = nadpis(sl, cx + 0.2, cy + (ch - vys) / 2, cw - 0.4, vys + 0.08)
        abzac(tf, p, pt, font=DISP, color=WHITE, bold=True, lead=1.2,
              align=PP_ALIGN.CENTER, first=True)

    # Сноска обязательна при любом упоминании Instagram в России.
    blok(sl, PAD, H - 0.62, CW,
         '* Instagram принадлежит компании Meta, признанной экстремистской '
         'организацией и запрещённой на территории Российской Федерации.',
         IR, 8.5, color=MUTED2, lead=1.3)


# ========================================================= 5. НОВОЕ В ПЛАТФОРМЕ

NOVOE = [
    ('new-video.jpg',   'Видео по сценарию', 'Опишите сцену — ролик соберётся сам'),
    ('new-dvojnik.jpg', 'Цифровой двойник',  'Реклама с вашим лицом и голосом'),
    ('new-lending.jpg', 'Сайт под заявки',   'Лендинг на семь стилей на выбор'),
    ('new-merch.jpg',   'Брендбук и мерч',   'Айдентика и макеты сувенирки'),
]


def slajd_5(prs):
    sl = novyj(prs); nomer(sl, 5)
    y = blok(sl, PAD, 0.72, CW, 'Новое в платформе',
             UB, 32, font=DISP, color=WHITE, bold=True, lead=1.18,
             kegli=[32, 29], max_strok=1)
    y = blok(sl, PAD, y + 0.26, 9.6,
             'Всё это входит в подписку и не оплачивается отдельно.',
             IR, 15, color=MUTED, lead=1.5, max_strok=1, max_h=0.4)

    y += 0.6
    zaz = 0.3
    cw = (CW - zaz * 3) / 4
    ih = 2.8                           # кадры крупнее: слайд держится на них
    for i, (fajl, t, d) in enumerate(NOVOE):
        cx = PAD + i * (cw + zaz)
        kartinka(sl, kadr(IMG + '/' + fajl, cw, ih, 'n-%d.png' % i, radius=0.18),
                 cx, y, cw, ih)
        gnezdo = 0.62                  # место под название, всегда одно
        blok(sl, cx, y + ih + 0.32, cw, t, UB, 16, font=DISP, color=WHITE,
             bold=True, lead=1.2, max_strok=2, max_h=gnezdo, chto='новое, %s' % t)
        blok(sl, cx, y + ih + 0.32 + gnezdo + 0.16, cw, d, IR, 12,
             color=MUTED2, lead=1.45, max_strok=3, max_h=0.8,
             chto='новое, подпись %s' % t)


# ============================================================= 6. ДЛЯ КОГО

# Девять ниш — те же, что на сайте, и с теми же значками. Под ними
# полоса «без ограничений по отраслям»: она снимает главный вопрос
# зала — «а у нас ниша другая».
NISHI = [
    ('cup',      'HoReCa'),
    ('scissors', 'Салоны красоты'),
    ('tooth',    'Стоматология'),
    ('flower',   'Цветочные салоны'),
    ('bag',      'Розница и услуги'),
    ('home',     'Товары для дома'),
    ('toy',      'Детские товары'),
    ('car',      'Авто и мотоиндустрия'),
    ('tools',    'Строительство и ремонт'),
]


def slajd_6(prs):
    sl = novyj(prs); nomer(sl, 6)
    y = blok(sl, PAD, 0.72, CW, 'Для кого',
             UB, 32, font=DISP, color=WHITE, bold=True, lead=1.18,
             kegli=[32, 29], max_strok=1)
    blok(sl, PAD, y + 0.26, 9.6,
         'Для каждой из этих ниш есть отдельная презентация с примерами '
         'запросов и цифрами.',
         IR, 15, color=MUTED, lead=1.5, max_strok=2, max_h=0.7)

    y = 2.26
    zaz = 0.2
    cw = (CW - zaz * 2) / 3
    ch = 0.92
    for i, (ik, t) in enumerate(NISHI):
        cx = PAD + (i % 3) * (cw + zaz)
        cy = y + (i // 3) * (ch + zaz)
        plitka(sl, cx, cy, cw, ch, fill=CARD, line=LINE, radius=0.16)
        znak(sl, cx + 0.2, cy + (ch - 0.56) / 2, 0.56, ik, '7FC4FF',
             fill=CARD2, pad=0.14)
        pt, lines = podobrat(t, UB, [15, 14, 13.5, 13, 12.5], cw - 1.1, 0.62,
                             1.22, 2)
        vys = len(lines) * pt * 1.22 / 72.0
        tf = nadpis(sl, cx + 0.92, cy + (ch - vys) / 2, cw - 1.1, vys + 0.08)
        abzac(tf, t, pt, font=DISP, color=WHITE, bold=True, lead=1.22,
              first=True)

    py = y + ch * 3 + zaz * 2 + 0.28
    ph = 1.06
    plitka(sl, PAD, py, CW, ph, fill=CARD, line=GREEN, radius=0.16, lw=1.4)
    znak(sl, PAD + 0.2, py + (ph - 0.56) / 2, 0.56, 'grid', '4ADE80',
         fill=CARD2, pad=0.14)
    ty = blok(sl, PAD + 0.92, py + 0.22, CW - 1.2, 'Без ограничений по отраслям',
              UB, 15, font=DISP, color=GREEN, bold=True, lead=1.22,
              max_strok=1, max_h=0.36)
    blok(sl, PAD + 0.92, ty + 0.12, CW - 1.2,
         'Модули изучают любую нишу с нуля — отрасль может быть узкой или редкой.',
         IR, 12.5, color=MUTED, lead=1.45, max_strok=1, max_h=0.28)


# =============================================================== 7. ЦЕНА

VHODIT = [
    'Полный цикл: тема, текст, картинка, видео, проверка, публикация',
    'Публикации 5 дней в неделю и 2 экспертные статьи',
    'Автопубликация на 6 площадках: Telegram, Instagram*, VK, Дзен, ОК, Max',
    'Видео по сценарию и цифровой двойник',
    'Сайт под заявки, брендбук и мерч',
    'Договор и закрывающие документы по законодательству РФ',
]


def slajd_7(prs):
    sl = novyj(prs); nomer(sl, 7)
    blok(sl, PAD, 0.72, CW, 'Одна подписка вместо агентства',
         UB, 32, font=DISP, color=WHITE, bold=True, lead=1.18,
         kegli=[32, 29, 26], max_strok=1)

    y = 2.3
    lw = 5.5
    vy = blok(sl, PAD, y, lw, '39 500 ₽', UB, 60, font=DISP, color=WHITE,
              bold=True, lead=1.08, max_strok=1, max_h=1.1)
    vy = blok(sl, PAD, vy + 0.16, lw, 'в месяц, цена фиксированная',
              IR, 15, color=MUTED2, lead=1.4)
    vy = blok(sl, PAD, vy + 0.46, lw,
              [('Экономия ', {'color': MUTED}),
               ('70 500 ₽', {'color': GREEN, 'bold': True}),
               (' каждый месяц', {'color': MUTED})],
              IS, 19, font=BODY, lead=1.3)
    blok(sl, PAD, vy + 0.18, lw, 'SEO-агентство за ту же работу — 110 000 ₽ в месяц',
         IR, 13, color=MUTED2, lead=1.4)

    rx = PAD + lw + 0.8
    rw = W - PAD - rx
    ry = blok(sl, rx, y + 0.1, rw, 'Что входит', UB, 19, font=DISP, color=WHITE,
              bold=True, lead=1.2, max_strok=1, max_h=0.42)
    ry += 0.4
    for t in VHODIT:
        n = len(perenos(t, IR, 13, (rw - 0.4) * 0.96))
        vys = n * 13 * 1.45 / 72.0
        kartinka(sl, ikonka('check', '4ADE80'), rx, ry + 0.05, 0.2, 0.2)
        tf = nadpis(sl, rx + 0.36, ry, rw - 0.36, vys + 0.08)
        abzac(tf, t, 13, font=BODY, color=MUTED, lead=1.45, first=True)
        ry += vys + 0.22

    # Сноска обязательна при любом упоминании Instagram в России.
    blok(sl, PAD, H - 0.62, CW,
         '* Instagram принадлежит компании Meta, признанной экстремистской '
         'организацией и запрещённой на территории Российской Федерации.',
         IR, 8.5, color=MUTED2, lead=1.3)


# ============================================================ 8. КОНТАКТЫ

def slajd_8(prs):
    sl = novyj(prs)
    kartinka(sl, kadr(IMG + '/hero-bg.jpg', W, H, 'final.png',
                      dark=0.46, left_wash=0.74), 0, 0, W, H)

    y = blok(sl, PAD, 1.7, 6.6, 'Посмотрим, как ваша ниша выглядит в ответах нейросетей',
             UB, 34, font=DISP, color=WHITE, bold=True, lead=1.16,
             kegli=[34, 31, 28], max_strok=3)
    y = blok(sl, PAD, y + 0.32, 6.2,
             'Бесплатно и без обязательств: проверим, называют ли нейросети '
             'вашу компанию — и кого называют вместо вас.',
             IR, 15.5, color=MUTED, lead=1.55)

    knopka(sl, PAD, y + 0.56, 3.7, 0.74, 'Получить разбор', ANALIZ, pt=15)
    tf = nadpis(sl, PAD + 4.0, y + 0.56, 3.0, 0.74, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, 'Откроется форма\nна сайте «Промптера»', 10.5, color=MUTED2,
          lead=1.35, first=True)

    # Справа — офис, а не конкретный человек: презентацию ведут
    # разные менеджеры, и каждый подставляет свой телефон, почту и
    # аккаунт — на обложке и здесь.
    kx = PAD + 7.5
    kw = W - PAD - kx
    ky, kh = 1.5, 4.5
    plitka(sl, kx, ky, kw, kh, fill=CARD, line=LINE2, radius=0.22)
    fw = kw - 0.84
    kartinka(sl, kadr(IMG + '/team.jpg', fw, 1.6, 'ofis.png', radius=0.16),
             kx + 0.42, ky + 0.42, fw, 1.6)
    ty = blok(sl, kx + 0.42, ky + 2.2, fw, 'Офис в Москве', UB, 17, font=DISP,
              color=WHITE, bold=True, lead=1.2, max_strok=1, max_h=0.42)
    ty = blok(sl, kx + 0.42, ty + 0.1, fw, 'Официальный партнёр по Москве и МО',
              IR, 11.5, color=MUTED2, lead=1.35, max_strok=1, max_h=0.26)

    ty += 0.34
    for ik, t, url in [('phone', TELEFON, 'tel:' + TELEFON.replace(' ', '').replace('-', '')),
                       ('mail', POCHTA, 'mailto:' + POCHTA),
                       ('tg', AKKAUNT, 'https://t.me/' + AKKAUNT.lstrip('@'))]:
        kartinka(sl, ikonka(ik, '7FC4FF'), kx + 0.42, ty + 0.04, 0.22, 0.22)
        tf = nadpis(sl, kx + 0.76, ty, fw - 0.34, 0.3)
        abzac(tf, t, 12.5, font=BODY, color=WHITE, lead=1.2, first=True)
        ssylka(tf._parent, url)
        ty += 0.4

    kartinka(sl, ASSETS + '/logo.png', PAD, H - 1.0, 0.42, 0.42)
    tf = nadpis(sl, PAD + 0.58, H - 0.94, 6.0, 0.3)
    abzac(tf, [('Prompter ', {}), ('Moscow', {'bold': True}),
               ('     prompter-ai.moscow', {'color': MUTED2, 'font': BODY})],
          13, font=DISP, color=WHITE, lead=1.1, first=True)


# ============================================================== СБОРКА

def proverit_znaki(prs):
    """Все ли знаки презентации есть в шрифтах.

    Один раз уже попался знак «галочка вниз»: в предпросмотре он
    рисовался подставным шрифтом и выглядел нормально, а у клиента
    вышел бы квадратик. Теперь сборка проверяет каждый знак по файлам
    шрифтов и ругается сразу.
    """
    import glob
    from fontTools.ttLib import TTFont

    karty = {os.path.basename(p): TTFont(p).getBestCmap()
             for p in glob.glob(os.path.join(SHRIFTY, '*.ttf'))}
    znaki = set()
    for sl in prs.slides:
        for sh in sl.shapes:
            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        znaki |= set(r.text)

    net = []
    for z in sorted(znaki):
        if z in ' \n\t':
            continue
        gde = [imya for imya, cm in karty.items() if ord(z) not in cm]
        if gde:
            net.append('%r (U+%04X) нет в: %s' % (z, ord(z), ', '.join(gde)))
    return net


def main():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    for i in range(1, VSEGO + 1):
        globals()['slajd_%d' % i](prs)
    net = proverit_znaki(prs)
    if net:
        print('ЗНАКИ БЕЗ БУКВ В ШРИФТЕ:')
        for x in net:
            print('  -', x)
    else:
        print('все знаки есть в шрифтах')

    put = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'obshchaya.pptx')
    prs.save(put)
    if MALO:
        print('НЕ ВЛЕЗЛО:')
        for m in MALO:
            print('  -', m)
    else:
        print('всё влезает в отведённое место')
    print('собрано:', put, '| слайдов:', VSEGO)
    return put


if __name__ == '__main__':
    main()
