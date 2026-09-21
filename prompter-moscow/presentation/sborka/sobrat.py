# -*- coding: utf-8 -*-
"""Сборка общей презентации «Промптер. Москва».

Презентация собирается с нуля, а не из старого файла. Палитра, шрифты,
значки и тексты взяты с сайта prompter-ai.moscow: цвета из style.css,
шрифты Unbounded и Inter — те же файлы, что подключены на странице,
значки вырезаны из спрайта в index.html.

Раздел «Как работает платформа» — схема цикла из девяти шагов, которую
недавно убрали с сайта: в презентации ей самое место.
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
IB  = ('Inter', 'b')

VSEGO = 13
SAJT  = 'https://prompter-ai.moscow'
ZAYAVKA = SAJT + '/zayavka.html?from=presentation-obshchaya'
ANALIZ  = SAJT + '/zayavka.html?from=presentation-analiz'


def novyj(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    fon(sl)
    return sl


def futer(sl, nomer):
    """Нижняя строка: знак, адрес сайта и номер страницы."""
    kartinka(sl, ASSETS + '/logo.png', PAD, H - 0.54, 0.23, 0.23)
    tf = nadpis(sl, PAD + 0.34, H - 0.53, 4.0, 0.24)
    abzac(tf, 'prompter-ai.moscow', 9.5, color=MUTED2, lead=1.0, first=True)
    tf = nadpis(sl, W - PAD - 2.0, H - 0.53, 2.0, 0.24)
    abzac(tf, '%02d / %02d' % (nomer, VSEGO), 9.5, color=MUTED2, lead=1.0,
          align=PP_ALIGN.RIGHT, first=True)


def _plain(x):
    """Текст без разметки — для измерения ширины."""
    if isinstance(x, str):
        return x
    return ''.join(k if isinstance(k, str) else k[0] for k in x)


MALO = []     # сюда попадает всё, что не влезло: печатаем в конце сборки


def blok(sl, x, y, w, text, key, size, font=BODY, color=WHITE, bold=False,
         lead=1.42, align=PP_ALIGN.LEFT, kegli=None, max_strok=None,
         max_h=None, chto=''):
    """Абзац с посчитанной высотой. Возвращает координату низа.

    Высоту не задаём на глаз: строки считаются по файлу шрифта. Если
    передан max_h — сколько места осталось внутри карточки, — кегль сам
    уменьшается до того, при котором текст туда влезает. Именно этой
    проверки не хватало в первой сборке: текст вылезал за карточки.
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
        MALO.append('%s: не влезает, надо %.2f\u2033, есть %.2f\u2033 — %s'
                    % (chto or 'блок', h, max_h, plain[:60]))
    tf = nadpis(sl, x, y, w, h + 0.08)
    abzac(tf, text, size, font=font, color=color, bold=bold, lead=lead,
          align=align, first=True)
    return y + h


def ostatok(cy, ch, y, pad=0.36):
    """Сколько высоты осталось внутри карточки от y до её низа."""
    return cy + ch - pad - y


def shapka(sl, zag, lead=None, nadzag=None, lead_w=9.8, y=0.56):
    """Заголовок раздела и подводка под ним. Возвращает низ шапки."""
    if nadzag:
        blok(sl, PAD, y, CW, nadzag.upper(), IS, 10, font=BODY, color=LBLUE,
             bold=True, lead=1.0)
        y += 0.32
    y = blok(sl, PAD, y, CW, zag, UB, 24, font=DISP, color=WHITE, bold=True,
             lead=1.18, kegli=[24, 22, 20, 18], max_strok=2)
    if lead:
        y = blok(sl, PAD, y + 0.2, lead_w, lead, IR, 13.5, color=MUTED,
                 lead=1.45, kegli=[13.5, 12.5, 11.5], max_strok=3)
    return y


def znak(sl, x, y, d, imya, cvet='7FC4FF', fill=None, pad=0.22):
    """Значок сайта в круглой подложке."""
    if fill is not None:
        s = plitka(sl, x, y, d, d, fill=fill, line=None, radius=d / 2)
    kartinka(sl, ikonka(imya, cvet), x + pad, y + pad, d - pad * 2, d - pad * 2)


def strelka(sl, x, y, h, nazad=False, cvet=LINE2):
    """Шеврон между карточками: показывает, куда идёт поток."""
    tf = nadpis(sl, x, y, 0.3, h, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, '‹' if nazad else '›', 19, font=BODY, color=cvet, bold=True,
          lead=1.0, align=PP_ALIGN.CENTER, first=True)


# ============================================================ 01. ОБЛОЖКА

def slajd_01(prs):
    sl = novyj(prs)
    kartinka(sl, kadr(IMG + '/hero-bg.jpg', W, H, 'oblozhka.png',
                      dark=0.30, left_wash=0.82), 0, 0, W, H)

    # Знак и название — той же связкой, что в шапке сайта.
    kartinka(sl, ASSETS + '/logo.png', PAD, 0.52, 0.44, 0.44)
    tf = nadpis(sl, PAD + 0.6, 0.6, 5.0, 0.36)
    abzac(tf, [('Prompter ', {'bold': False}), ('Moscow', {'bold': True})],
          15, font=DISP, color=WHITE, lead=1.1, first=True)

    y = blok(sl, PAD, 3.24, 10.7,
             'Комплексное GEO- и SEO-продвижение бизнеса с помощью ИИ',
             UB, 30, font=DISP, color=WHITE, bold=True, lead=1.16,
             kegli=[30, 28, 26], max_strok=2)
    y = blok(sl, PAD, y + 0.26, 8.4,
             'Делаем ваш бизнес заметным в нейровыдаче и поисковых системах.',
             IR, 17, color=MUTED, lead=1.4)

    # Плашка партнёрства: на сайте она стоит первым элементом первого
    # экрана, и в презентации это тоже первое, что стоит сказать.
    ph = 0.94
    py = y + 0.46
    plitka(sl, PAD, py, 7.9, ph, fill=CARD, line=LINE2, radius=0.16)
    znak(sl, PAD + 0.26, py + (ph - 0.5) / 2, 0.5, 'certificate', '7FC4FF', pad=0.05)
    tf = nadpis(sl, PAD + 0.92, py, 6.8, ph, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, 'Официальный партнёр разработчика платформы — IT-компании '
              '«Промптер» — по Москве и МО.', 11.5, color=MUTED, lead=1.35, first=True)
    abzac(tf, 'Лицензионный договор № 54-ПРТ', 11.5, color=LBLUE, bold=True,
          lead=1.35, space_before=3)

    tf = nadpis(sl, PAD, H - 0.62, CW, 0.3)
    abzac(tf, [('prompter-ai.moscow', {'color': WHITE, 'bold': True}),
               ('     +7 906 758-77-77     prompter.moscow@mail.ru     @Prompter_mos',
                {'color': MUTED2})],
          11.5, font=BODY, lead=1.1, first=True)


