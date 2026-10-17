# -*- coding: utf-8 -*-
"""Пресс-кит к пресс-конференции «Эффективные инструменты привлечения клиентов».

Это не презентация доклада. Руслан Дёмин выступает не спикером, а
экспертом, на чьи слова потом ссылаются в прессе. Значит, у листа одна
задача: чтобы журналист взял цитату готовой и не переписывал её своими
словами. Отсюда правила этой сборки:

  - на каждом развороте ровно одна фраза в кавычках, крупно, — та,
    которая пойдёт в текст с подписью «Руслан Дёмин»;
  - вокруг неё — короткое пояснение на случай, если захотят развернуть;
  - никаких цен и призывов: мероприятие про тему, а не про продукт;
  - шапка с обоими знаками на каждой странице — страницы расходятся
    по редакциям поодиночке, скриншотом, и каждая должна сама
    отвечать на вопрос «кто это сказал».

Палитра и шрифты взяты у «Промптера»: тёмный лист, синий акцент.
Инструменты сборки общие с презентациями — kit.py по соседству.
"""
import os
import sys

TUT = os.path.dirname(os.path.abspath(__file__))
KOREN = os.path.abspath(os.path.join(TUT, '..', '..'))
sys.path.insert(0, os.path.join(KOREN, 'prompter-moscow', 'presentation', 'sborka'))

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from kit import (W, H, PAD, BG, CARD, CARD2, LINE, LINE2, BLUE, LBLUE, GREEN,
                 WHITE, MUTED, MUTED2, DISP, BODY, IMG, ASSETS,
                 TMP, kadr, fon, plitka, nadpis, abzac, kartinka,
                 perenos, podobrat)

UB = ('Unbounded', True)
UBS = ('Unbounded', False)
IR = ('Inter', 'r')
IM = ('Inter', 'm')
IS = ('Inter', 's')

GENII_ZNAK = os.path.join(KOREN, 'genii', 'assets', 'mark.png')
PROMPTER_ZNAK = os.path.join(KOREN, 'prompter-moscow', 'assets', 'logo.png')

VSEGO = 6

# Контакты эксперта — с его визитки, а не из презентаций для клиентов:
# в прессу идёт личная подпись, а не общий ящик отдела продаж.
EKSPERT = 'Руслан Анатольевич Дёмин'
DOLZHNOST = 'управляющий партнёр'
TELEFON = '+7 906 758-77-77'
POCHTA = 'ubeto@mail.ru'
SAJT = 'genii-ai.ru'

SOBYTIE = ('Пресс-конференция «Эффективные инструменты привлечения клиентов»'
           '   ·   20 октября 2026   ·   Москва, Кузнецкий мост, 7')

MALO = []     # всё, что не влезло в отведённое место


# ------------------------------------------------------------ основа

def novyj(prs, shapka=True):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    fon(sl)
    if shapka:
        znaki(sl)
    return sl


def znaki(sl, y=0.5):
    """Шапка: ГенИИ слева, «Промптер» справа — как на визитке.

    Знаки разного сложения: у ГенИИ квадратный, у «Промптера» выше
    своей ширины. Поэтому высоту задаём одну, а ширину считаем по
    настоящим пропорциям файла — иначе один из них поедет.
    """
    from PIL import Image

    vys = 0.5
    for put, sprava in ((GENII_ZNAK, False), (PROMPTER_ZNAK, True)):
        im = Image.open(put)
        shir = vys * im.width / im.height
        x = (W - PAD - shir) if sprava else PAD
        kartinka(sl, put, x, y, shir, vys)

    # Подписи под знаками — мелко, серым: на листе они не должны
    # спорить с цитатой, ради которой лист и существует.
    tf = nadpis(sl, PAD, y + vys + 0.08, 3.0, 0.22)
    abzac(tf, 'ГенИИ', 9.5, font=BODY, color=MUTED2, lead=1.2, first=True)
    tf = nadpis(sl, W - PAD - 3.0, y + vys + 0.08, 3.0, 0.22)
    abzac(tf, 'Промптер', 9.5, font=BODY, color=MUTED2, lead=1.2,
          align=PP_ALIGN.RIGHT, first=True)


