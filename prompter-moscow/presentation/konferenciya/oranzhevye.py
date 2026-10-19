# -*- coding: utf-8 -*-
"""Пять листов пресс-кита в оформлении презентации «Промптер SMM 2026».

Те же пять мыслей, что были в синем пресс-ките, но перекрашенные под
оранжевую презентацию: тёмный фон с тёплыми частицами, тонкая
оранжевая рамка во весь лист, карточки с оранжевым контуром. Знаки
обеих компаний стоят по бокам шапки на каждом листе — ГенИИ слева,
«Промптер» справа.

Вставлять так же, как и остальные: выделить листы в панели слева,
скопировать, вставить с «Сохранить исходное форматирование».
"""
import os
import sys

TUT = os.path.dirname(os.path.abspath(__file__))
KOREN = os.path.abspath(os.path.join(TUT, '..', '..', '..'))
KARTINKI = os.path.join(KOREN, 'pressa', 'img')
sys.path.insert(0, os.path.join(os.path.dirname(TUT), 'sborka'))

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from ikonki import ikonka
from kit import (W, H, PAD, DISP, BODY, IMG, ASSETS, TMP,
                 kadr, plitka, nadpis, abzac, kartinka, perenos, podobrat)
from pptx.dml.color import RGBColor

# Палитра оранжевой презентации. Синюю отсюда убрали целиком: один
# холодный акцент на тёплом листе читается как чужая вставка.
BG = RGBColor(0x0A, 0x09, 0x0B)
CARD = RGBColor(0x16, 0x0E, 0x0A)
CARD2 = RGBColor(0x20, 0x14, 0x0D)
LINE = RGBColor(0x4A, 0x2A, 0x16)
LINE2 = RGBColor(0x7A, 0x3F, 0x1C)
BLUE = RGBColor(0xE8, 0x61, 0x1A)
LBLUE = RGBColor(0xFF, 0x8A, 0x3D)      # оранжевый вместо светло-синего
GREEN = RGBColor(0x4A, 0xDE, 0x80)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0xDE, 0xD6, 0xCF)
MUTED2 = RGBColor(0xA2, 0x97, 0x8E)
ORANZH = BLUE

UB = ('Unbounded', True)
UBS = ('Unbounded', False)
IR = ('Inter', 'r')
IM = ('Inter', 'm')
IS = ('Inter', 's')

GENII_ZNAK = os.path.join(KOREN, 'genii', 'assets', 'mark.png')
PROMPTER_ZNAK = os.path.join(KOREN, 'prompter-moscow', 'assets', 'logo.png')

VSEGO = 8

# Контакты эксперта — с его визитки, а не из презентаций для клиентов:
# в прессу идёт личная подпись, а не общий ящик отдела продаж.
EKSPERT = 'Руслан Анатольевич Дёмин'
DOLZHNOST = 'управляющий партнёр'
TELEFON = '+7 906 758-77-77'
POCHTA = 'prompter.moscow@mail.ru'
SAJT = 'prompter-ai.moscow'      # на него ведёт QR
SAJT_2 = 'genii-ai.ru'
AKKAUNT = '@geniimoscow'

SOBYTIE = ('Пресс-конференция «Эффективные инструменты привлечения клиентов»'
           '   ·   20 октября 2026   ·   Москва, Кузнецкий мост, 7')

MALO = []     # всё, что не влезло в отведённое место


# ------------------------------------------------------------ основа

STRANICA = 0


FON = os.path.join(TUT, 'fon.jpg')


def fon(sl):
    """Фон презентации: частицы плюс тонкая оранжевая рамка."""
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Pt as _Pt
    kartinka(sl, FON, 0, 0, W, H)
    ramka = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.1), Inches(0.1),
                                Inches(W - 0.2), Inches(H - 0.2))
    ramka.fill.background()
    ramka.line.color.rgb = ORANZH
    ramka.line.width = _Pt(1.25)
    ramka.shadow.inherit = False
    return ramka


def novyj(prs, shapka=True):
    global STRANICA
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    fon(sl)
    if shapka:
        znaki(sl)
    STRANICA += 1
    if VSEGO:
        nomer(sl, STRANICA)
    return sl