# ============================================== 02. РЫНОК И БЕСПЛАТНЫЙ АНАЛИЗ

BYLO_STALO = [
    ('Было', 'Десять синих ссылок. Человек листает выдачу и выбирает сам.', MUTED2),
    ('Стало', 'Один ответ нейросети и два-три названия. Кого назвали — к тому и пошли.', LBLUE),
]


def slajd_02(prs):
    sl = novyj(prs); futer(sl, 2)
    y = shapka(sl, 'Рынок изменился: клиентов ищут нейросети',
               'Пользователь больше не листает десять синих ссылок. Он спрашивает '
               'нейросеть и получает готовый ответ с двумя-тремя названиями компаний.',
               lead_w=10.4)
    y += 0.34

    # Слева — что именно поменялось, справа картинка, внизу во всю
    # ширину — бесплатное предложение. Оно идёт вторым слайдом
    # намеренно: с него начинается разговор.
    lw = 7.1
    ih = 2.06
    for i, (t, d, c) in enumerate(BYLO_STALO):
        cy = y + i * (ih / 2 + 0.16)
        ch = ih / 2
        plitka(sl, PAD, cy, lw, ch, fill=CARD, line=LINE, radius=0.18)
        tf = nadpis(sl, PAD + 0.42, cy, 1.1, ch, anchor=MSO_ANCHOR.MIDDLE)
        abzac(tf, t, 13, font=DISP, color=c, bold=True, lead=1.1, first=True)
        tf = nadpis(sl, PAD + 1.6, cy, lw - 2.0, ch, anchor=MSO_ANCHOR.MIDDLE)
        abzac(tf, d, 12.5, font=BODY, color=MUTED, lead=1.45, first=True)

    kartinka(sl, kadr(IMG + '/neurons.jpg', CW - lw - 0.3, ih, 'nejrony.png',
                      radius=0.18), PAD + lw + 0.3, y, CW - lw - 0.3, ih)

    # Бесплатное предложение — полосой во всю ширину.
    by = y + ih + 0.36
    bh = 6.62 - by
    plitka(sl, PAD, by, CW, bh, fill=CARD2, line=LINE2, radius=0.22)
    tx, tw = PAD + 0.56, 7.5
    ty = blok(sl, tx, by + 0.46, tw, 'БЕСПЛАТНО', IS, 10.5, color=GREEN, bold=True,
              lead=1.0)
    ty = blok(sl, tx, ty + 0.2, tw, 'Проверьте ваш бизнес в нейровыдаче',
              UB, 18, font=DISP, color=WHITE, bold=True, lead=1.2,
              max_strok=1, max_h=1.0, chto='02 заголовок проверки')
    blok(sl, tx, ty + 0.2, tw,
         'Посмотрим, называют ли нейросети вашу компанию по запросам вашей ниши — '
         'и кого называют вместо вас. Пришлём разбор с наглядной картинкой. '
         'Без обязательств.', IR, 13, color=MUTED, lead=1.5,
         max_h=ostatok(by, bh, ty + 0.2, 0.4), chto='02 текст проверки')

    bw, bh2 = 3.5, 0.68
    bx = PAD + CW - bw - 0.56
    knopka = plitka(sl, bx, by + (bh - bh2) / 2, bw, bh2, fill=BLUE, line=None,
                    radius=bh2 / 2)
    ssylka(knopka, ANALIZ)
    tf = nadpis(sl, bx, by + (bh - bh2) / 2, bw, bh2, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, 'Получить бесплатный анализ', 13, font=BODY, color=WHITE,
          bold=True, lead=1.0, align=PP_ALIGN.CENTER, first=True)
    ssylka(tf._parent, ANALIZ)


# ====================================================== 03. ЧТО ЗА ПЛАТФОРМА

def slajd_03(prs):
    sl = novyj(prs); futer(sl, 3)
    y = shapka(sl, 'Полный цикл продвижения внутри одной платформы') + 0.38
    hh = 6.62 - y

    plitka(sl, PAD, y, 5.3, hh, fill=CARD, line=LINE, radius=0.2)
    kartinka(sl, ASSETS + '/logo-full.png', PAD + (5.3 - 1.61) / 2, y + 0.5, 1.61, 2.2)
    blok(sl, PAD + 0.46, y + 3.06, 4.38,
         'Платформа ведёт полный цикл продвижения: от идеи и сбора данных до '
         'проверки текста, фото, видео и автономной публикации на площадках. '
         'Вам не нужно ставить задачи, согласовывать материалы и следить за сроками.',
         IR, 13.5, color=MUTED, lead=1.55, align=PP_ALIGN.CENTER,
         max_h=ostatok(y, hh, y + 3.06, 0.4), chto='03 текст платформы')

    fakty = [
        ('217', 'ИИ-модулей внутри платформы',
         'Каждый отвечает за свой участок работы: темы, тексты, фото, видео, '
         'проверка фактов, оформление, публикация, отчётность.'),
        ('GEO', 'Фокус на нейровыдаче',
         'Мы работаем на то, чтобы вашу компанию называли нейросети, и '
         'параллельно усиливаем классические позиции в поиске.'),
    ]
    fx, fw = PAD + 5.6, CW - 5.6
    fh = (hh - 0.3) / 2
    for i, (v, t, d) in enumerate(fakty):
        fy = y + i * (fh + 0.3)
        plitka(sl, fx, fy, fw, fh, fill=CARD, line=LINE, radius=0.2)
        blok(sl, fx + 0.5, fy + 0.38, 2.6, v, UB, 34, font=DISP, color=LBLUE,
             bold=True, lead=1.05)
        ty = blok(sl, fx + 0.5, fy + 1.06, fw - 1.0, t, UB, 16, font=DISP,
                  color=WHITE, bold=True, lead=1.2, max_strok=1, max_h=0.36)
        blok(sl, fx + 0.5, ty + 0.22, fw - 1.0, d, IR, 13, color=MUTED2, lead=1.5,
             max_h=ostatok(fy, fh, ty + 0.22, 0.32), chto='03 факт %s' % v)


