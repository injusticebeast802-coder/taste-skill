# -*- coding: utf-8 -*-
"""Вшивает шрифты сайта внутрь файла презентации.

Зачем: Unbounded и Inter стоят на сайте, но у клиента на компьютере их
почти наверняка нет. Без вшитых шрифтов PowerPoint подставит свой, и
презентация поедет. Формат .pptx позволяет положить файлы шрифтов
внутрь — этим и пользуемся.

Если вдруг PowerPoint не примет вшитые шрифты, он просто подставит
свои: текст останется на месте, файл не сломается.
"""
import os, re, shutil, zipfile, sys

TUT = os.path.dirname(os.path.abspath(__file__))
SHRIFTY = os.path.abspath(os.path.join(TUT, '..', '..', '..', 'analiz', 'shrifty'))
NABOR = [
    # (имя гарнитуры в разметке, файл обычного, файл жирного)
    ('Inter',     'Inter-Regular.ttf',      'Inter-Bold.ttf'),
    ('Unbounded', 'Unbounded-SemiBold.ttf', 'Unbounded-Bold.ttf'),
]
TIP = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/font'


def vshit(ishodnik, itog):
    raspak = 'raspakovka'
    shutil.rmtree(raspak, ignore_errors=True)
    with zipfile.ZipFile(ishodnik) as z:
        z.extractall(raspak)
    os.makedirs(os.path.join(raspak, 'ppt', 'fonts'), exist_ok=True)

    # 1. Сами файлы шрифтов.
    nomer, svyazi, spisok = 0, [], []
    for garnitura, obychnyj, zhirnyj in NABOR:
        idy = []
        for fajl in (obychnyj, zhirnyj):
            nomer += 1
            imya = 'font%d.fntdata' % nomer
            shutil.copy(os.path.join(SHRIFTY, fajl),
                        os.path.join(raspak, 'ppt', 'fonts', imya))
            rid = 'rIdFont%d' % nomer
            idy.append(rid)
            svyazi.append('<Relationship Id="%s" Type="%s" Target="fonts/%s"/>'
                          % (rid, TIP, imya))
        spisok.append(
            '<p:embeddedFont><p:font typeface="%s" pitchFamily="34" charset="0"/>'
            '<p:regular r:id="%s"/><p:bold r:id="%s"/></p:embeddedFont>'
            % (garnitura, idy[0], idy[1]))

    # 2. Тип содержимого для расширения .fntdata.
    put = os.path.join(raspak, '[Content_Types].xml')
    t = open(put, encoding='utf-8').read()
    if 'fntdata' not in t:
        t = t.replace('<Types ', '<Types ', 1)
        t = re.sub(r'(<Types[^>]*>)',
                   r'\1<Default Extension="fntdata" ContentType="application/x-fontdata"/>',
                   t, count=1)
        open(put, 'w', encoding='utf-8').write(t)

    # 3. Связи презентации со шрифтами.
    put = os.path.join(raspak, 'ppt', '_rels', 'presentation.xml.rels')
    t = open(put, encoding='utf-8').read()
    t = t.replace('</Relationships>', ''.join(svyazi) + '</Relationships>')
    open(put, 'w', encoding='utf-8').write(t)

    # 4. Список вшитых шрифтов в presentation.xml. По схеме он стоит
    #    строго после notesSz — иначе PowerPoint не откроет файл.
    put = os.path.join(raspak, 'ppt', 'presentation.xml')
    t = open(put, encoding='utf-8').read()
    if '<p:embeddedFontLst>' not in t:
        m = re.search(r'<p:notesSz[^>]*/>', t)
        if not m:
            raise SystemExit('не нашёл notesSz — не знаю, куда класть список шрифтов')
        t = t[:m.end()] + '<p:embeddedFontLst>' + ''.join(spisok) + \
            '</p:embeddedFontLst>' + t[m.end():]
        t = re.sub(r'(<p:presentation\b(?![^>]*embedTrueTypeFonts)[^>]*?)>',
                   r'\1 embedTrueTypeFonts="1">', t, count=1)
        open(put, 'w', encoding='utf-8').write(t)

    if os.path.exists(itog):
        os.remove(itog)
    with zipfile.ZipFile(itog, 'w', zipfile.ZIP_DEFLATED) as z:
        for koren, _, fajly in os.walk(raspak):
            for f in fajly:
                p = os.path.join(koren, f)
                z.write(p, os.path.relpath(p, raspak))
    shutil.rmtree(raspak, ignore_errors=True)
    print('вшито шрифтов: %d, файл: %s (%.1f МБ)'
          % (nomer, itog, os.path.getsize(itog) / 1048576))


if __name__ == '__main__':
    vshit('obshchaya.pptx', 'obshchaya-so-shriftami.pptx')