def znaki(sl, y=0.5, podlozhka=False):
    """Шапка: ГенИИ слева, «Промптер» справа — как на визитке.

    Знаки разного сложения: у ГенИИ квадратный, у «Промптера» —
    вытянутый в строку. Поэтому высоту задаём одну, а ширину
    считаем по настоящим пропорциям файла — иначе один из них
    поедет.

    Подпись ставится только под знаком-символом. Если в файле
    логотип с названием — а в самой презентации знак «Промптера»
    именно такой, — слово под ним повторяет то, что уже написано.
    """
    from PIL import Image

    for put_, imya, sprava in ((GENII_ZNAK, u'ГенИИ', False),
                               (PROMPTER_ZNAK, u'Промптер', True)):
        im = Image.open(put_)
        nadpisnoj = im.width > im.height * 2
        vys = 0.44 if nadpisnoj else 0.6
        shir = vys * im.width / im.height
        x = (W - PAD - shir) if sprava else PAD
        sy = y + (0.08 if nadpisnoj else 0)
        if sprava and podlozhka:
            # На обложке знак приходится на светлый кадр и теряется.
            # Тёмная подложка возвращает ему контраст, не закрывая лицо.
            plitka(sl, x - 0.3, y - 0.26, shir + 0.6, vys + 0.94,
                   fill=BG, line=None, radius=0.14)
        kartinka(sl, put_, x, sy, shir, vys)
        if nadpisnoj:
            continue
        # Подпись под знаком — мелко, серым: на листе она не должна
        # спорить с цитатой, ради которой лист и существует.
        tf = nadpis(sl, (W - PAD - 3.0) if sprava else PAD, y + vys + 0.08,
                    3.0, 0.22)
        abzac(tf, imya, 9.5, font=BODY, color=MUTED2, lead=1.2,
              align=PP_ALIGN.RIGHT if sprava else PP_ALIGN.LEFT, first=True)


def _plain(x):
    if isinstance(x, str):
        return x
    return ''.join(k if isinstance(k, str) else k[0] for k in x)


# Межстрочный шаг PowerPoint считает не от кегля, а от высоты строки
# самого шрифта: при межстрочном 1,26 строки расходятся на
# 1,26 × 1,15 em. Без этой поправки блок считался ниже, чем выходил
# на листе: подпись эксперта садилась на последнюю строку цитаты,
# а оранжевая черта слева обрывалась на третьей из четырёх.
SHAG = 1.15


def blok(sl, x, y, w, text, key, size, font=BODY, color=WHITE, bold=False,
         lead=1.42, align=PP_ALIGN.LEFT, kegli=None, max_strok=None,
         max_h=None, chto=''):
    """Абзац с посчитанной высотой. Возвращает координату низа.

    Ширина строки считается по тому же файлу шрифта, которым набран
    текст, поэтому кегль не подбирается на глаз: берём самый крупный
    из тех, при которых текст заведомо влезает.
    """
    plain = _plain(text)
    shag = lead * SHAG
    if kegli is None and max_h is not None:
        kegli = [round(size * k, 1) for k in (1, .96, .92, .88, .84, .8, .76, .72)]
    if kegli:
        size, lines = podobrat(plain, key, kegli, w, max_h if max_h else 99,
                               shag, max_strok)
    else:
        lines = perenos(plain, key, size, w * 0.96)
    h = len(lines) * size * shag / 72.0
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


def citata(sl, y, text, max_h=2.9, w=None, kegl=30):
    """Фраза для прессы во весь лист.

    Главное решение всей сборки: цитата — это и есть страница, а не
    подпись под схемой. Первый вариант был свёрстан как отчёт —
    плитки, списки, текст в двенадцать пунктов, — и читался как
    доклад. Журналисту нужно обратное: одна мысль, набранная так
    крупно, что её видно с последнего ряда и не надо вчитываться.
    """
    w = w or (W - PAD * 2 - 0.6)
    niz = blok(sl, PAD + 0.5, y, w, '«%s»' % text, UBS, kegl, font=DISP,
               color=WHITE, bold=False, lead=1.26,
               kegli=[kegl, kegl - 2, kegl - 4, kegl - 6, kegl - 8,
                      kegl - 10, kegl - 12],
               max_h=max_h, chto='цитата')
    cherta(sl, PAD, y + 0.08, 0.09, max(0.5, niz - y - 0.04), LBLUE)
    blok(sl, PAD + 0.5, niz + 0.4, w,
         [('%s, ' % EKSPERT, {'color': LBLUE, 'bold': True}),
          (DOLZHNOST, {'color': MUTED2})],
         IR, 15, font=BODY, lead=1.3)
    return niz + 0.9