# ===================================== 04. КАК РАБОТАЕТ ПЛАТФОРМА: ЦИКЛ

# Девять шагов идут змейкой: верхний ряд слева направо, нижний справа
# налево, и слева внизу стрелка возвращает к началу. Так видно, что это
# кольцо, а не список с концом. Публикация и статистика выделены
# зелёным: ради них цикл и существует.
CIKL = [
    ('1', 'Информация о компании', 'Бизнес, продукты, аудитория, бренд'),
    ('2', 'Исследование',          'Компания, рынок и аудитория'),
    ('3', 'Стратегия',             'Направления, каналы и тактики'),
    ('4', 'Контент-план',          'Темы, рубрики и последовательность'),
    ('5', 'Текст',                 'Посты, сценарии и CTA'),
    ('6', 'Визуал',                'Изображения, видео'),
    ('7', 'Проверка',              'Логика, ошибки и соответствие бренду'),
    ('8', 'Публикация',            'Размещение в соцсетях'),
    ('9', 'Статистика',            'Охваты, переходы, реакции, обращения'),
]


def slajd_04(prs):
    sl = novyj(prs); futer(sl, 4)
    y = shapka(
        sl, 'Как работает платформа «Промптер»',
        [('Платформа объединяет ', {}), ('исследование', {'color': WHITE, 'bold': True}),
         (', ', {}), ('стратегию', {'color': WHITE, 'bold': True}),
         (', ', {}), ('создание', {'color': WHITE, 'bold': True}),
         (', ', {}), ('проверку', {'color': WHITE, 'bold': True}),
         (', ', {}), ('публикацию', {'color': WHITE, 'bold': True}),
         (' и ', {}), ('анализ', {'color': WHITE, 'bold': True}),
         (' контента. Цикл повторяется неделя за неделей, а результат обычно '
          'виден на третьем месяце работы.', {})],
        lead_w=10.4)
    y += 0.42

    kol, zaz = 5, 0.2
    cw = (CW - zaz * (kol - 1)) / kol
    ch = (6.62 - y - 0.5) / 2
    ry = [y, y + ch + 0.5]

    def karta(i, cx, cy):
        n, t, d = CIKL[i]
        vyhod = i >= 7                       # публикация и статистика
        c = GREEN if vyhod else LBLUE
        plitka(sl, cx, cy, cw, ch, fill=CARD, line=(GREEN if vyhod else LINE),
               radius=0.16, lw=(1.4 if vyhod else 1.0))
        blok(sl, cx + 0.26, cy + 0.26, 0.8, n, UB, 15, font=DISP, color=c,
             bold=True, lead=1.0)
        ty = blok(sl, cx + 0.26, cy + 0.66, cw - 0.52, t, UB, 11.5, font=DISP,
                  color=WHITE, bold=True, lead=1.2, max_strok=2, max_h=0.5,
                  chto='04 шаг %s' % n)
        blok(sl, cx + 0.26, ty + 0.18, cw - 0.52, d, IR, 10, color=MUTED2,
             lead=1.42, max_h=ostatok(cy, ch, ty + 0.18, 0.26), chto='04 подпись %s' % n)

    for i in range(5):
        cx = PAD + i * (cw + zaz)
        karta(i, cx, ry[0])
        if i < 4:
            strelka(sl, cx + cw - 0.02, ry[0], ch)

    for poz, i in enumerate([8, 7, 6, 5]):
        cx = PAD + (poz + 1) * (cw + zaz)
        karta(i, cx, ry[1])
        strelka(sl, cx - zaz - 0.04, ry[1], ch, nazad=True)

    vx, vy = PAD, ry[1]
    plitka(sl, vx, vy, cw, ch, fill=None, line=LINE2, radius=0.16)
    znak(sl, vx + (cw - 0.66) / 2, vy + 0.36, 0.66, 'refresh', '7FC4FF', pad=0.06)
    ty = blok(sl, vx + 0.2, vy + 1.18, cw - 0.4, 'Новый цикл', UB, 12.5, font=DISP,
              color=LBLUE, bold=True, lead=1.2, align=PP_ALIGN.CENTER)
    blok(sl, vx + 0.2, ty + 0.14, cw - 0.4, 'и так неделя за неделей', IR, 10,
         color=MUTED2, lead=1.3, align=PP_ALIGN.CENTER,
         max_h=ostatok(vy, ch, ty + 0.14, 0.2))

    # Поворот потока с верхнего ряда на нижний — по правому краю.
    tf = nadpis(sl, W - PAD - 0.42, ry[0] + ch, 0.42, 0.5, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, '⌄', 22, font=BODY, color=LINE2, bold=True, lead=1.0,
          align=PP_ALIGN.CENTER, first=True)


# ============================================== 05. ЦИКЛ ОБУЧЕНИЯ

UCHEBA = [
    ('Корректировка клиента', 'Что изменить в тексте, визуале, стиле или призыве к действию'),
    ('Настройка контекста', 'Правила бренда, медиатека, tone of voice, референсы'),
    ('ИИ-сотрудники учитывают настройки',
     'Следующий контент создаётся с учётом накопленного контекста'),
    ('Меньше правок руками', 'Система становится точнее и автономнее'),
]


