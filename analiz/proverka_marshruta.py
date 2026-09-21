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

# Заявка с сайта, вставленная целиком. Менеджер именно так и делает:
# пересылает сообщение, а не перепечатывает поля руками.
ZAYAVKA_KOROTKAYA = (
    '🎁 Заявка на БЕСПЛАТНЫЙ АНАЛИЗ\n'
    '👤 Имя: Иван\n'
    '📞 Телефон: +7 999 000-11-22\n'
    '📧 Почта: ivan@romashka.ru\n'
    '🏢 Компания: Ромашка\n'
    '📦 Род деятельности: стоматология\n'
    '👔 ЛПР: да\n'
    '📍 Источник: бесплатный анализ\n'
    '🕒 21.09.2026, 16:40 МСК'
)

ZAYAVKA_POLNAYA = (
    ZAYAVKA_KOROTKAYA.replace('📍 Источник: бесплатный анализ',
                              '📍 Источник: углублённый анализ · анкета')
    + '\n\n— для углублённого анализа —\n'
      '🌍 Город и районы: Москва, ЮЗАО и Одинцово\n'
      '🔗 Сайт: https://romashka.ru/\n'
      '🥊 Конкуренты: Дента, Белый клык\n'
      '🔍 Как ищут: имплантация зубов под ключ, детский стоматолог\n'
      '📡 Уже есть: vk.com/romashka\n'
      '🧪 Пробовали: контекст'
)

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
    (ZAYAVKA_KOROTKAYA,                           True),
    (ZAYAVKA_POLNAYA,                             True),
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
        podpis = ' '.join(text.split())[:43]
        print('  %-44s %-9s %s' % (podpis, itog, 'ок' if ladno else 'НЕ ТАК'))

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

    # Что именно бот вытащил из вставленной заявки. Маршрут может быть
    # верным, а поля — потеряться: тогда проверка пойдёт не про ту
    # компанию и не в том городе, и заметить это будет уже поздно.
    print()
    razbor = bot_mod.runner.parse_request(ZAYAVKA_POLNAYA)
    nado = ('', 'Ромашка', 'стоматология', 'Москва')
    if razbor != nado:
        plohо.append('из заявки вышло %r, а надо %r' % (razbor, nado))
    print('  из заявки: %s' % (razbor,))

    dop = bot_mod.runner.razobrat_zayavku(ZAYAVKA_POLNAYA)
    proverki = [
        ('сайт', bot_mod.runner.domen_iz(dop.get('site')), 'romashka.ru'),
        ('конкуренты', bot_mod.runner.spisok(dop.get('rivals')), ['Дента', 'Белый клык']),
        ('запросы', bot_mod.runner.spisok(dop.get('queries')),
         ['имплантация зубов под ключ', 'детский стоматолог']),
    ]
    for imya, bylo, nado_tak in proverki:
        if bylo != nado_tak:
            plohо.append('%s из анкеты: вышло %r, а надо %r' % (imya, bylo, nado_tak))
        print('  %-12s %s' % (imya + ':', bylo))

    # Слова клиента должны идти первыми в вопросах нейросетям: ради
    # этого поле в анкете и заведено.
    from nejroanaliz import queries as q_mod
    uzkie, _ = q_mod.subjects_for({
        'industry': 'стоматология', 'kind': 'стоматология', 'kind_from_lead': True,
        'own_queries': bot_mod.runner.spisok(dop.get('queries'))})
    if uzkie[:2] != ['имплантация зубов под ключ', 'детский стоматолог']:
        plohо.append('запросы из анкеты не встали первыми: %r' % (uzkie,))
    print('  спросим про: %s' % ', '.join(uzkie))

    # Конкурент из анкеты обязан попасть в список, даже если его не
    # назвали ни разу: ноль — это тоже ответ клиенту.
    from nejroanaliz import report as r_mod
    ryadom = r_mod._rivals([{'answer': '1. Улыбка\n2. Дента'}], ['Ромашка'],
                           ['Дента', 'Белый клык'])
    if ('Белый клык', 0) not in ryadom:
        plohо.append('конкурент без упоминаний выпал из списка: %r' % (ryadom,))
    print('  конкуренты в отчёте: %s' % ryadom)

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