def ryad(sl, y, slova, kegl=18, cvet=WHITE, razdelitel='·'):
    """Короткие слова в строку через точку — вместо ряда карточек.

    Карточки с рамками и были той самой «отчётностью»: шесть коробок
    в ряд читаются как таблица. Те же шесть слов, набранные строкой,
    занимают вдвое меньше места и вдвое крупнее.
    """
    text = (' %s ' % razdelitel).join(slova)
    return blok(sl, PAD, y, W - PAD * 2, text, IM, kegl, font=BODY,
                color=cvet, lead=1.35, kegli=[kegl, kegl - 1.5, kegl - 3],
                max_strok=2, max_h=1.0, chto='ряд слов')


def chislo(sl, x, y, w, bolshoe, podpis, cvet=GREEN, kegl=92):
    """Огромное число и подпись под ним."""
    niz = blok(sl, x, y, w, bolshoe, UB, kegl, font=DISP, color=cvet,
               bold=True, lead=1.02,
               kegli=[kegl, kegl - 8, kegl - 16, kegl - 24, kegl - 32,
                      kegl - 40],
               max_strok=1)
    return blok(sl, x, niz + 0.14, w, podpis, IR, 16, color=MUTED,
                lead=1.35, max_h=0.95, chto='подпись к числу')


def zagolovok(sl, text, y=1.6, max_strok=2, kegl=40):
    return blok(sl, PAD, y, W - PAD * 2 - 0.4, text, UB, kegl, font=DISP,
                color=WHITE, bold=True, lead=1.14,
                kegli=[kegl, kegl - 3, kegl - 6, kegl - 9, kegl - 12],
                max_strok=max_strok)


def nomer(sl, n):
    tf = nadpis(sl, W - PAD - 1.2, H - 0.62, 1.2, 0.3)
    abzac(tf, '%d / %d' % (n, VSEGO), 10, font=BODY, color=MUTED2,
          lead=1.2, align=PP_ALIGN.RIGHT, first=True)


# =================================================== 1. ОБЛОЖКА

def slajd_1(prs):
    sl = novyj(prs, shapka=False)

    # Человек и светящиеся панели — с фирменного баннера «Промптера».
    # Пустая обложка с одним заголовком выглядела холодно: у компании
    # уже есть свой кадр, и на пресс-конференции узнают именно его.
    iw = 5.3
    kartinka(sl, kadr(os.path.join(KARTINKI, 'muzhik.jpg'), iw, H,
                      'press-muzhik.png', dark=0.12), W - iw, 0, iw, H)
    # Растушёвка слева направо, чтобы кадр не обрывался по линейке.
    kartinka(sl, kadr(os.path.join(IMG, 'hero-bg.jpg'), W - iw + 0.9, H,
                      'press-fon.png', dark=0.62, left_wash=0.5),
             0, 0, W - iw + 0.9, H)
    znaki(sl, podlozhka=True)

    # Слоган — дословно с баннера. Это то, с чего просили начинать.
    y = blok(sl, PAD, 2.0, W - iw - PAD + 0.1,
             'ИНТЕЛЛЕКТУАЛЬНЫЙ СЕРВИС\n'
             'ДЛЯ АВТОМАТИЗАЦИИ SMM\n'
             'И УСИЛЕНИЯ ЦИФРОВОГО\n'
             'ПРИСУТСТВИЯ КОМПАНИЙ\n'
             'В ИНТЕРНЕТЕ',
             UB, 27, font=DISP, color=WHITE, bold=True, lead=1.26,
             kegli=[27, 25, 23, 21], max_strok=5)

    cherta(sl, PAD, y + 0.52, 2.0, 0.035, LBLUE)
    y = blok(sl, PAD, y + 0.85, W - iw - PAD, EKSPERT,
             IS, 16, font=BODY, color=WHITE, bold=True, lead=1.35)
    blok(sl, PAD, y + 0.06, W - iw - PAD, DOLZHNOST,
         IR, 14, font=BODY, color=MUTED2, lead=1.35)

    # Строку события держим в левой, тёмной половине: на светлом
    # кадре справа она читалась бы по складам.
    blok(sl, PAD, H - 1.05, W - iw - PAD + 0.2,
         'Пресс-конференция «Эффективные инструменты привлечения клиентов»\n'
         '20 октября 2026 · Москва, Кузнецкий мост, 7',
         IR, 11, color=MUTED2, lead=1.45)


