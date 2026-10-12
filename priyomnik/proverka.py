#!/usr/bin/env python3
"""Проверка анкеты без телеграма.

Бот разговаривает с живым человеком, и сломанная анкета видна только
на клиенте — то есть поздно. Поэтому ход разговора проверяем здесь:
подставляем ответы и смотрим, что бот спросил бы дальше и что отправил
бы менеджеру. Сеть при этом не нужна, токен тоже.

Запуск:  python proverka.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bot as b

oshibki = []


def ravno(bylo, zhdali, chto):
    if bylo != zhdali:
        oshibki.append('%s: ждали %r, вышло %r' % (chto, zhdali, bylo))


# ---------------------------------------------------------- проверки

def proverka_polej():
    """Каждый шаг пропускает верное значение и отвергает мусор."""
    sluchai = [
        ('nazvanie', 'Брусина', True),
        ('nazvanie', 'Б', False),
        ('nisha', 'доставка цветов', True),
        ('nisha', '  ', False),
        ('gorod', 'Одинцово, Заречье', True),
        ('sajt', 'нет', True),
        ('inn', '9702020445', True),
        ('inn', '9702020446', False),          # контрольная цифра не сошлась
        ('inn', '970202044', False),           # девять цифр
        ('inn', 'нет ИНН', False),
        ('telefon', '+7 906 758-77-77', True),
        ('telefon', '12345', False),
    ]
    for pole, tekst, godno in sluchai:
        shag = b.shag_po_imeni(pole)
        znach, oshibka = shag[2](tekst)
        ravno(oshibka is None, godno, 'поле %s на %r' % (pole, tekst))
        if godno:
            ravno(bool(znach), True, 'поле %s вернуло пустое значение' % pole)


def proverka_inn_chistitsya():
    """ИНН из заявки приходит с пробелами и дефисами — их отрезаем."""
    znach, oshibka = b.shag_po_imeni('inn')[2](' 9702-020-445 ')
    ravno(oshibka, None, 'ИНН с пробелами забракован')
    ravno(znach, '9702020445', 'ИНН не очистился')


def proverka_poryadka():
    """Анкета идёт по порядку и заканчивается вопросом про ЛПР."""
    poryadok = [s[0] for s in b.SHAGI]
    ravno(poryadok[0], 'nazvanie', 'первый вопрос')
    ravno(poryadok[-1], 'telefon', 'последний вопрос анкеты')
    ravno(len(set(poryadok)), len(poryadok), 'шаги повторяются')
    for imya in poryadok + [b.SHAG_LPR]:
        if imya not in b.PODPISI:
            oshibki.append('шаг %s без подписи в карточке менеджера' % imya)


def proverka_dlinnogo_otveta():
    """Длинный ответ обрезается до предела, а не уходит в карточку целиком."""
    ravno(len(b.obrezat('А' * 4000)), b.PREDEL, 'длинный ответ не обрезан')
    ravno(b.obrezat('  Брусина   и   сыновья '), 'Брусина и сыновья',
          'лишние пробелы не убраны')
    znach, oshibka = b.shag_po_imeni('nazvanie')[2](b.obrezat('А' * 4000))
    ravno(oshibka, None, 'обрезанное название забраковано')


def proverka_hranilishcha():
    """Незаконченные анкеты переживают перезапуск и протухают за сутки."""
    staroe = b.ANKETY
    b.ANKETY = os.path.join(os.path.dirname(staroe), 'anketa-proverka.json')
    try:
        sostoyanie = {'1': {'shag': 'nisha', 'otvety': {'nazvanie': 'Брусина'},
                            'kogda': __import__('time').time()},
                      '2': {'shag': 'nisha', 'otvety': {}, 'kogda': 0}}
        b.sohranit(sostoyanie)
        snova = b.zagruzit()
        ravno(snova['1']['otvety']['nazvanie'], 'Брусина', 'анкета не пережила запись')

        b.pochistit(snova)
        ravno('2' in snova, False, 'вчерашняя анкета не убрана')
        ravno('1' in snova, True, 'свежую анкету убрали зря')
    finally:
        if os.path.exists(b.ANKETY):
            os.remove(b.ANKETY)
        b.ANKETY = staroe


def proverka_kanala():
    """Название канала приводится к виду @имя, ссылка собирается сама."""
    cfg = {'kanal': 'geniimoscow', 'kanal_ssylka': ''}
    kanal = cfg['kanal'].strip()
    if not kanal.startswith('@') and not kanal.lstrip('-').isdigit():
        kanal = '@' + kanal
    ravno(kanal, '@geniimoscow', 'собачка не добавилась')
    ravno('https://t.me/' + kanal.lstrip('@'), 'https://t.me/geniimoscow',
          'ссылка на канал собралась неверно')


if __name__ == '__main__':
    for proverka in (proverka_polej, proverka_inn_chistitsya, proverka_poryadka,
                     proverka_dlinnogo_otveta, proverka_hranilishcha,
                     proverka_kanala):
        proverka()

    if oshibki:
        print('ОШИБКИ:')
        for o in oshibki:
            print('  -', o)
        sys.exit(1)
    print('анкета в порядке')
