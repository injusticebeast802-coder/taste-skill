# -*- coding: utf-8 -*-
"""Делает контактные строки в pdf полями, которые менеджер правит сам.

Зачем. Клиентам уходит pdf: pptx в Телеграме открывается через раз.
Но тогда менеджер не может подставить свой телефон — pdf обычно не
редактируется. Решение штатное для pdf: на месте контактных строк
стоят поля формы. Их правит и сохраняет любая бесплатная смотрелка —
Acrobat Reader, Chrome, Яндекс.Браузер, «Просмотр» на маке.

Как собирается:

    python3 sobrat.py --polya --fajl pustaya.pptx
    soffice --headless --convert-to pdf pustaya.pptx
    python3 polya_pdf.py pustaya.pdf prompter-obshchaya-dlya-menedzhera.pdf

Первая команда собирает презентацию без контактных строк и кладёт
рядом polya.json с их координатами, вторая переводит её в pdf, третья
ставит на эти места поля.

Шрифт полей — Helvetica: она есть в любой программе для pdf, её не
нужно зашивать в файл. Кириллицу она не покажет, но в телефоне, почте
и телеграм-аккаунте кириллицы не бывает.
"""
import json, os, sys
import pikepdf
from pikepdf import Array, Dictionary, Name, Pdf, Stream, String

PODSKAZKI = {
    'kontakty-oblozhka': 'Телефон и почта менеджера',
    'telefon': 'Телефон менеджера',
    'pochta': 'Почта менеджера',
    'akkaunt': 'Телеграм менеджера',
}


def ekran(t):
    """Экранирование для строки внутри потока pdf."""
    return t.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def postavit(ishodnik, vyhod, koordinaty):
    dannye = json.load(open(koordinaty, encoding='utf-8'))
    pdf = Pdf.open(ishodnik)

    shrift = pdf.make_indirect(Dictionary(
        Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica,
        Encoding=Name.WinAnsiEncoding))

    polya = []
    for p in dannye:
        stranica = pdf.pages[p['stranica'] - 1]
        vysota = float(stranica.MediaBox[3]) - float(stranica.MediaBox[1])
        x0 = p['x'] * 72
        x1 = (p['x'] + p['w']) * 72
        y0 = vysota - (p['y'] + p['h']) * 72
        y1 = vysota - p['y'] * 72
        sh, vys = x1 - x0, y1 - y0
        kegl = p['kegl']
        cvet = [int(p['cvet'][i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
        da = '/Helv %g Tf %.3f %.3f %.3f rg' % (kegl, cvet[0], cvet[1], cvet[2])

        # Базовая линия по середине коробки: 0.72 кегля — примерная
        # высота прописной буквы в Helvetica.
        niz = (vys - kegl * 0.72) / 2

        vid = Stream(pdf, ('/Tx BMC q BT %s 2 %.2f Td (%s) Tj ET Q EMC'
                           % (da, niz, ekran(p['tekst']))).encode('latin-1'))
        vid.Type = Name.XObject
        vid.Subtype = Name.Form
        vid.BBox = Array([0, 0, sh, vys])
        vid.Resources = Dictionary(Font=Dictionary(Helv=shrift))

        pole = pdf.make_indirect(Dictionary(
            Type=Name.Annot, Subtype=Name.Widget, FT=Name.Tx,
            T=String(p['imya']), V=String(p['tekst']), DV=String(p['tekst']),
            TU=String(PODSKAZKI.get(p['imya'], 'Контакты менеджера')),
            DA=String(da), Ff=0, F=4, Q=0,
            Rect=Array([x0, y0, x1, y1]),
            AP=Dictionary(N=vid), P=stranica.obj))

        if '/Annots' in stranica:
            stranica.Annots.append(pole)
        else:
            stranica.Annots = Array([pole])
        polya.append(pole)

    # NeedAppearances: смотрелка сама перерисует строку после правки.
    pdf.Root.AcroForm = Dictionary(
        Fields=Array(polya), NeedAppearances=True,
        DA=String('/Helv 12 Tf 1 1 1 rg'),
        DR=Dictionary(Font=Dictionary(Helv=shrift)))
    pdf.save(vyhod)
    return len(polya)


if __name__ == '__main__':
    tut = os.path.dirname(os.path.abspath(__file__))
    ishodnik = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tut, 'pustaya.pdf')
    vyhod = sys.argv[2] if len(sys.argv) > 2 else os.path.join(tut, 'dlya-menedzhera.pdf')
    koordinaty = sys.argv[3] if len(sys.argv) > 3 else os.path.join(tut, 'polya.json')
    n = postavit(ishodnik, vyhod, koordinaty)
    print('полей поставлено:', n, '| файл:', vyhod)