# =================================================== 2. ВОЗМОЖНОСТИ

AGENTY = [
    ('target', 'AI-маркетолог', 'Ниша, конкуренты, запросы'),
    ('pencil', 'AI-копирайтер', 'Тексты в стиле бренда'),
    ('palette', 'AI-дизайнер', 'Визуал под площадки'),
    ('video', 'AI-сценарист\nи оператор', 'Сценарий и готовый ролик'),
    ('send', 'AI СММ-менеджер', 'Проверка и публикация'),
]

PLOSHCHADKI = 'Telegram · VK · Дзен · Одноклассники · Max · Instagram*'

SVERH = 'Цифровой двойник · Видео по сценарию · Сайт под заявки · Брендбук и мерч'


def znachok(sl, x, y, d, imya):
    """Значок сайта в круглой подложке — как в карточках агентов."""
    plitka(sl, x, y, d, d, fill=CARD2, line=None, radius=d / 2)
    pole = d * 0.27
    kartinka(sl, ikonka(imya, '7FC4FF'), x + pole, y + pole,
             d - pole * 2, d - pole * 2)


def slajd_2(prs):
    sl = novyj(prs)

    zagolovok(sl, 'Пять ИИ-агентов вместо агентства', kegl=40, max_strok=1)

    # Карточки те же, что на сайте и в общей презентации: синяя
    # заливка, тонкая рамка, значок в круге. Первый вариант был набран
    # строками без карточек — на телефоне он читался как мелкий
    # список, и фирменного в нём не осталось ничего.
    n = len(AGENTY)
    zazor = 0.22
    shir = (W - PAD * 2 - zazor * (n - 1)) / n
    verh, vys = 2.7, 2.85
    for i, (znak, imya, chto) in enumerate(AGENTY):
        x = PAD + i * (shir + zazor)
        plitka(sl, x, verh, shir, vys, fill=CARD, line=LINE, radius=0.18)
        znachok(sl, x + 0.26, verh + 0.26, 0.82, znak)
        blok(sl, x + 0.26, verh + 1.24, shir - 0.52, imya, UBS, 16,
             font=DISP, color=WHITE, bold=True, lead=1.22,
             max_strok=2, kegli=[16, 15, 14, 13])
        blok(sl, x + 0.26, verh + 1.98, shir - 0.52, chto, IR, 13.5,
             color=MUTED, lead=1.4, max_strok=3,
             kegli=[13.5, 12.5, 11.5], max_h=vys - 2.15,
             chto='описание агента %s' % imya)

    niz = verh + vys + 0.3
    ny = blok(sl, PAD, niz, W - PAD * 2,
              [('Автопубликация: ', {'color': WHITE, 'bold': True}),
               (PLOSHCHADKI, {'color': MUTED})],
              IM, 17, font=BODY, lead=1.4, max_strok=1,
              kegli=[17, 16, 15, 14])
    ny = blok(sl, PAD, ny + 0.22, W - PAD * 2,
              [('Сверх цикла: ', {'color': WHITE, 'bold': True}),
               (SVERH, {'color': MUTED2})],
              IM, 16, font=BODY, lead=1.4, max_strok=1,
              kegli=[16, 15, 14, 13])

    # Сноска обязательная: без неё название соцсети на экране —
    # нарушение, и на таком мероприятии это заметят первыми.
    blok(sl, PAD, ny + 0.24, W - PAD * 2,
         '* Instagram принадлежит компании Meta, признанной экстремистской '
         'организацией и запрещённой на территории Российской Федерации.',
         IR, 9.5, color=MUTED2, lead=1.35, max_strok=1,
         kegli=[9.5, 9, 8.5])