def slajd_05(prs):
    sl = novyj(prs); futer(sl, 5)
    y = shapka(sl, 'Цикл обучения на основе настроек и обратной связи',
               'Платформа не просто повторяет цикл — она запоминает ваши правки. '
               'Каждое замечание меняет не одну публикацию, а все следующие.',
               lead_w=9.4)
    y += 0.46

    kol, zaz = 4, 0.34
    cw = (CW - zaz * (kol - 1)) / kol
    nh = 0.82
    ch = 6.62 - y - nh - 0.34
    for i, (t, d) in enumerate(UCHEBA):
        cx = PAD + i * (cw + zaz)
        itog = (i == kol - 1)
        plitka(sl, cx, y, cw, ch, fill=CARD, line=(GREEN if itog else LINE),
               radius=0.2, lw=(1.4 if itog else 1.0))
        blok(sl, cx + 0.34, y + 0.42, 0.9, '0%d' % (i + 1), IS, 11,
             color=(GREEN if itog else MUTED2), bold=True, lead=1.0)
        ty = blok(sl, cx + 0.34, y + 0.9, cw - 0.68, t, UB, 14, font=DISP,
                  color=(GREEN if itog else WHITE), bold=True, lead=1.22,
                  max_strok=3, max_h=1.4, chto='05 шаг %d' % (i + 1))
        blok(sl, cx + 0.34, ty + 0.26, cw - 0.68, d, IR, 11.5, color=MUTED2,
             lead=1.5, max_h=ostatok(y, ch, ty + 0.26, 0.4), chto='05 подпись %d' % (i + 1))
        if i < kol - 1:
            strelka(sl, cx + cw + 0.02, y, ch)

    ny = y + ch + 0.34
    plitka(sl, PAD, ny, CW, nh, fill=CARD2, line=LINE, radius=0.16)
    tf = nadpis(sl, PAD + 0.44, ny, CW - 0.88, nh, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, [('Корректировка не исчезает после одной публикации — ', {'color': MUTED}),
               ('она работает на следующие циклы.', {'color': LBLUE, 'bold': True})],
          13, font=BODY, lead=1.3, align=PP_ALIGN.CENTER, first=True)


# ====================================================== 06. ЧЕТЫРЕ ИИ-АГЕНТА

AGENTY = [
    ('pencil', 'AI-копирайтер',
     'Создаёт публикации о компании: тексты, карточки, экспертные посты в '
     'едином стиле бренда для всех площадок.'),
    ('target', 'AI-маркетолог',
     'Изучает нишу, конкурентов и запросы пользователей в нейросетях, строит '
     'контент-стратегию и определяет ключевые запросы для присутствия бренда '
     'в нейровыдаче.'),
    ('send', 'AI СММ-менеджер',
     'Проверяет контент на соответствие бренду и требованиям GEO-индексации, '
     'следит за присутствием бренда в нейро- и поисковой выдаче и правит план '
     'в реальном времени.'),
    ('palette', 'AI-дизайнер',
     'Создаёт визуальные материалы, адаптированные к стилистике бренда и '
     'требованиям каждой площадки.'),
]


