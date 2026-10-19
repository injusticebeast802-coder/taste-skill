# -*- coding: utf-8 -*-
"""Два слайда для пресс-конференции в оформлении «Промптер SMM 2026».

Зачем отдельный файл. Сама презентация собиралась не здесь, и прислать
её не вышло — клиент не пропускает .pptx. Поэтому два листа собраны
отдельно, по снимкам экрана: тёмный фон с тёплыми частицами, тонкая
оранжевая рамка во весь слайд, логотип слева вверху, надпись раздела
справа, карточки со скруглением и оранжевым контуром.

Как вставить: открыть этот файл, выделить оба слайда в панели слева,
скопировать, в своей презентации вставить с «Сохранить исходное
форматирование». Темы ставят вторым листом и повтором в конец,
контакты — вместо прежнего листа контактов.

Шрифт намеренно Arial, а не наш Inter: файл уходит на чужой компьютер,
и шрифта, которого там нет, PowerPoint подставит замену — поедут и
кегли, и переносы. Arial есть везде, а в капители с разрядкой он
близок к начертанию презентации.
"""
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

TUT = os.path.dirname(os.path.abspath(__file__))
SAJT = os.path.abspath(os.path.join(TUT, '..', '..'))
ZNAK = os.path.join(SAJT, 'assets', 'logo.png')
FON = os.path.join(TUT, 'fon.jpg')

W, H = 13.333, 7.5
PAD = 0.9

ORANZH = RGBColor(0xE8, 0x61, 0x1A)
ORANZH_SVET = RGBColor(0xFF, 0x8A, 0x3D)
KARTA = RGBColor(0x16, 0x0E, 0x0A)
BELYJ = RGBColor(0xFF, 0xFF, 0xFF)
SERYJ = RGBColor(0xC9, 0xC6, 0xC2)
SERYJ_2 = RGBColor(0x9A, 0x95, 0x90)
ZELENYJ = RGBColor(0x4A, 0xDE, 0x80)

SHRIFT = 'Arial'

TELEFON = '+7 906 758-77-77'
TELEGA = '@geniimoscow'
POCHTA = 'prompter.moscow@mail.ru'
ADRES = 'prompter-ai.moscow'

TEMY = [
    ('ТЕМА 1', 'Время',
     'Контент-фабрики есть у всех, но процессом управляет человек. '
     'Управление циклом можно отдать самому ИИ'),
    ('ТЕМА 2', 'Деньги',
     'Не платить агентству, не покупать токены, не воевать с '
     'блокировками аккаунтов',
     'от 120–150 000 ₽ в месяц'),
    ('ТЕМА 3', 'Нейровыдача',
     'Попасть в ответы нейросетей можно целенаправленно. Это не '
     'кнопка: от 3 до 6 месяцев работы'),
]

# Кегль у каждой строки свой: почта длиннее телефона вдвое и при общем
# размере переносилась посреди адреса — «mail.r / u».
KONTAKTY = [
    ('ТЕЛЕФОН', TELEFON, 18),
    ('МЕССЕНДЖЕР', TELEGA, 18),
    ('ПОЧТА', POCHTA, 14.5),
]


# ------------------------------------------------------------ основа

def razryadka(run, sotye):
    """Разрядка между буквами.

    В python-pptx её нет, а без неё капитель выглядит сбитой в комок —
    в презентации все заголовки набраны вразрядку.
    """
    run.font._rPr.set('spc', str(int(sotye)))


def nadpis(sl, x, y, w, h, tekst, kegl, cvet=BELYJ, zhirno=False,
           vyravnivanie=PP_ALIGN.LEFT, spc=0, mezhstrochnyj=1.25,
           yakor=MSO_ANCHOR.TOP):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = yakor
    p = tf.paragraphs[0]
    p.alignment = vyravnivanie
    p.line_spacing = mezhstrochnyj
    r = p.add_run()
    r.text = tekst
    r.font.size = Pt(kegl)
    r.font.name = SHRIFT
    r.font.bold = zhirno
    r.font.color.rgb = cvet
    if spc:
        razryadka(r, spc)
    return tb


def karta(sl, x, y, w, h, kontur=ORANZH, tolshchina=1.75, zalivka=KARTA):
    s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                            Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = zalivka
    s.line.color.rgb = kontur
    s.line.width = Pt(tolshchina)
    s.adjustments[0] = min(0.5, 0.16 / min(w, h))
    s.shadow.inherit = False
    return s


def osnova(prs, razdel):
    """Чистый слайд: фон, рамка, логотип, надпись раздела."""
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    sl.shapes.add_picture(FON, 0, 0, Inches(W), Inches(H))

    ramka = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.1), Inches(0.1),
                                Inches(W - 0.2), Inches(H - 0.2))
    ramka.fill.background()
    ramka.line.color.rgb = ORANZH
    ramka.line.width = Pt(1.25)
    ramka.shadow.inherit = False

    sl.shapes.add_picture(ZNAK, Inches(PAD), Inches(0.52),
                          Inches(0.46), Inches(0.46))
    nadpis(sl, PAD + 0.62, 0.6, 4.0, 0.34, 'ПРОМПТЕР', 19, BELYJ, True,
           spc=260)
    nadpis(sl, W - PAD - 5.0, 0.64, 5.0, 0.3, razdel, 12, ORANZH, True,
           vyravnivanie=PP_ALIGN.RIGHT, spc=220)
    return sl


