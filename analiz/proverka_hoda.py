#!/usr/bin/env python3
"""Сколько сообщений бот шлёт за одну проверку.

    python proverka_hoda.py

Ключей и связи не нужно: телеграм подменяем. Смысл проверки в том,
что на одну проверку в чате должно оставаться одно-два сообщения, а
не десяток. Один раз их уже было двенадцать, и отчёт терялся среди
«…6 из 24».
"""

import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bot as bot_mod                   # noqa: E402

# Ровно то, что бот печатал в примере из чата.
HOD_PROVERKI = [
    'Ищу компанию в справочнике…',
    'Внимание: по справочнику компания не действующая.',
    'Компания: ООО "БРУСИНА.РУ" · Котельники · строительство деревянных домов и бань',
    'Сайт из анкеты: brusina.ru',
    'Спрашиваю про: строительство деревянных домов и бань, строительство дома',
    'Спрашиваю нейросети: 12 вопросов × 2 — это минута-две…',
    '…6 из 24',
    '…12 из 24',
    '…18 из 24',
    '…24 из 24',
    'Смотрю выдачу Яндекса…',
]


def progon(pravka_razreshena, shag=5.0):
    """Прогоняет ход проверки. Возвращает: сколько сообщений послано,
    сколько правок сделано и что в итоге видит менеджер."""
    poslano, pravok = [], []
    chasy = {'t': 1000.0}

    def api(cfg, method, **p):
        if method == 'sendMessage':
            poslano.append(p['text'])
            return {'ok': True, 'result': {'message_id': 77}}
        if method == 'editMessageText':
            if not pravka_razreshena:
                return {'ok': False, 'description': 'Команда не разрешена: editMessageText'}
            pravok.append(p['text'])
            return {'ok': True, 'result': {'message_id': 77}}
        return {'ok': True}

    bylo_api, bylo_time = bot_mod.api, bot_mod.time.time
    bot_mod.api = api
    bot_mod.time.time = lambda: chasy['t']
    try:
        hod = bot_mod.Hod({}, 1)
        for stroka in HOD_PROVERKI:
            hod(stroka)
            chasy['t'] += shag          # между строками проходит время
        hod.zakonchit()
    finally:
        bot_mod.api, bot_mod.time.time = bylo_api, bylo_time

    vidno = (pravok[-1] if pravok else '\n'.join(poslano))
    return len(poslano), len(pravok), vidno


def main():
    plohо = []

    print('Посредник разрешает править сообщения:')
    poslano, pravok, vidno = progon(True)
    print('  сообщений: %d, правок: %d' % (poslano, pravok))
    if poslano != 1:
        plohо.append('с правкой должно быть одно сообщение, а не %d' % poslano)
    if 'Смотрю выдачу Яндекса…' not in vidno:
        plohо.append('последняя строка не доехала до менеджера')
    if '…24 из 24' not in vidno:
        plohо.append('счётчик не доехал: %r' % vidno[-80:])
    if '…6 из 24' in vidno:
        plohо.append('счётчики копятся вместо того, чтобы заменять друг друга')

    print()
    print('Посредник править не даёт (старая версия):')
    poslano, pravok, vidno = progon(False)
    print('  сообщений: %d, правок: %d' % (poslano, pravok))
    if poslano > 2:
        plohо.append('без правки должно быть не больше двух сообщений, а не %d' % poslano)
    if 'Смотрю выдачу Яндекса…' not in vidno:
        plohо.append('без правки последняя строка не доехала')
    if 'из 24' in vidno:
        plohо.append('счётчики не должны уходить отдельными сообщениями')

    print()
    print('Что в итоге видит менеджер:')
    for stroka in vidno.splitlines():
        print('  | ' + stroka)

    print()
    if plohо:
        print('НЕ В ПОРЯДКЕ:')
        for x in plohо:
            print('  ' + x)
        return 1
    print('Ход проверки укладывается в одно-два сообщения.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