def slajd_06(prs):
    sl = novyj(prs); futer(sl, 6)
    y = shapka(sl, '4 ваших ИИ-агента вместо digital-агентства',
               'Каждый ИИ-агент закрывает роль, которую в агентстве занимает '
               'отдельный человек с отдельной зарплатой.', lead_w=8.6)
    y += 0.42

    cw = (CW - 0.32) / 2
    ch = (6.62 - y - 0.3) / 2
    for i, (ik, t, d) in enumerate(AGENTY):
        cx = PAD + (i % 2) * (cw + 0.32)
        cy = y + (i // 2) * (ch + 0.3)
        plitka(sl, cx, cy, cw, ch, fill=CARD, line=LINE, radius=0.2)
        znak(sl, cx + 0.44, cy + 0.4, 0.66, ik, '7FC4FF', fill=CARD2, pad=0.17)
        tf = nadpis(sl, cx + 1.26, cy + 0.4, cw - 1.7, 0.66, anchor=MSO_ANCHOR.MIDDLE)
        abzac(tf, t, 17, font=DISP, color=WHITE, bold=True, lead=1.15, first=True)
        blok(sl, cx + 0.44, cy + 1.2, cw - 0.88, d, IR, 13, color=MUTED, lead=1.55,
             max_h=ostatok(cy, ch, cy + 1.2, 0.28), chto='06 агент %s' % t)


# ================================================== 07. КЛЮЧЕВАЯ ТЕХНОЛОГИЯ

RELSY = [
    ('01', 'sparkles', 'Генерация',
     'Платформа собирает данные по нише и готовит материал под конкретный '
     'запрос клиента.', False),
    ('02', 'shield', 'Модерация ИИ',
     'Отдельный модуль проверяет факты, цифры и формулировки. Слабый материал '
     'не проходит дальше.', False),
    ('03', 'send', 'Автопубликация',
     'Готовый материал сам уходит на площадки по расписанию. Ваше участие не '
     'требуется.', True),
    ('04', 'trend', 'Рост в нейровыдаче',
     'Материалы индексируются, и нейросети начинают опираться на них, отвечая '
     'на запросы клиентов.', False),
]


def slajd_07(prs):
    sl = novyj(prs); futer(sl, 7)
    y = shapka(sl,
               [('Не просто генерирует — ', {}),
                ('сама публикует', {'color': LBLUE})],
               'Большинство AI-сервисов отдают вам текст и на этом заканчивают. '
               'Дальше кто-то в компании должен всё разместить руками. Мы '
               'закрываем этот шаг платформой: от идеи до опубликованного '
               'материала не нужен ни один человек с вашей стороны.',
               nadzag='Ключевая технология', lead_w=10.2)
    y += 0.44

    zaz, fh = 0.28, 0.84
    cw = (CW - zaz * 3) / 4
    ch = 6.62 - y - fh - 0.34
    for i, (n, ik, t, d, klyuch) in enumerate(RELSY):
        cx = PAD + i * (cw + zaz)
        plitka(sl, cx, y, cw, ch, fill=(CARD2 if klyuch else CARD),
               line=(BLUE if klyuch else LINE), radius=0.2, lw=(1.6 if klyuch else 1.0))
        blok(sl, cx + 0.34, y + 0.36, 0.9, n, UB, 13, font=DISP,
             color=(LBLUE if klyuch else MUTED2), bold=True, lead=1.0)
        znak(sl, cx + cw - 0.92, y + 0.3, 0.6, ik, '7FC4FF', pad=0.1)
        ty = blok(sl, cx + 0.34, y + 0.94, cw - 0.68, t, UB, 14.5, font=DISP,
                  color=WHITE, bold=True, lead=1.2, max_strok=2, max_h=0.62,
                  chto='07 шаг %s' % n)
        # Под ключевым шагом внизу стоит плашка — оставляем ей место.
        niz = 0.34 + (0.48 if klyuch else 0.0)
        blok(sl, cx + 0.34, ty + 0.22, cw - 0.68, d, IR, 11.5, color=MUTED2,
             lead=1.5, max_h=ostatok(y, ch, ty + 0.22, niz), chto='07 текст %s' % n)
        if klyuch:
            fw = 1.74
            plitka(sl, cx + 0.34, y + ch - 0.66, fw, 0.36, fill=BLUE, line=None,
                   radius=0.18)
            tf = nadpis(sl, cx + 0.34, y + ch - 0.66, fw, 0.36, anchor=MSO_ANCHOR.MIDDLE)
            abzac(tf, 'Этого нет у других', 9.5, font=BODY, color=WHITE, bold=True,
                  lead=1.0, align=PP_ALIGN.CENTER, first=True)

    fy = y + ch + 0.34
    plitka(sl, PAD, fy, CW, fh, fill=None, line=LINE2, radius=0.16)
    tf = nadpis(sl, PAD + 0.44, fy, CW - 0.88, fh, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, [('Вам не нужно писать, согласовывать и публиковать. ', {'color': MUTED}),
               ('Минимум вашего времени в цикле.', {'color': LBLUE, 'bold': True})],
          13.5, font=BODY, lead=1.3, align=PP_ALIGN.CENTER, first=True)


# ================================================== 08. НОВЫЕ ФУНКЦИИ

def slajd_08(prs):
    sl = novyj(prs); futer(sl, 8)
    y = shapka(sl, 'Новые функции платформы',
               'Всё перечисленное входит в подписку и не оплачивается отдельно. '
               'Отдельный подрядчик на видео, сайт и фирменный стиль не нужен.',
               lead_w=10.4)
    y += 0.38

    # Раскладка повторяет сетку сайта: видео и двойник — то, ради чего
    # раздел существует, поэтому они крупные, сайт и мерч идут полосой.
    dostupno = 6.62 - y
    h2 = 1.62
    h1 = dostupno - h2 - 0.24

    # Видео: текст слева, кадры справа. Высота кадра посчитана по
    # пропорциям самого файла, чтобы кадрирование ничего не срезало.
    aw, iw = 7.9, 3.2
    plitka(sl, PAD, y, aw, h1, fill=CARD, line=LINE, radius=0.2)
    vih = iw * 356 / 782.0
    kartinka(sl, kadr(IMG + '/new-video.jpg', iw, vih, 'f-video.png', radius=0.14),
             PAD + aw - iw - 0.44, y + (h1 - vih) / 2, iw, vih)
    tw = aw - iw - 0.44 * 2 - 0.34
    ty = blok(sl, PAD + 0.44, y + 0.44, tw, 'Видео по сценарию и фотографии',
              UB, 15, font=DISP, color=WHITE, bold=True, lead=1.22,
              max_strok=3, max_h=1.0, chto='08 видео заголовок')
    ty = blok(sl, PAD + 0.44, ty + 0.18, tw,
              'Опишите сцену, и ролик соберётся сам. Без камеры, съёмочной '
              'группы и монтажа.', IR, 11.5, color=MUTED2, lead=1.5,
              max_h=1.1, chto='08 видео текст')
    blok(sl, PAD + 0.44, ty + 0.18, tw,
         '6, 10 или 15 секунд   ·   9:16, 16:9 и 1:1\n'
         'Стандарт и Про   ·   первый кадр — ваше фото',
         IR, 10.5, color=LBLUE, lead=1.5,
         max_h=ostatok(y, h1, ty + 0.18, 0.34), chto='08 видео форматы')

    # Двойник: сначала текст, кадр занимает всё, что осталось снизу —
    # тогда в карточке не остаётся пустого места.
    bx, bw = PAD + aw + 0.3, CW - aw - 0.3
    plitka(sl, bx, y, bw, h1, fill=CARD, line=LINE, radius=0.2)
    ty = blok(sl, bx + 0.44, y + 0.44, bw - 0.88, 'Цифровой двойник',
              UB, 15, font=DISP, color=WHITE, bold=True, lead=1.2,
              max_strok=1, max_h=0.36)
    ty = blok(sl, bx + 0.44, ty + 0.16, bw - 0.88,
              'Видеореклама с вашим лицом и голосом. Двойник говорит как живой.',
              IR, 11, color=MUTED2, lead=1.45, max_h=0.6, chto='08 двойник текст')
    dih = y + h1 - 0.44 - (ty + 0.24)
    kartinka(sl, kadr(IMG + '/new-dvojnik.jpg', bw - 0.88, dih, 'f-dvojnik.png',
                      radius=0.14), bx + 0.44, ty + 0.24, bw - 0.88, dih)

    # Нижняя полоса: сайт под заявки и брендбук.
    ny = y + h1 + 0.24
    polosy = [
        ('new-lending.jpg', 'Создание сайта под заявки',
         'Отдельный лендинг, который собирает заявки. Семь готовых стилей '
         'страницы.', 6.0),
        ('new-merch.jpg', 'Брендбук и мерч',
         'Фирменный стиль и макеты сувенирки: айдентика, мерч, брендбук.',
         CW - 6.0 - 0.3),
    ]
    px = PAD
    for i, (fajl, t, d, pw) in enumerate(polosy):
        plitka(sl, px, ny, pw, h2, fill=CARD, line=LINE, radius=0.2)
        piw = 1.9
        kartinka(sl, kadr(IMG + '/' + fajl, piw, h2 - 0.64, 'f-%d.png' % i, radius=0.14),
                 px + 0.32, ny + 0.32, piw, h2 - 0.64)
        tx = px + 0.32 + piw + 0.32
        twi = pw - (tx - px) - 0.36
        ty = blok(sl, tx, ny + 0.34, twi, t, UB, 13.5, font=DISP, color=WHITE,
                  bold=True, lead=1.2, max_strok=2, max_h=0.56,
                  chto='08 полоса %s' % t)
        blok(sl, tx, ty + 0.16, twi, d, IR, 11, color=MUTED2, lead=1.45,
             max_h=ostatok(ny, h2, ty + 0.16, 0.28), chto='08 текст %s' % t)
        px += pw + 0.3


# ====================================================== 09. КЛЮЧЕВЫЕ ВЫГОДЫ

VYGODY = [
    ('01', 'clock', 'в 4 раза', 'Экономия времени',
     'Не нужно писать техзадания и согласовывать публикации. Платформа ведёт '
     'весь цикл сама, а вы возвращаетесь к своей основной работе.'),
    ('02', 'wallet', 'в 3 раза', 'Оптимизация расходов на СММ',
     'Стоимость известна заранее и не растёт от количества правок и задач. '
     'Бюджет уходит на результат, а не на переписку с подрядчиками.'),
    ('03', 'users', '0 человек', 'Без найма штата',
     'Не нужно искать копирайтера, SEO-специалиста и дизайнера и платить им '
     'каждый месяц. Их роли закрывают ИИ-агенты.'),
]


def slajd_09(prs):
    sl = novyj(prs); futer(sl, 9)
    y = shapka(sl, 'Ключевые выгоды для вашего бизнеса',
               'Три вещи, ради которых бизнес переходит на платформу.')
    y += 0.46

    zaz = 0.32
    cw = (CW - zaz * 2) / 3
    ch = 6.62 - y
    for i, (n, ik, v, t, d) in enumerate(VYGODY):
        cx = PAD + i * (cw + zaz)
        plitka(sl, cx, y, cw, ch, fill=CARD, line=LINE, radius=0.22)
        znak(sl, cx + 0.46, y + 0.46, 0.68, ik, '7FC4FF', fill=CARD2, pad=0.18)
        tf = nadpis(sl, cx + cw - 1.0, y + 0.46, 0.54, 0.4)
        abzac(tf, n, 12, font=DISP, color=MUTED2, bold=True, lead=1.0,
              align=PP_ALIGN.RIGHT, first=True)
        vy = blok(sl, cx + 0.46, y + 1.5, cw - 0.92, v, UB, 30, font=DISP,
                  color=LBLUE, bold=True, lead=1.1, max_strok=1, max_h=0.6)
        ty = blok(sl, cx + 0.46, vy + 0.28, cw - 0.92, t, UB, 15, font=DISP,
                  color=WHITE, bold=True, lead=1.22, max_strok=2, max_h=0.62)
        blok(sl, cx + 0.46, ty + 0.28, cw - 0.92, d, IR, 12.5, color=MUTED2,
             lead=1.55, max_h=ostatok(y, ch, ty + 0.28, 0.46), chto='09 выгода %s' % t)


# ============================================================== 10. ЦЕНА

# Четыре новых пункта помечены значком «new» — так же, как в списке
# «Что входит в подписку» на сайте. Текст этих четырёх подобран так,
# чтобы он умещался в одну строку: тогда ширину строки можно посчитать
# точно и поставить значок ровно за последним словом.
PODPISKA = [
    ([('Полный AI-цикл', {'color': LBLUE, 'bold': True}),
      (': от идеи и текста до модерации и публикации', {})], False),
    ([('Публикации ', {}), ('5', {'color': LBLUE, 'bold': True}),
      (' дней в неделю', {})], False),
    ([('2', {'color': LBLUE, 'bold': True}), (' экспертные статьи в неделю', {})], False),
    ([('Автопубликация', {'color': LBLUE, 'bold': True}),
      (' на ', {}), ('6', {'color': LBLUE, 'bold': True}),
      (' площадках: Telegram, Instagram*, VK, Яндекс Дзен, Одноклассники, Max', {})], False),
    ([('Для других площадок — готовый контент для самостоятельной публикации', {})], False),
    ([('Видео по сценарию', {'color': LBLUE, 'bold': True}), (' и фотографии', {})], True),
    ([('Цифровой двойник', {'color': LBLUE, 'bold': True}),
      (': видеореклама с вашим лицом', {})], True),
    ([('Сайт под заявки', {'color': LBLUE, 'bold': True}),
      (': семь стилей страницы', {})], True),
    ([('Брендбук и мерч', {'color': LBLUE, 'bold': True}),
      (': айдентика и макеты сувенирки', {})], True),
    ([('Работа по законодательству РФ, договор и закрывающие документы', {})], False),
]


def _shirina_kuskov(kuski, pt):
    """Ширина строки из разнородных кусков: жирные считаем жирным файлом."""
    w = 0.0
    for t, o in kuski:
        w += shirina(t, IS if o.get('bold') else IR, pt)
    return w


def slajd_10(prs):
    sl = novyj(prs); futer(sl, 10)
    y = shapka(sl, 'Комплексное решение по фиксированной цене') + 0.4
    hh = 6.36 - y

    # Левая карточка — деньги.
    lw = 4.9
    plitka(sl, PAD, y, lw, hh, fill=CARD, line=LINE, radius=0.22)
    ix = PAD + 0.5
    blok(sl, ix, y + 0.54, lw - 1.0, 'ЭКОНОМИЯ КАЖДЫЙ МЕСЯЦ', IS, 10.5,
         color=MUTED2, bold=True, lead=1.0)
    blok(sl, ix, y + 0.98, lw - 1.0, '70 000 ₽', UB, 44, font=DISP, color=GREEN,
         bold=True, lead=1.08, max_strok=1, max_h=1.0)
    ry = y + 2.2
    s = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(ix), Inches(ry),
                            Inches(lw - 1.0), Inches(0.012))
    s.fill.solid(); s.fill.fore_color.rgb = LINE
    s.line.fill.background(); s.shadow.inherit = False

    ty = blok(sl, ix, ry + 0.46, lw - 1.0,
              [('Промптер', {'color': WHITE, 'bold': True}),
               ('   ', {}), ('29 500 ₽', {'color': LBLUE, 'bold': True}),
               (' / мес', {'color': LBLUE})], IS, 17, font=BODY, lead=1.25)
    ty = blok(sl, ix, ty + 0.28, lw - 1.0,
              [('SEO-агентство', {}), ('   100 000 ₽ / мес', {})],
              IR, 14, font=BODY, color=MUTED2, lead=1.25)
    blok(sl, ix, ty + 0.38, lw - 1.0,
         'Цена фиксированная: она не растёт от количества правок, задач и '
         'площадок.', IR, 11.5, color=MUTED2, lead=1.5,
         max_h=ostatok(y, hh, ty + 0.38, 0.4), chto='10 сноска цены')

    # Правая карточка — что входит.
    rx = PAD + lw + 0.3
    rw = CW - lw - 0.3
    plitka(sl, rx, y, rw, hh, fill=CARD, line=LINE, radius=0.22)
    zy = blok(sl, rx + 0.5, y + 0.5, rw - 1.0, 'Что входит в подписку', UB, 18,
              font=DISP, color=WHITE, bold=True, lead=1.2)

    tx = rx + 0.5 + 0.36
    tw = rw - 1.0 - 0.36
    est = hh - (zy - y) - 0.9
    for pt, zaz in [(12, 0.15), (11.5, 0.13), (11, 0.12), (10.5, 0.11), (10, 0.1)]:
        vsego = 0.0
        for kuski, _ in PODPISKA:
            n = len(perenos(_plain(kuski), IR, pt, tw * 0.96))
            vsego += n * pt * 1.45 / 72.0 + zaz
        if vsego - zaz <= est:
            break

    py = zy + 0.44
    for kuski, novoe in PODPISKA:
        n = len(perenos(_plain(kuski), IR, pt, tw * 0.96))
        vys = n * pt * 1.45 / 72.0
        kartinka(sl, ikonka('check', '4ADE80'), rx + 0.5, py + 0.035, 0.2, 0.2)
        tf = nadpis(sl, tx, py, tw, vys + 0.08)
        abzac(tf, kuski, pt, font=BODY, color=MUTED, lead=1.45, first=True)
        if novoe:
            bx = tx + _shirina_kuskov(kuski, pt) + 0.12
            bw2, bh2 = 0.46, 0.21
            plitka(sl, bx, py + 0.04, bw2, bh2, fill=LBLUE, line=None, radius=bh2 / 2)
            tf2 = nadpis(sl, bx, py + 0.04, bw2, bh2, anchor=MSO_ANCHOR.MIDDLE)
            abzac(tf2, 'new', 8, font=BODY, color=RGBColor(0x08, 0x12, 0x2B),
                  bold=True, lead=1.0, align=PP_ALIGN.CENTER, first=True)
        py += vys + zaz

    # Сноска обязательна при любом упоминании Instagram в России.
    blok(sl, PAD, 6.5, CW,
         '* Instagram принадлежит компании Meta, признанной экстремистской '
         'организацией и запрещённой на территории Российской Федерации.',
         IR, 8.5, color=MUTED2, lead=1.3)