# =================================================== 3. КОНТЕНТ-ФАБРИКИ

def slajd_3(prs):
    sl = novyj(prs)

    citata(sl, 1.75,
           'Контент-фабрики есть у всех, это не новость. Новость в том, что '
           'управление циклом можно отдать самому ИИ: он знает правила своих '
           'собратьев лучше человека',
           max_h=2.75, kegl=34)

    # Внизу — та же цепочка, но строкой, а не шестью коробками.
    cherta(sl, PAD, H - 1.85, W - PAD * 2, 0.012, LINE2)
    blok(sl, PAD, H - 1.58, W - PAD * 2,
         [('Исследование · Стратегия · Генерация', {'color': MUTED2}),
          ('      Проверка · Публикация · Анализ', {'color': WHITE, 'bold': True})],
         IM, 18, font=BODY, lead=1.35)
    blok(sl, PAD, H - 1.0, W - PAD * 2,
         'Светлым — то, что почти везде до сих пор делает человек',
         IR, 14, color=MUTED2, lead=1.35)



# =================================================== 4. ВРЕМЯ

def slajd_4(prs):
    sl = novyj(prs)

    # Фото нейронов с синего пресс-кита сюда не переехало: холодный
    # кадр на тёплом листе читается как чужая вставка, да ещё и
    # перекрывал оранжевую рамку справа. Цитата забирает весь лист.
    citata(sl, 2.1,
           'Предприниматель тратит на соцсети не деньги, а своё время — '
           'самый дорогой ресурс в компании',
           max_h=2.6, kegl=36)

    cherta(sl, PAD, H - 1.6, W - PAD * 2, 0.012, LINE2)
    blok(sl, PAD, H - 1.34, W - PAD * 2,
         'Согласование тем · Правки текстов · Раскладка по площадкам',
         IM, 17, color=MUTED2, lead=1.35, kegli=[17, 16, 15],
         max_strok=1)


# =================================================== 5. ДЕНЬГИ

def slajd_5(prs):
    sl = novyj(prs)

    chislo(sl, PAD, 1.6, W - PAD * 2, '120–150 000 ₽',
           'в месяц — столько стоит digital-агентство', kegl=78)

    citata(sl, 4.15,
           'Чтобы работать с нейросетями самому, нужно покупать токены, '
           'держать зарубежные аккаунты и воевать с блокировками. Готовый '
           'сервис снимает это целиком',
           max_h=2.2, kegl=30)


# =================================================== 6. НЕЙРОВЫДАЧА

def slajd_6(prs):
    sl = novyj(prs)

    chislo(sl, PAD, 1.6, 5.4, '3–6',
           'месяцев занимает выход в нейровыдачу')

    # Про маркировку — справа от числа, мелко: это замечание вскользь.
    x = PAD + 6.1
    cherta(sl, x, 1.75, 0.05, 1.5, GREEN)
    blok(sl, x + 0.35, 1.7, W - PAD - x - 0.35,
         [('Маркировать фото и видео как созданные ИИ закон сегодня '
           'не требует. ', {'color': MUTED, 'bold': True}),
          ('Этим грех не пользоваться.', {'color': MUTED2})],
         IR, 15, font=BODY, lead=1.45, max_h=1.5, chto='маркировка')

    citata(sl, 4.25,
           'Клиент больше не листает десять ссылок — он спрашивает нейросеть '
           'и получает два-три названия. Попасть в этот ответ можно '
           'целенаправленно',
           max_h=2.0, kegl=30)


# =================================================== 7. КЕЙСЫ

