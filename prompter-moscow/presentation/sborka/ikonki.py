# -*- coding: utf-8 -*-
"""Иконки для презентации берём прямо со сайта.

В index.html лежит спрайт: набор <symbol> с контурами. Те же самые
контуры рисуем в png нужного цвета. Так значки в презентации и на
сайте — буквально один и тот же рисунок, а не похожий набор из
стороннего пакета.
"""
import os, re, tempfile
import cairosvg

TUT      = os.path.dirname(os.path.abspath(__file__))
ISHODNIK = os.path.abspath(os.path.join(TUT, '..', '..', 'index.html'))
KUDA     = os.path.join(tempfile.gettempdir(), 'prompter-preza', 'ikonki')
os.makedirs(KUDA, exist_ok=True)

_simvoly = None


def _sprajt():
    global _simvoly
    if _simvoly is None:
        html = open(ISHODNIK, encoding='utf-8').read()
        _simvoly = dict(re.findall(
            r'<symbol id="([^"]+)" viewBox="0 0 24 24">(.*?)</symbol>', html, re.S))
    return _simvoly


def ikonka(imya, cvet, px=192, tolshchina=1.5):
    """Отрисовывает значок спрайта в png. cvet — строка вида '7FC4FF'."""
    fajl = os.path.join(KUDA, '%s-%s-%d.png' % (imya, cvet, px))
    if os.path.exists(fajl):
        return fajl
    telo = _sprajt()['i-' + imya]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'width="%d" height="%d" fill="none" stroke="#%s" stroke-width="%s" '
        'stroke-linecap="round" stroke-linejoin="round">%s</svg>'
        % (px, px, cvet, tolshchina, telo))
    cairosvg.svg2png(bytestring=svg.encode('utf-8'), write_to=fajl,
                     output_width=px, output_height=px)
    return fajl


if __name__ == '__main__':
    for n in ['pencil', 'target', 'send', 'palette', 'check', 'refresh']:
        print(ikonka(n, '7FC4FF'))
