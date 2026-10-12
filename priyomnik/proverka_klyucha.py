#!/usr/bin/env python3
"""Проверка, что бот и сайт одинаково понимают ключ подписки.

Ключ выдаёт бот на питоне, а проверяет его сайт на php. Подпись
считается в двух разных языках по одной формуле, и разойтись они могут
незаметно: ошибёшься в обрезке или в кодировке — и ни одна заявка не
получит отметки о подписке, а понять почему будет не по чему.

Поэтому здесь ключ выдаётся настоящим кодом бота и проверяется
настоящим кодом сайта: функция берётся прямо из lead.php, а не
переписывается заново.

Запуск:  python proverka_klyucha.py

Если php или файлы сайта недоступны — проверка молча пропускается:
на хостинге бот живёт отдельно от сайта, и это не ошибка.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bot as b

SEKRET = 'proverochnyj-sekret-40-znakov-dlinoj-abc'
# Сайтов два, и ключ проверяет каждый у себя. Разойтись они могут
# незаметно: правку перенесли на один сайт и забыли про второй, а
# заметно это станет только по заявкам без отметки о подписке.
KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAJTY = [
    ('ГенИИ', os.path.join(KOREN, 'genii', 'hosting-ru', 'lead.php')),
    ('Промптер', os.path.join(KOREN, 'prompter-moscow', 'hosting-ru', 'lead.php')),
]

oshibki = []


def vyrezat_funkciyu(ishodnik, imya):
    """Достаёт функцию из php-файла по фигурным скобкам."""
    nachalo = ishodnik.find('function %s(' % imya)
    if nachalo < 0:
        return None
    i = ishodnik.index('{', nachalo)
    glubina = 0
    for j in range(i, len(ishodnik)):
        if ishodnik[j] == '{':
            glubina += 1
        elif ishodnik[j] == '}':
            glubina -= 1
            if glubina == 0:
                return ishodnik[nachalo:j + 1]
    return None


def sprosit_php(klyuch, funkciya):
    with tempfile.TemporaryDirectory() as papka:
        put = os.path.join(papka, 'proba.php')
        with open(put, 'w', encoding='utf-8') as f:
            f.write("<?php\ndefine('RAZBOR_SECRET', '%s');\n%s\n"
                    "echo podpiskaPoKlyuchu($argv[1]);\n" % (SEKRET, funkciya))
        gotovo = subprocess.run(['php', put, klyuch],
                                capture_output=True, text=True, timeout=30)
        return gotovo.stdout.strip()


def main():
    if not shutil.which('php'):
        print('php не найден — проверку пропускаю')
        return 0
    est = [(imya, put) for imya, put in SAJTY if os.path.exists(put)]
    if not est:
        print('lead.php рядом нет — проверку пропускаю')
        return 0

    for imya, put in est:
        funkciya = vyrezat_funkciyu(open(put, encoding='utf-8').read(),
                                    'podpiskaPoKlyuchu')
        if not funkciya:
            oshibki.append('%s: в lead.php нет функции podpiskaPoKlyuchu' % imya)
            continue
        proverit_sajt(imya, funkciya)

    if oshibki:
        print('ОШИБКИ:')
        for o in oshibki:
            print('  -', o)
        return 1
    print('бот и сайты понимают ключ одинаково: %s'
          % ', '.join(imya for imya, _ in est))
    return 0


def proverit_sajt(imya, funkciya):
    cfg = {'sekret_ssylki': SEKRET}

    def plohо(chto):
        oshibki.append('%s: %s' % (imya, chto))

    # 1. Свежий ключ сайт принимает и возвращает номер человека.
    klyuch = b.klyuch_dlya(cfg, 777000123)
    otvet = sprosit_php(klyuch, funkciya)
    if otvet != '777000123':
        plohо('свежий ключ не принят: php ответил %r' % otvet)

    # 2. Подделанный ключ отвергается.
    porchenyj = klyuch[:-1] + ('A' if klyuch[-1] != 'A' else 'B')
    if sprosit_php(porchenyj, funkciya) != '':
        plohо('подделанный ключ прошёл проверку')

    # 3. Чужой секрет не подходит.
    chuzhoj = b.klyuch_dlya({'sekret_ssylki': 'drugoj-sekret'}, 777000123)
    if sprosit_php(chuzhoj, funkciya) != '':
        plohо('ключ с чужим секретом прошёл проверку')

    # 4. Просроченный ключ виден как просроченный, а не как чужой:
    #    менеджеру это разные новости.
    telo = '777000123.%d' % (int(time.time()) - 60)
    import base64, hashlib, hmac
    syroe = hmac.new(SEKRET.encode(), telo.encode(), hashlib.sha256).digest()
    staryj = '%s.%s' % (telo, base64.urlsafe_b64encode(syroe)
                        .decode('ascii').rstrip('=')[:27])
    otvet = sprosit_php(staryj, funkciya)
    if otvet != 'prosrochen':
        plohо('просроченный ключ: php ответил %r' % otvet)

    # 5. Пустой ключ — просто нет отметки, не ошибка.
    if sprosit_php('', funkciya) != '':
        plohо('пустой ключ дал отметку о подписке')

    # 6. Мусор вместо ключа не роняет php.
    for musor in ('abc', '1.2', '..', '1.2.3.4', 'a.b.c'):
        if sprosit_php(musor, funkciya) != '':
            plohо('мусор %r прошёл проверку' % musor)


if __name__ == '__main__':
    sys.exit(main())
