#!/usr/bin/env python3
"""Проверка дороги до телеграма через посредника.

Спрашивает у телеграма имя бота — тем же путём, которым дальше пойдёт
сам бот, — и сверяет, чей бот ответил.

Сверка тут главное. Посредник общий с ботом отчётов, и старый
посредник на пометку b=priyom не смотрит: он ответит, всё будет
выглядеть исправным, а клиенту напишет не тот бот, в котором тот
спрашивал. Сверять есть с чем — номер бота это начало его токена, до
двоеточия.

Запуск:  proverit_dorogu.py <адрес посредника с k=> <токен приёмщика>

Печатает одну строку: «ДА: имя», «ЧУЖОЙ: имя» или «НЕТ: причина».
"""

import json
import sys
import urllib.request

SROK = 40


def sprosit(adres, srok=SROK):
    with urllib.request.urlopen(adres, timeout=srok) as svyaz:
        return svyaz.read().decode('utf-8', 'replace')


def razobrat(telo, nash_token):
    """Что сказал посредник. Отдельно от сети, чтобы можно было проверить."""
    try:
        razbor = json.loads(telo)
    except ValueError:
        return 'НЕТ: посредник ответил не по-телеграмски — %s' % telo[:300].strip()
    if not isinstance(razbor, dict) or not razbor.get('ok'):
        opisanie = (razbor.get('description') if isinstance(razbor, dict)
                    else None)
        return 'НЕТ: %s' % (opisanie or telo[:300].strip())

    otvetil = razbor.get('result') or {}
    imya = otvetil.get('username') or str(otvetil.get('id') or 'без имени')
    nash = nash_token.split(':')[0]
    if str(otvetil.get('id')) != nash:
        return 'ЧУЖОЙ: %s' % imya
    return 'ДА: %s' % imya


def main(argv):
    if len(argv) != 3:
        print('НЕТ: не сказано, куда идти и с каким токеном')
        return 0
    adres, token = argv[1], argv[2]
    try:
        telo = sprosit('%s&m=getMe&b=priyom' % adres)
    except Exception as e:
        print('НЕТ: до посредника не достучался — %s' % e)
        return 0
    print(razobrat(telo, token))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
