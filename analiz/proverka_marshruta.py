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
    '🔢 ИНН: 7707083893\n'
    '📦 Род деятельности: стоматология\n'
    '👔 ЛПР: да\n'
    '📍 Источник: бесплатный анализ\n'
    '🕒 21.09.2026, 16:40 МСК'
)

# Заявка с расширенной анкеты: город с районами, сайт и что пробовали.
# Конкурентов и запросы анкета больше не спрашивает — их дописывает
# менеджер руками, и это следующий случай.
ZAYAVKA_ANKETA = (
    ZAYAVKA_KOROTKAYA.replace('📍 Источник: бесплатный анализ',
                              '📍 Источник: углублённый анализ · анкета')
    + '\n\n— для углублённого анализа —\n'
      '🌍 Город и районы: Москва, ЮЗАО и Одинцово\n'
      '🔗 Сайт: https://romashka.ru/\n'
      '🧪 Пробовали: контекст'
)

# Та же заявка, дописанная менеджером. Бот обязан понимать эти строки:
# полей в анкете нет, но менеджер конкурентов клиента обычно знает.
ZAYAVKA_POLNAYA = (
    ZAYAVKA_ANKETA
    + '\nКонкуренты: Дента, Белый клык'
      '\nКак ищут: имплантация зубов под ключ, детский стоматолог'
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
    (ZAYAVKA_ANKETA,                              True),
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
    nado = ('7707083893', 'Ромашка', 'стоматология', 'Москва')
    if razbor != nado:
        plohо.append('из заявки вышло %r, а надо %r' % (razbor, nado))
    print('  из заявки: %s' % (razbor,))

    anketa = bot_mod.runner.razobrat_zayavku(ZAYAVKA_ANKETA)
    if 'rivals' in anketa or 'queries' in anketa:
        plohо.append('анкета не должна присылать конкурентов и запросы: %r' % (anketa,))
    if bot_mod.runner.domen_iz(anketa.get('site')) != 'romashka.ru':
        plohо.append('сайт из анкеты не прочитался: %r' % (anketa,))
    print('  из анкеты: %s' % sorted(anketa))

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

    # Район из анкеты должен отделяться от города: город идёт в вопрос,
    # район — в поиск соседей и в часть вопросов.
    print()
    mesto = bot_mod.runner.razdelit_mesto('Москва, ЮЗАО и Одинцово')
    if mesto != ('Москва', ['ЮЗАО', 'Одинцово']):
        plohо.append('место разобрано как %r' % (mesto,))
    print('  место: %s' % (mesto,))

    # Четверть вопросов должна уходить про район: клиента ищут рядом
    # с домом, и по району ответ бывает совсем другой.
    s_rajonom = q_mod.build({
        'industry': 'стоматология', 'kind': 'стоматология',
        'kind_from_lead': True, 'city': 'Москва', 'rajony': ['ЮЗАО']}, limit=12)
    pro_rajon = [q for q in s_rajonom if 'ЮЗАО' in q]
    if not pro_rajon:
        plohо.append('вопросов про район не нашлось: %r' % (s_rajonom[:3],))
    if len(s_rajonom) != 12:
        plohо.append('вопросов вышло %d вместо 12' % len(s_rajonom))
    print('  вопросов про район: %d из %d' % (len(pro_rajon), len(s_rajonom)))

    # Названия соседей вынимаются из заголовков выдачи. Подборки вроде
    # «Топ-10 стоматологий» компанией считаться не должны.
    from nejroanaliz import search_yandex as sy_mod
    zagolovki = [
        ('Стоматология «Дента-Люкс» — лечение зубов в Ясенево', True),
        ('Белый Клык | стоматологическая клиника', True),
        ('Зубная фея - детская стоматология ЮЗАО', True),
        ('Стоматологии в ЮЗАО: 45 клиник, цены, отзывы', False),
        ('Топ-10 стоматологий Юго-Западного округа', False),
        ('Цены на имплантацию зубов в Москве', False),
        ('Все стоматологии района — адреса и телефоны', False),
    ]
    for zag, nado_tak in zagolovki:
        golova = sy_mod._golova(zag)
        vyshlo = sy_mod._pohozhe_na_nazvanie(golova, 'стоматология',
                                             ['ЮЗАО', 'Москва', 'Ясенево'])
        if vyshlo != nado_tak:
            plohо.append('заголовок «%s» сочли %s' % (
                zag, 'названием' if vyshlo else 'подборкой'))
    print('  заголовков разобрано: %d' % len(zagolovki))

    # Справочники отсеиваются по границам доменных имён, а не по
    # вхождению подстроки. Иначе zubfeya.ru попадал в справочники
    # из-за «ya.ru», и сайт компании терялся вместе с ним.
    hosty = [
        ('zubfeya.ru', False), ('vkusno.ru', False), ('privitok.ru', False),
        ('supermarket-mebeli.ru', False), ('romashka.ru', False),
        ('ya.ru', True), ('maps.yandex.ru', True), ('m.vk.com', True),
        ('market.yandex.ru', True), ('www.zoon.ru', True), ('hh.ru', True),
    ]
    for host, nado_tak in hosty:
        if sy_mod.spravochnik(host) != nado_tak:
            plohо.append('%s сочли %s' % (
                host, 'справочником' if not nado_tak else 'сайтом компании'))
    print('  доменов проверено: %d' % len(hosty))

    # И весь отбор соседей целиком, на подставной выдаче.
    vydacha = [
        {'url': 'https://zoon.ru/msk/', 'title': 'Стоматологии в ЮЗАО: 45 клиник', 'text': ''},
        {'url': 'https://denta-lux.ru/', 'title': 'Стоматология «Дента-Люкс» — Ясенево', 'text': ''},
        {'url': 'https://msk.denta-lux.ru/', 'title': 'Стоматология «Дента-Люкс» — Ясенево', 'text': ''},
        {'url': 'https://top10.ru/', 'title': 'Топ-10 стоматологий округа', 'text': ''},
        {'url': 'https://romashka.ru/', 'title': 'Ромашка — стоматология в Ясенево', 'text': ''},
        {'url': 'https://zubfeya.ru/', 'title': 'Зубная фея - детская стоматология', 'text': ''},
    ]
    bylo_raw = sy_mod.raw_search
    sy_mod.raw_search = lambda q, f, k, timeout=20: vydacha
    try:
        ryadom = sy_mod.sosedi('стоматология', 'ЮЗАО', 'Москва', 'f', 'k',
                               svoi=['Ромашка'], limit=5)
        nado_ryadom = ['Стоматология «Дента-Люкс»', 'Зубная фея']
        if ryadom != nado_ryadom:
            plohо.append('соседи: вышло %r, а надо %r' % (ryadom, nado_ryadom))
        print('  соседи из выдачи: %s' % ryadom)

        # Поиск упал — проверка не должна падать вместе с ним.
        def slomalsya(*a, **k):
            raise sy_mod.SearchError('поиск не ответил')
        sy_mod.raw_search = slomalsya
        if sy_mod.sosedi('стоматология', 'ЮЗАО', 'Москва', 'f', 'k') != []:
            plohо.append('сломанный поиск не должен ронять проверку')
    finally:
        sy_mod.raw_search = bylo_raw
    print('  сломанный поиск: проверка продолжается')

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