# ============================================================ 11. ДЛЯ КОГО

NISHI = [
    ('cup', 'HoReCa', 'Рестораны, кафе, бары и доставка'),
    ('scissors', 'Салоны красоты', 'Парикмахерские, барбершопы, ногтевой сервис'),
    ('tooth', 'Стоматология', 'Клиники и частные кабинеты'),
    ('flower', 'Цветочные салоны', 'Магазины, мастерские и доставка букетов'),
    ('bag', 'Розница и услуги', 'Локальные магазины и сервисные компании'),
    ('home', 'Товары для дома', 'Мебель, текстиль, интерьерные решения'),
    ('toy', 'Детские товары', 'Магазины и бренды детских товаров'),
    ('car', 'Авто и мотоиндустрия', 'Дилеры, автосервисы, детейлинг, шиномонтаж'),
    ('tools', 'Строительство и ремонт', 'Бригады, отделочники, застройщики'),
]


def slajd_11(prs):
    sl = novyj(prs); futer(sl, 11)
    shapka(sl, 'Для кого')
    y, zaz = 1.58, 0.22
    wh = 1.0                       # нижняя карточка «без ограничений»
    cw = (CW - zaz * 2) / 3
    ch = (6.62 - y - wh - 0.28 - 2 * 0.2) / 3
    for i, (ik, t, d) in enumerate(NISHI):
        cx = PAD + (i % 3) * (cw + zaz)
        cy = y + (i // 3) * (ch + 0.2)
        plitka(sl, cx, cy, cw, ch, fill=CARD, line=LINE, radius=0.16)
        znak(sl, cx + 0.3, cy + (ch - 0.5) / 2, 0.5, ik, '7FC4FF', pad=0.05)
        ty = blok(sl, cx + 0.94, cy + 0.28, cw - 1.24, t, UB, 13, font=DISP,
                  color=WHITE, bold=True, lead=1.2, max_strok=1, max_h=0.32)
        blok(sl, cx + 0.94, ty + 0.14, cw - 1.24, d, IR, 10, color=MUTED2,
             lead=1.35, max_h=ostatok(cy, ch, ty + 0.14, 0.24), chto='11 ниша %s' % t)

    wy = 6.62 - wh
    plitka(sl, PAD, wy, CW, wh, fill=CARD2, line=LINE2, radius=0.18)
    znak(sl, PAD + 0.42, wy + (wh - 0.52) / 2, 0.52, 'grid', '7FC4FF', pad=0.05)
    ty = blok(sl, PAD + 1.1, wy + 0.26, CW - 1.6, 'Без ограничений по отраслям',
              UB, 15, font=DISP, color=WHITE, bold=True, lead=1.2,
              max_strok=1, max_h=0.36)
    blok(sl, PAD + 1.1, ty + 0.14, CW - 1.6,
         'Списком выше мы себя не ограничиваем: модули изучают любую нишу с нуля '
         'и на этих данных строят стратегию продвижения.', IR, 11.5, color=MUTED,
         lead=1.45, max_h=ostatok(wy, wh, ty + 0.14, 0.16), chto='11 нижняя карточка')


# =============================================== 12. ПОДДЕРЖКА И ЦИФРЫ

PODDERZHKA = [
    ('pulse', 'Постоянный мониторинг',
     'Следим за трендами в SEO и GEO продвижении бизнеса.'),
    ('headset', 'Всегда на связи',
     'Московский офис ответит на вопросы и подключит к платформе.'),
    ('refresh', 'Развитие вместе с рынком',
     'Нейросети меняются, и мы обновляем подход под них.'),
]

CIFRY = [
    ('1 000', 'руководителей довольны'),
    ('1 100', 'предприятий продвинулись в GEO и SEO'),
    ('400',   'предприятий оптимизировали свои расходы'),
]


def slajd_12(prs):
    sl = novyj(prs); futer(sl, 12)
    y = shapka(sl, 'Поддержка и сопровождение') + 0.42

    chh = 1.32                     # нижний ряд с цифрами
    ih = 6.62 - y - chh - 0.62     # фотография и карточки поддержки
    iw = 6.2
    kartinka(sl, kadr(IMG + '/team.jpg', iw, ih, 'ofis.png', dark=0.12, radius=0.2),
             PAD, y, iw, ih)
    blok(sl, PAD + 0.04, y + ih + 0.12, iw, 'Офис в Москве', IR, 11,
         color=MUTED2, lead=1.2)

    px, pw = PAD + iw + 0.3, CW - iw - 0.3
    ph = (ih - 0.24) / 3
    for i, (ik, t, d) in enumerate(PODDERZHKA):
        py = y + i * (ph + 0.12)
        plitka(sl, px, py, pw, ph, fill=CARD, line=LINE, radius=0.18)
        znak(sl, px + 0.32, py + (ph - 0.52) / 2, 0.52, ik, '7FC4FF', pad=0.05)
        ty = blok(sl, px + 1.0, py + 0.26, pw - 1.36, t, UB, 13.5, font=DISP,
                  color=WHITE, bold=True, lead=1.2, max_strok=1, max_h=0.34)
        blok(sl, px + 1.0, ty + 0.12, pw - 1.36, d, IR, 11, color=MUTED2, lead=1.4,
             max_h=ostatok(py, ph, ty + 0.12, 0.22), chto='12 поддержка %s' % t)

    cy = 6.62 - chh
    zaz = 0.3
    cw = (CW - zaz * 2) / 3
    for i, (v, k) in enumerate(CIFRY):
        cx = PAD + i * (cw + zaz)
        plitka(sl, cx, cy, cw, chh, fill=CARD, line=LINE, radius=0.18)
        vy = blok(sl, cx + 0.42, cy + 0.26, cw - 0.84, v, UB, 28, font=DISP,
                  color=LBLUE, bold=True, lead=1.1, max_strok=1, max_h=0.5)
        blok(sl, cx + 0.42, vy + 0.14, cw - 0.84, k, IR, 11, color=MUTED, lead=1.35,
             max_h=ostatok(cy, chh, vy + 0.14, 0.2), chto='12 цифра %s' % v)


# ========================================================= 13. КОНТАКТЫ

def slajd_13(prs):
    sl = novyj(prs)
    kartinka(sl, kadr(IMG + '/hero-bg.jpg', W, H, 'final.png',
                      dark=0.44, left_wash=0.72), 0, 0, W, H)

    y = blok(sl, PAD, 1.55, 7.0, 'Выведите ваш бизнес в нейровыдачу уже сегодня',
             UB, 30, font=DISP, color=WHITE, bold=True, lead=1.16,
             kegli=[30, 28, 26], max_strok=3)
    y = blok(sl, PAD, y + 0.32, 6.6,
             'Оставьте заявку, наш специалист свяжется с вами в ближайшее время. '
             'Расскажем, как ваша ниша выглядит в ответах нейросетей.',
             IR, 14.5, color=MUTED, lead=1.5)

    bw, bh = 3.5, 0.72
    by = y + 0.54
    knopka = plitka(sl, PAD, by, bw, bh, fill=BLUE, line=None, radius=bh / 2)
    ssylka(knopka, ZAYAVKA)
    tf = nadpis(sl, PAD, by, bw, bh, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, 'Оставить заявку', 15, font=BODY, color=WHITE, bold=True,
          lead=1.0, align=PP_ALIGN.CENTER, first=True)
    ssylka(tf._parent, ZAYAVKA)
    tf = nadpis(sl, PAD + bw + 0.3, by, 3.2, bh, anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, 'Откроется форма\nна сайте «Промптера»', 10.5, color=MUTED2,
          lead=1.35, first=True)

    # Справа — человек, с которым клиент будет говорить.
    kx, kw = PAD + 7.6, CW - 7.6
    ky, kh = 1.42, 4.7
    plitka(sl, kx, ky, kw, kh, fill=CARD, line=LINE2, radius=0.22)
    fw = kw - 0.88
    kartinka(sl, kadr(IMG + '/director.jpg', fw, 1.7, 'direktor.png', radius=0.16),
             kx + 0.44, ky + 0.44, fw, 1.7)
    ty = blok(sl, kx + 0.44, ky + 2.32, fw, 'Руслан Демин', UB, 16, font=DISP,
              color=WHITE, bold=True, lead=1.2, max_strok=1, max_h=0.4)
    ty = blok(sl, kx + 0.44, ty + 0.1, fw, 'Управляющий партнёр, офис в Москве',
              IR, 11, color=MUTED2, lead=1.35, max_h=0.44)

    ty += 0.36
    for ik, t, url in [('phone', '+7 906 758-77-77', 'tel:+79067587777'),
                       ('mail', 'prompter.moscow@mail.ru', 'mailto:prompter.moscow@mail.ru'),
                       ('tg', '@Prompter_mos', 'https://t.me/Prompter_mos')]:
        kartinka(sl, ikonka(ik, '7FC4FF'), kx + 0.44, ty + 0.04, 0.22, 0.22)
        tf = nadpis(sl, kx + 0.78, ty, fw - 0.34, 0.3)
        abzac(tf, t, 12.5, font=BODY, color=WHITE, lead=1.2, first=True)
        ssylka(tf._parent, url)
        ty += 0.42

    kartinka(sl, ASSETS + '/logo.png', PAD, H - 0.98, 0.4, 0.4)
    tf = nadpis(sl, PAD + 0.56, H - 0.92, 6.0, 0.3)
    abzac(tf, [('Prompter ', {}), ('Moscow', {'bold': True}),
               ('     prompter-ai.moscow', {'color': MUTED2, 'font': BODY})],
          13, font=DISP, color=WHITE, lead=1.1, first=True)


# ============================================================== СБОРКА

def main():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    for i in range(1, VSEGO + 1):
        globals()['slajd_%02d' % i](prs)
    put = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'obshchaya.pptx')
    prs.save(put)
    if MALO:
        print('НЕ ВЛЕЗЛО:')
        for m in MALO:
            print('  -', m)
    else:
        print('всё влезает в свои карточки')
    print('собрано:', put)
    return put


if __name__ == '__main__':
    main()