# Кейсы из презентации «Промптера» за 2026 год. Берём из каждого две
# цифры — заявки и клиентов: охваты и подписчики на пресс-конференции
# звучат как реклама, а заявки и клиенты это результат, про который
# спрашивают. Подписи к числам у кейсов разные намеренно: у магазина
# на маркетплейсах это клики и оформления, и подменять их общим
# словом «заявки» значило бы приукрасить.
KEJSY = [
    ('55 РозДари', 'доставка цветов · Нижний Новгород', '6 месяцев',
     ('745', 'заявок'), ('317', 'клиентов')),
    ('Сахара.Нет', 'ПП-конфеты без сахара', '3,5 месяца',
     ('376', 'кликов на WB и Ozon'), ('226', 'оформлений')),
    ('Эмиграционно-визовый центр', 'Калининград', '3 месяца',
     ('149', 'заявок'), ('46', 'клиентов')),
    ('МЁД', 'кафе-караоке · Домодедово', '5 месяцев',
     ('181', 'заявка'), ('109', 'клиентов')),
]


def razryady(n):
    """Тысячи через пробел: «1451» глаз читает как опечатку."""
    return '{:,}'.format(n).replace(',', '\u00a0')


def sklonenie(n, formy):
    """«1 451 обращение», а не «обращений».

    Число в тексте склоняет за собой слово, и на листе для прессы это
    замечают: журналист переписывает фразу целиком, вместе с ошибкой.
    """
    ost100, ost10 = n % 100, n % 10
    if 11 <= ost100 <= 14:
        return formy[2]
    if ost10 == 1:
        return formy[0]
    if 2 <= ost10 <= 4:
        return formy[1]
    return formy[2]


def slajd_7(prs):
    sl = novyj(prs)
    zagolovok(sl, 'Кейсы 2026', kegl=38, max_strok=1)

    n = len(KEJSY)
    zazor = 0.45
    shir = (W - PAD * 2 - zazor * (n - 1)) / n
    verh = 2.75
    for i, (imya, nisha, srok, pervoe, vtoroe) in enumerate(KEJSY):
        x = PAD + i * (shir + zazor)
        cherta(sl, x, verh, shir * 0.42, 0.03, LBLUE)
        y = blok(sl, x, verh + 0.26, shir, imya, UBS, 18, font=DISP,
                 color=WHITE, bold=True, lead=1.2, max_strok=2,
                 kegli=[18, 16.5, 15, 14])
        y = blok(sl, x, y + 0.12, shir, nisha, IR, 12.5, color=MUTED2,
                 lead=1.35, max_strok=2, kegli=[12.5, 11.5, 10.5])

        blok(sl, x, verh + 1.52, shir, srok, IR, 12, color=LBLUE,
             lead=1.3, max_strok=1)

        y = verh + 1.82
        for chislo_, podpis in (pervoe, vtoroe):
            y = blok(sl, x, y + 0.2, shir, chislo_, UB, 36, font=DISP,
                     color=GREEN, bold=True, lead=1.05, max_strok=1,
                     kegli=[36, 32, 29])
            y = blok(sl, x, y + 0.04, shir, podpis, IR, 12,
                     color=MUTED, lead=1.3, max_strok=2,
                     kegli=[12, 11, 10])

    # Итог — то, что журналист вынесет в текст одной строкой.
    vsego_z = sum(int(k[3][0]) for k in KEJSY)
    vsego_k = sum(int(k[4][0]) for k in KEJSY)
    cherta(sl, PAD, H - 0.82, W - PAD * 2, 0.012, LINE2)
    blok(sl, PAD, H - 0.6, W - PAD * 2,
         [('%d %s за 2026 год: '
           % (len(KEJSY),
              sklonenie(len(KEJSY), ('проект', 'проекта', 'проектов'))),
           {'color': MUTED2}),
          ('%s %s и %s %s'
           % (razryady(vsego_z),
              sklonenie(vsego_z, ('обращение', 'обращения', 'обращений')),
              razryady(vsego_k),
              sklonenie(vsego_k, ('клиент', 'клиента', 'клиентов'))),
           {'color': WHITE, 'bold': True})],
         IM, 15, font=BODY, lead=1.35, max_strok=1, kegli=[15, 14, 13])


# =================================================== 8. КОНТАКТЫ

def qr(adres, imya):
    import qrcode
    im = qrcode.make('https://%s' % adres, border=1, box_size=10)
    put = os.path.join(TMP, imya)
    im.convert('RGB').save(put)
    return put