def _plain(x):
    if isinstance(x, str):
        return x
    return ''.join(k if isinstance(k, str) else k[0] for k in x)


def blok(sl, x, y, w, text, key, size, font=BODY, color=WHITE, bold=False,
         lead=1.42, align=PP_ALIGN.LEFT, kegli=None, max_strok=None,
         max_h=None, chto=''):
    """Абзац с посчитанной высотой. Возвращает координату низа.

    Ширина строки считается по тому же файлу шрифта, которым набран
    текст, поэтому кегль не подбирается на глаз: берём самый крупный
    из тех, при которых текст заведомо влезает.
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
    s.fill.solid()
    s.fill.fore_color.rgb = cvet
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def citata(sl, y, text, max_h=1.9, w=None):
    """Фраза для прессы: крупно, в кавычках, с подписью под ней.

    Кавычки рисуем сами, а не доверяем журналисту: так он видит, что
    это готовая цитата, а не заголовок слайда, и ставит её в текст
    как есть.
    """
    w = w or (W - PAD * 2 - 0.5)
    cherta(sl, PAD, y, 0.07, max_h + 0.5, LBLUE)
    niz = blok(sl, PAD + 0.42, y, w, '«%s»' % text, UBS, 23, font=DISP,
               color=WHITE, bold=False, lead=1.3,
               kegli=[23, 21, 19.5, 18, 16.5, 15], max_h=max_h,
               chto='цитата')
    blok(sl, PAD + 0.42, niz + 0.26, w,
         [('%s, ' % EKSPERT, {'color': LBLUE, 'bold': True}),
          (DOLZHNOST, {'color': MUTED2})],
         IR, 13, font=BODY, lead=1.3)
    return niz + 0.72


def zagolovok(sl, text, y=1.55, max_strok=2):
    return blok(sl, PAD, y, W - PAD * 2 - 1.0, text, UB, 34, font=DISP,
                color=WHITE, bold=True, lead=1.16,
                kegli=[34, 31, 28, 25], max_strok=max_strok)


def nomer(sl, n):
    tf = nadpis(sl, W - PAD - 1.2, H - 0.62, 1.2, 0.3)
    abzac(tf, '%d / %d' % (n, VSEGO), 10, font=BODY, color=MUTED2,
          lead=1.2, align=PP_ALIGN.RIGHT, first=True)


# =================================================== 1. ОБЛОЖКА

def slajd_1(prs):
    sl = novyj(prs, shapka=False)
    kartinka(sl, kadr(os.path.join(IMG, 'hero-bg.jpg'), W, H, 'press-fon.png',
                      dark=0.42, left_wash=0.7), 0, 0, W, H)
    znaki(sl)

    y = blok(sl, PAD, 2.25, 10.6,
             'Полный ИИ-цикл для бизнеса: от исследования до публикации',
             UB, 40, font=DISP, color=WHITE, bold=True, lead=1.14,
             kegli=[40, 36, 32], max_strok=3)
    y = blok(sl, PAD, y + 0.46, 9.4,
             'Исследование, стратегия, генерация текстов, картинок и видео, '
             'автопубликация на 6+ площадках. Продвижение в SEO и GEO.',
             IR, 17, color=MUTED, lead=1.5)

    cherta(sl, PAD, y + 0.55, 1.5, 0.026, LBLUE)
    blok(sl, PAD, y + 0.85, 9.0,
         [('%s' % EKSPERT, {'color': WHITE, 'bold': True, 'font': DISP}),
          ('    %s' % DOLZHNOST, {'color': MUTED2})],
         IS, 16, font=BODY, lead=1.3)

    blok(sl, PAD, H - 0.75, 11.8, SOBYTIE, IR, 11.5, color=MUTED2, lead=1.4)


# =================================================== 2. КОНТЕНТ-ФАБРИКИ

# Цепочка работы с контентом. Третий элемент пары — кто этим занят
# сегодня у всех остальных: там, где стоит человек, и теряется время.
CEPOCHKA = [
    ('Исследование', 'машина'),
    ('Стратегия', 'машина'),
    ('Тексты и визуал', 'машина'),
    ('Проверка', 'человек'),
    ('Публикация', 'человек'),
    ('Анализ выдачи', 'человек'),
]


def slajd_2(prs):
    sl = novyj(prs)
    nomer(sl, 2)

    zagolovok(sl, 'Контент-фабрики есть у всех. Управляет ими всё равно человек')

    # Цепочка: шесть шагов в ряд. Там, где сегодня стоит человек,
    # карточка светлее и подписана — это и есть мысль слайда.
    n = len(CEPOCHKA)
    zazor = 0.16
    shir = (W - PAD * 2 - zazor * (n - 1)) / n
    verh, vys = 2.95, 1.35
    for i, (shag, kto) in enumerate(CEPOCHKA):
        x = PAD + i * (shir + zazor)
        chelovek = kto == 'человек'
        plitka(sl, x, verh, shir, vys,
               fill=CARD2 if chelovek else CARD,
               line=LINE2 if chelovek else LINE, radius=0.14)
        tf = nadpis(sl, x + 0.16, verh + 0.2, shir - 0.32, 0.8)
        abzac(tf, shag, 12.5, font=BODY, color=WHITE, bold=True, lead=1.25,
              first=True)
        tf = nadpis(sl, x + 0.16, verh + vys - 0.44, shir - 0.32, 0.3)
        abzac(tf, kto, 10, font=BODY,
              color=LBLUE if chelovek else MUTED2, lead=1.2, first=True)

    blok(sl, PAD, verh + vys + 0.26, W - PAD * 2,
         'Три шага справа почти везде делает человек: правит, раскладывает, '
         'проверяет, что вышло.',
         IR, 14, color=MUTED2, lead=1.45)

    citata(sl, 5.25,
           'Контент-фабрики есть у всех, это не новость. Новость в том, что '
           'управление циклом можно отдать самому ИИ: он лучше человека знает, '
           'по каким правилам его собратья отбирают контент',
           max_h=1.15)


# =================================================== 3. ВРЕМЯ

UHODIT = [
    'Согласование тем и планов',
    'Правки текстов и картинок',
    'Раскладка по шести площадкам',
]


def slajd_3(prs):
    sl = novyj(prs)
    nomer(sl, 3)

    iw = 4.6
    kartinka(sl, kadr(os.path.join(IMG, 'neurons.jpg'), iw, H - 1.7,
                      'press-nejrony.png', dark=0.2, radius=0.2),
             W - PAD - iw, 1.55, iw, H - 1.7 - 0.55)

    tw = W - iw - PAD * 2 - 0.7
    blok(sl, PAD, 1.6, tw, 'Дороже денег — время собственника',
         UB, 31, font=DISP, color=WHITE, bold=True, lead=1.16,
         kegli=[31, 28, 25], max_strok=2)

    y = 3.3
    for punkt in UHODIT:
        cherta(sl, PAD, y + 0.14, 0.22, 0.022, LBLUE)
        y = blok(sl, PAD + 0.42, y, tw - 0.42, punkt, IR, 14.5,
                 color=MUTED, lead=1.4) + 0.3

    citata(sl, 5.35,
           'Предприниматель тратит на соцсети не деньги, а своё время — самый '
           'дорогой ресурс в компании. Цикл забирает рутину, человеку остаётся '
           'решение и смысл',
           max_h=1.1, w=tw + 0.3)


# =================================================== 4. ДЕНЬГИ

PUTI = [
    ('Диджитал-агентство',
     'Счёт каждый месяц, правки через менеджера',
     False),
    ('Своими силами',
     'Токены, зарубежные аккаунты, оплата из-за рубежа, блокировки',
     False),
    ('Готовый сервис',
     'Фиксированная плата, те же площадки, сравнимый эффект',
     True),
]


def slajd_4(prs):
    sl = novyj(prs)
    nomer(sl, 4)

    zagolovok(sl, 'Без агентства, токенов и борьбы с блокировками')

    n = len(PUTI)
    zazor = 0.3
    shir = (W - PAD * 2 - zazor * (n - 1)) / n
    verh, vys = 2.9, 1.95
    for i, (imya, opisanie, svoj) in enumerate(PUTI):
        x = PAD + i * (shir + zazor)
        plitka(sl, x, verh, shir, vys,
               fill=CARD2 if svoj else CARD,
               line=GREEN if svoj else LINE, radius=0.16,
               lw=1.6 if svoj else 1.0)
        tf = nadpis(sl, x + 0.26, verh + 0.26, shir - 0.52, 0.5)
        abzac(tf, imya, 15, font=DISP, color=GREEN if svoj else WHITE,
              bold=True, lead=1.2, first=True)
        blok(sl, x + 0.26, verh + 0.86, shir - 0.52, opisanie, IR, 12.5,
             color=MUTED if svoj else MUTED2, lead=1.45,
             max_h=vys - 1.0, chto='путь %s' % imya)

    blok(sl, PAD, verh + vys + 0.3, W - PAD * 2,
         [('Разница — от 70–80 тысяч рублей в месяц. ', {'color': GREEN, 'bold': True}),
          ('Столько стоят те же роли своими силами.', {'color': MUTED2})],
         IR, 13.5, font=BODY, lead=1.45)

    citata(sl, 5.6,
           'Чтобы работать с нейросетями самому, нужно покупать токены, держать '
           'зарубежные аккаунты и воевать с блокировками. Готовый сервис '
           'снимает это целиком',
           max_h=1.05)


# =================================================== 5. НЕЙРОВЫДАЧА

SRAVNENIE = [
    ('Поиск', 'Десять ссылок. Выбирает человек', 'позицию в списке'),
    ('Нейроответ', 'Два-три названия. Выбор уже сделан', 'упоминание в ответе'),
]


def slajd_5(prs):
    sl = novyj(prs)
    nomer(sl, 5)

    zagolovok(sl, 'Клиент спрашивает нейросеть, а не поисковик')

    n = len(SRAVNENIE)
    zazor = 0.4
    shir = (W - PAD * 2 - 2.9 - zazor * n) / n
    verh, vys = 2.9, 2.05
    for i, (imya, opisanie, chto) in enumerate(SRAVNENIE):
        x = PAD + i * (shir + zazor)
        novoe = i == 1
        plitka(sl, x, verh, shir, vys,
               fill=CARD2 if novoe else CARD,
               line=LBLUE if novoe else LINE, radius=0.16,
               lw=1.6 if novoe else 1.0)
        tf = nadpis(sl, x + 0.3, verh + 0.26, shir - 0.6, 0.5)
        abzac(tf, imya, 17, font=DISP, color=LBLUE if novoe else WHITE,
              bold=True, lead=1.2, first=True)
        blok(sl, x + 0.3, verh + 0.88, shir - 0.6, opisanie, IR, 13.5,
             color=MUTED if novoe else MUTED2, lead=1.45,
             max_h=0.7, chto='путь %s' % imya)
        blok(sl, x + 0.3, verh + vys - 0.52, shir - 0.6,
             [('Борьба за ', {'color': MUTED2}),
              (chto, {'color': WHITE, 'bold': True})],
             IR, 12, font=BODY, lead=1.35)

    # Срок — отдельной карточкой справа. Это главное, что эксперт
    # говорит про GEO: не «кнопка», а работа на несколько месяцев.
    # Честный срок в прессе цитируют охотнее обещаний.
    x = PAD + (shir + zazor) * n
    plitka(sl, x, verh, W - PAD - x, vys, fill=CARD, line=LINE2, radius=0.16)
    tf = nadpis(sl, x + 0.3, verh + 0.3, W - PAD - x - 0.6, 0.8)
    abzac(tf, '3–6', 40, font=DISP, color=GREEN, bold=True, lead=1.0,
          first=True)
    blok(sl, x + 0.3, verh + 1.0, W - PAD - x - 0.6,
         'месяцев занимает выход в нейровыдачу', IR, 12.5, color=MUTED,
         lead=1.4, max_h=0.6, chto='срок GEO')

    cherta(sl, PAD, 5.14, 0.22, 0.022, GREEN)
    blok(sl, PAD + 0.42, 5.0, W - PAD * 2 - 0.42,
         [('Маркировать фото и видео как созданные ИИ закон сегодня не требует. ',
           {'color': MUTED, 'bold': True}),
          ('Этим грех не пользоваться.', {'color': MUTED2})],
         IR, 12.5, font=BODY, lead=1.4)

    citata(sl, 5.62,
           'Попасть в нейроответ можно целенаправленно, но это не кнопка: '
           'от трёх до шести месяцев работы. Зато эту работу машина делает '
           'лучше человека — и без агентского счёта каждый месяц',
           max_h=1.0)


# =================================================== 6. СПРАВКА И КОНТАКТЫ

def qr(adres, imya):
    import qrcode
    im = qrcode.make('https://%s' % adres, border=1, box_size=10)
    put = os.path.join(TMP, imya)
    im.convert('RGB').save(put)
    return put


def slajd_6(prs):
    sl = novyj(prs)
    nomer(sl, 6)

    blok(sl, PAD, 1.6, 8.6, 'Справка и контакты', UB, 30, font=DISP,
         color=WHITE, bold=True, lead=1.16)

    # Справка — то, что редакции ставят в конце статьи. Поэтому она
    # написана целыми предложениями: журналист копирует её как есть.
    y = 2.7
    for imya, text in (
        ('Промптер',
         'Российский сервис автоматизации SMM: исследование ниши, стратегия, '
         'генерация текстов, изображений и видео, публикация на 6+ площадках.'),
        ('ГенИИ',
         'Официальный партнёр «Промптера» по Москве и области. Продвижение '
         'компаний в ответах нейросетей — SEO и GEO.'),
    ):
        plitka(sl, PAD, y, 7.3, 1.35, fill=CARD, line=LINE, radius=0.16)
        tf = nadpis(sl, PAD + 0.28, y + 0.22, 6.7, 0.36)
        abzac(tf, imya, 14.5, font=DISP, color=LBLUE, bold=True, lead=1.2,
              first=True)
        blok(sl, PAD + 0.28, y + 0.68, 6.74, text, IR, 12, color=MUTED,
             lead=1.4, max_h=0.56, chto='справка %s' % imya)
        y += 1.6

    # Контакты эксперта — справа, отдельной карточкой с кодом: её
    # фотографируют с экрана, а не переписывают.
    x = PAD + 7.8
    shir = W - PAD - x
    plitka(sl, x, 2.7, shir, 2.95, fill=CARD2, line=LINE2, radius=0.16)
    blok(sl, x + 0.3, 2.95, shir - 0.6, EKSPERT, UBS, 16, font=DISP,
         color=WHITE, bold=True, lead=1.22, kegli=[16, 14.5, 13],
         max_strok=2)
    blok(sl, x + 0.3, 3.62, shir - 0.6, DOLZHNOST, IR, 12, color=MUTED2,
         lead=1.3)

    kod = qr(SAJT, 'press-qr.png')
    kartinka(sl, kod, x + 0.3, 4.1, 1.25, 1.25)
    blok(sl, x + 1.75, 4.18, shir - 2.05,
         [(TELEFON + '\n', {'color': WHITE, 'bold': True}),
          (POCHTA + '\n', {'color': MUTED}),
          (SAJT, {'color': LBLUE, 'bold': True})],
         IS, 13, font=BODY, lead=1.55)

    blok(sl, PAD, H - 1.0, 11.8, SOBYTIE, IR, 11.5, color=MUTED2, lead=1.4)


# =================================================== сборка

def proverit_znaki(prs):
    """Все ли знаки есть в файлах шрифтов.

    Кавычки-ёлочки, тире и неразрывные пробелы в предпросмотре
    рисуются подставным шрифтом и выглядят прилично, а у получателя
    выходят квадратиками. Поэтому проверяем по самим файлам.
    """
    import glob
    from fontTools.ttLib import TTFont
    from kit import SHRIFTY

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


def main(fajl='press-kit.pptx'):
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

    put = os.path.join(TUT, fajl)
    prs.save(put)
    if MALO:
        print('НЕ ВЛЕЗЛО:')
        for m in MALO:
            print('  -', m)
    else:
        print('всё влезает в отведённое место')
    print('собрано:', put, '| страниц:', VSEGO)
    return put


if __name__ == '__main__':
    main()
