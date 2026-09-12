"""Поиск упоминания компании в чужом тексте.

Нейросеть пишет название как хочет: «Белый Клык», «БЕЛЫЙ КЛЫК»,
«Белый клык» — и почти никогда «ООО "БЕЛЫЙ КЛЫК"». Поэтому сравниваем
не строки целиком, а приведённые к общему виду: только буквы и цифры,
в нижнем регистре, ё=е.
"""

import re

_KEEP = re.compile(r'[^0-9a-zа-я ]+')


def fold(text):
    t = (text or '').lower().replace('ё', 'е')
    t = _KEEP.sub(' ', t)
    return ' '.join(t.split())


def mentioned(text, name):
    """Названо ли имя компании в тексте."""
    n = fold(name)
    if len(n) < 3:
        return False
    return n in fold(text)


def position(text, name):
    """Каким по счёту названо в перечислении.

    Нейросеть отвечает списком, и разница между первым и седьмым
    местом для клиента существенная. Считаем по порядку появления
    названий, выделенных нумерацией или переносом строки. Если списка
    нет, но упоминание есть — возвращаем 1.
    """
    if not mentioned(text, name):
        return None

    lines = [l.strip(' -•*\t') for l in (text or '').splitlines() if l.strip()]
    numbered = [l for l in lines if re.match(r'^\d+[.)]\s*', l) or len(lines) > 3]
    seq = numbered or lines

    n = fold(name)
    for i, line in enumerate(seq, 1):
        if n in fold(line):
            return i
    return 1


def domain_of(url):
    """Домен из адреса, без www — для сравнения сайта в выдаче."""
    u = (url or '').strip().lower()
    u = re.sub(r'^[a-z]+://', '', u)
    u = u.split('/')[0].split('?')[0]
    return u[4:] if u.startswith('www.') else u