def slajd_8(prs):
    sl = novyj(prs)

    # Последний лист повторяет оборот визитки: тот же текст, тот же
    # код. Человек уносит с собой карточку и лист, и если они говорят
    # разными словами, запоминается ни то ни другое.
    qr_shir = 2.3
    qx = W - PAD - qr_shir
    kod = qr(SAJT, 'press-qr.png')
    kartinka(sl, kod, qx, 1.75, qr_shir, qr_shir)
    y = blok(sl, qx - 0.6, 1.75 + qr_shir + 0.22, qr_shir + 0.6, SAJT,
             IS, 17, font=BODY, color=WHITE, bold=True, lead=1.3,
             align=PP_ALIGN.CENTER, max_strok=1, kegli=[17, 16, 15])
    blok(sl, qx - 0.6, y + 0.08, qr_shir + 0.6, 'SEO и GEO', IR, 14,
         color=LBLUE, lead=1.3, align=PP_ALIGN.CENTER, max_strok=1)

    tw = qx - PAD - 0.8
    y = blok(sl, PAD, 1.7, tw, 'Полный AI цикл', UB, 46, font=DISP,
             color=WHITE, bold=True, lead=1.12,
             kegli=[46, 42, 38], max_strok=1)
    y = blok(sl, PAD, y + 0.42, tw,
             'Исследование, генерация контента, автоматическая публикация '
             'на площадках, аналитика нейровыдачи.',
             IR, 18, color=MUTED, lead=1.5, kegli=[18, 17, 16], max_strok=3)
    blok(sl, PAD, y + 0.3, tw,
         'Интеллектуальный сервис для автоматизации SMM и усиления '
         'цифрового присутствия компании в интернете.',
         IR, 18, color=MUTED, lead=1.5, kegli=[18, 17, 16], max_strok=3)

    cherta(sl, PAD, H - 1.75, W - PAD * 2, 0.012, LINE2)
    y = blok(sl, PAD, H - 1.5, W - PAD * 2,
             '%s     %s     %s' % (TELEFON, AKKAUNT, POCHTA),
             IS, 19, font=BODY, color=WHITE, bold=True, lead=1.35,
             max_strok=1, kegli=[19, 18, 17, 16])
    blok(sl, PAD, y + 0.18, W - PAD * 2,
         [('%s, %s' % (EKSPERT, DOLZHNOST), {'color': MUTED2}),
          ('     ГенИИ — официальный партнёр «Промптера» по Москве и области',
           {'color': MUTED2})],
         IR, 12.5, font=BODY, lead=1.4, max_strok=1,
         kegli=[12.5, 11.5, 10.5])


# ====================================== 9. ТЕМЫ ДЛЯ КОНФЕРЕНЦИИ

# Три направления, которые эксперт заявил организатору. Порядок и
# слова — его, менять их по своему вкусу нельзя: по этим формулировкам
# его и анонсируют.
TEMY = [
    (u'ТЕМА 1', u'Время',
     u'Контент-фабрики есть у всех, но процессом управляет '
     u'человек. Управление циклом можно отдать самому ИИ', None),
    (u'ТЕМА 2', u'Деньги',
     u'Не платить агентству, не покупать токены, не воевать '
     u'с блокировками аккаунтов', u'от 120–150 000 ₽ в месяц'),
    (u'ТЕМА 3', u'Нейровыдача',
     u'Попасть в ответы нейросетей можно целенаправленно. '
     u'Это не кнопка: от 3 до 6 месяцев работы', None),
]

TEMY_VVOD = (u'Что даёт предпринимателю полный AI-цикл: исследование, '
             u'стратегия, генерация текстов, картинок и видео, '
             u'автопубликация на 6+ площадках. Продвижение в SEO и GEO')


