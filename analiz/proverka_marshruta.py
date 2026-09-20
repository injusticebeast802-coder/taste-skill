#!/usr/bin/env python3
"""Проверка маршрутов бота: что уходит в работу, а что в справку.

    python proverka_marshruta.py

Ключи не нужны, идёт одну секунду. Смысл в том, чтобы справка и
сторож на входе не разъезжались. Один раз уже разъехались: справка
предлагала прислать «Flowwow, доставка цветов, Москва», а сторож
пропускал дальше только сообщения с цифрами и такой запрос молча
отбивал — показывал ту же справку с тем же примером.
"""

import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bot as bot_mod                   # noqa: E402

# Сообщение, должно ли уйти в работу
SLUCHAI = [
    ('Pho-House, Вьетнамская закусочная, Москва', True),
    ('Flowwow, доставка цветов, Москва',          True),
    ('Бритва, барбершоп в Москве',                True),
    ('Дом Сантехники, сантехника, Рязань',        True),
    ('ООО "Нияма", суши-бар, Москва',             True),
    ('9702020445',                                True),
    ('9702020445 Flowwow',                        True),
    ('9702020445 Flowwow, доставка цветов',       True),
    ('привет',                                    False),
    ('Москва',                                    False),
    ('спасибо, всё ок',                           False),
    ('да, давай',                                 False),
    ('ок, жду',                                   False),
    ('привет, как дела',                          False),
    ('/start',                                    False),
    ('помощь',                                    False),
]


def main():
    otpravleno = []
    zapusheno = []

    # Подменяем только отправку в телеграм и сам разбор: проверяем
    # маршрут, а не отчёт. Настоящий анализ стоит денег и минут.
    bot_mod.send = lambda cfg, chat, txt: otpravleno.append(txt)
    bot_mod.send_photo = lambda *a, **k: otpravleno.append('[картинка]')

    def vmesto_analiza(text, cfg, progress=None):
        zapusheno.append(text)
        raise bot_mod.runner.RunError('(проверяем маршрут, анализ не идёт)')

    bot_mod.runner.analyze = vmesto_analiza

    plohо = []
    for text, nado in SLUCHAI:
        del otpravleno[:], zapusheno[:]
        bot_mod.handle({'allowed_chats': ''}, 1, text)
        poshlo = bool(zapusheno)
        itog = 'в работу' if poshlo else 'справка'
        ladno = poshlo == nado
        if not ladno:
            plohо.append('%s — ушло в «%s», а надо было в «%s»'
                         % (text, itog, 'в работу' if nado else 'справка'))
        print('  %-44s %-9s %s' % (text[:43], itog, 'ок' if ladno else 'НЕ ТАК'))

    # Отдельно: каждый пример из справки должен приниматься. Справка —
    # обещание пользователю, и нарушать его нельзя.
    print()
    primery = ['9702020445 Flowwow, доставка цветов', '9702020445',
               'Flowwow, доставка цветов, Москва']
    for p in primery:
        if p not in bot_mod.HELP:
            plohо.append('пример «%s» пропал из справки' % p)
            continue
        del otpravleno[:], zapusheno[:]
        bot_mod.handle({'allowed_chats': ''}, 1, p)
        if not zapusheno:
            plohо.append('пример из справки «%s» бот не принимает' % p)
        print('  пример из справки: %-38s %s'
              % (p[:37], 'принят' if zapusheno else 'ОТБИТ'))

    print()
    if plohо:
        print('НЕ В ПОРЯДКЕ:')
        for s in plohо:
            print('  ' + s)
        return 1
    print('Все маршруты в порядке.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