# ------------------------------------------------------------ слайды

def slajd_temy(prs):
    sl = osnova(prs, 'ТЕМЫ ДЛЯ КОНФЕРЕНЦИИ')

    nadpis(sl, PAD, 1.5, W - PAD * 2, 0.9, 'ТЕМЫ ДЛЯ КОНФЕРЕНЦИИ', 40, BELYJ,
           True, vyravnivanie=PP_ALIGN.CENTER, spc=180)
    nadpis(sl, PAD + 1.0, 2.5, W - PAD * 2 - 2.0, 0.6,
           'Что даёт предпринимателю полный AI-цикл: исследования, стратегия, '
           'генерация текстов, картинок и видео, автопубликация на 6+ '
           'площадках. Продвижение в SEO и GEO',
           14, SERYJ, False, vyravnivanie=PP_ALIGN.CENTER,
           mezhstrochnyj=1.45)

    n = len(TEMY)
    zazor = 0.4
    shir = (W - PAD * 2 - zazor * (n - 1)) / n
    verh, vys = 3.35, 2.6
    for i, tema in enumerate(TEMY):
        nomer, imya, opisanie = tema[0], tema[1], tema[2]
        itog = tema[3] if len(tema) > 3 else None
        x = PAD + i * (shir + zazor)
        karta(sl, x, verh, shir, vys)
        nadpis(sl, x + 0.3, verh + 0.32, shir - 0.6, 0.24, nomer, 11, ORANZH,
               True, vyravnivanie=PP_ALIGN.CENTER, spc=200)
        nadpis(sl, x + 0.3, verh + 0.68, shir - 0.6, 0.42, imya, 22, BELYJ,
               True, vyravnivanie=PP_ALIGN.CENTER)
        nadpis(sl, x + 0.34, verh + 1.22, shir - 0.68, 1.0, opisanie, 11,
               SERYJ, False, vyravnivanie=PP_ALIGN.CENTER, mezhstrochnyj=1.4)
        # Итоговая строка прижата к низу карточки, а не поставлена
        # после описания: описания разной длины, и иначе цифра у
        # второй темы садилась бы прямо на текст.
        if itog:
            nadpis(sl, x + 0.25, verh + vys - 0.52, shir - 0.5, 0.32, itog,
                   12.5, ZELENYJ, True, vyravnivanie=PP_ALIGN.CENTER)

    # Полоса с контактами спикера — такая же, как нижняя плашка на
    # слайде тарифов: карточка во всю ширину с оранжевым контуром.
    karta(sl, PAD, H - 1.12, W - PAD * 2, 0.72, kontur=ORANZH,
          tolshchina=2.0)
    nadpis(sl, PAD + 0.4, H - 1.12, W - PAD * 2 - 0.8, 0.72,
           'РУСЛАН ДЁМИН, управляющий партнёр        %s        %s        %s'
           % (TELEFON, TELEGA, POCHTA),
           13, BELYJ, True, vyravnivanie=PP_ALIGN.CENTER,
           yakor=MSO_ANCHOR.MIDDLE)
    return sl


def kod(adres, imya='qr.png'):
    import qrcode
    put = os.path.join(TUT, imya)
    qrcode.make('https://%s' % adres, border=1,
                box_size=10).convert('RGB').save(put)
    return put


def slajd_kontakty(prs):
    sl = osnova(prs, 'КОНТАКТЫ')

    nadpis(sl, PAD, 1.45, W - PAD * 2, 1.0, 'КОНТАКТЫ', 52, BELYJ, True,
           vyravnivanie=PP_ALIGN.CENTER, spc=280)
    nadpis(sl, PAD, 2.6, W - PAD * 2, 0.4,
           'Подключим ваш бизнес к «Промптеру» — напишите или позвоните',
           15, SERYJ, False, vyravnivanie=PP_ALIGN.CENTER)

    n = len(KONTAKTY)
    zazor = 0.45
    shir = (W - PAD * 2 - zazor * (n - 1)) / n
    verh, vys = 3.35, 1.55
    for i, (podpis, znachenie, kegl) in enumerate(KONTAKTY):
        x = PAD + i * (shir + zazor)
        karta(sl, x, verh, shir, vys)
        nadpis(sl, x + 0.25, verh + 0.34, shir - 0.5, 0.26, podpis, 11,
               ORANZH, True, vyravnivanie=PP_ALIGN.CENTER, spc=200)
        nadpis(sl, x + 0.14, verh + 0.78, shir - 0.28, 0.42, znachenie,
               kegl, BELYJ, True, vyravnivanie=PP_ALIGN.CENTER)

    # Код и адрес сайта вместо строки про менеджера: это лист для
    # конференции, а не для клиента конкретного менеджера.
    kw = 1.3
    sl.shapes.add_picture(kod(ADRES), Inches(W / 2 - kw / 2), Inches(5.25),
                          Inches(kw), Inches(kw))
    nadpis(sl, PAD, 6.68, W - PAD * 2, 0.34, ADRES, 17, ORANZH_SVET, True,
           vyravnivanie=PP_ALIGN.CENTER, spc=120)
    return sl


def main(fajl='konferenciya-slajdy.pptx'):
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    slajd_temy(prs)
    slajd_kontakty(prs)
    put = os.path.join(TUT, fajl)
    prs.save(put)
    print('собрано:', put, '| слайдов:', len(prs.slides))
    return put


if __name__ == '__main__':
    main()