def slajd_temy_konf(prs):
    """Три темы и подпись эксперта — лист для организатора и прессы.

    Стоит вторым листом и повтором в конце: в начале — чтобы
    сразу было видно, о чём разговор, в конце — чтобы снимок
    последнего кадра увозили с собой вместе с телефоном.
    """
    sl = novyj(prs)

    zagolovok(sl, u'Темы для конференции', y=1.45, kegl=40, max_strok=1)
    blok(sl, PAD, 2.34, W - PAD * 2 - 1.2, TEMY_VVOD, IR, 15,
         color=MUTED, lead=1.45, max_strok=2, kegli=[15, 14, 13],
         max_h=0.76, chto=u'ввод к темам')

    n = len(TEMY)
    zazor = 0.3
    shir = (W - PAD * 2 - zazor * (n - 1)) / n
    verh, vys = 3.32, 2.56

    # Кегль описаний один на все три карточки: подобранный каждой
    # отдельно, он выходил разным, и средняя карточка читалась как
    # сноска к двум соседним.
    kegli_op = [14.5, 13.5, 12.5, 11.5, 11]
    obshchij = min(
        podobrat(o, IR, kegli_op, shir - 0.6,
                 (vys - 1.4) if it is None else (vys - 1.94),
                 1.4 * SHAG, 4)[0]
        for _, _, o, it in TEMY)

    for i, (nomer_, imya, opisanie, itog) in enumerate(TEMY):
        x = PAD + i * (shir + zazor)
        plitka(sl, x, verh, shir, vys, fill=CARD, line=LINE, radius=0.18)
        blok(sl, x + 0.3, verh + 0.28, shir - 0.6, nomer_, IM, 11.5,
             color=LBLUE, bold=True, lead=1.3, max_strok=1)
        blok(sl, x + 0.3, verh + 0.62, shir - 0.6, imya, UBS, 26,
             font=DISP, color=WHITE, bold=True, lead=1.18, max_strok=1,
             kegli=[26, 24, 22, 20])
        blok(sl, x + 0.3, verh + 1.26, shir - 0.6, opisanie, IR, 14.5,
             color=MUTED, lead=1.4, max_strok=4,
             kegli=[obshchij],
             max_h=(vys - 1.4) if itog is None else (vys - 1.94),
             chto=u'описание темы %s' % imya)
        # Итоговая строка прижата к низу карточки, а не поставлена
        # сразу за описанием: описания разной длины, и иначе
        # цифра у второй темы садилась бы прямо на текст.
        if itog:
            blok(sl, x + 0.3, verh + vys - 0.52, shir - 0.6, itog, IS, 14,
                 color=GREEN, bold=True, lead=1.3, max_strok=1,
                 kegli=[14, 13, 12])

    # Полоса с подписью эксперта: лист расходится по редакциям
    # поодиночке, и на нём должно быть, кому звонить.
    sy, svys = verh + vys + 0.28, 0.68
    plitka(sl, PAD, sy, W - PAD * 2, svys, fill=CARD2, line=LINE2,
           radius=0.16)
    kuski = [(u'%s, ' % EKSPERT, {'color': WHITE, 'bold': True}),
             (DOLZHNOST, {'color': MUTED2}),
             (u'     %s     %s     %s' % (TELEFON, AKKAUNT, POCHTA),
              {'color': WHITE, 'bold': True})]
    # Кегль подбирается, а не назначается: строка длинная, и при
    # фиксированном почта уезжала на вторую строку — в полосе,
    # рассчитанной на одну.
    razmer, _ = podobrat(_plain(kuski), IS, [14, 13.5, 13, 12.5, 12, 11.5, 11],
                         W - PAD * 2 - 0.8, svys, 1.3, 1)
    tf = nadpis(sl, PAD + 0.4, sy, W - PAD * 2 - 0.8, svys,
                anchor=MSO_ANCHOR.MIDDLE)
    abzac(tf, kuski, razmer, font=BODY, lead=1.3, first=True)


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


def main(fajl='oranzhevye-listy.pptx'):
    global VSEGO
    # Из пресс-кита берём только то, чего нет в оранжевой презентации:
    # обложку, лист агентов и кейсы она рассказывает сама.
    listy = [slajd_3, slajd_4, slajd_5, slajd_6, slajd_8]
    VSEGO = len(listy)

    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    for list_ in listy:
        list_(prs)

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
    print('собрано:', put, '| листов:', VSEGO)
    return put


if __name__ == '__main__':
    main()
