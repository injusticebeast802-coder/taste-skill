#!/usr/bin/env python3
"""Проверка того, что отчёт говорит клиенту.

    python proverka_otcheta.py

Ключей и связи не нужно: ответы нейросетей и выдачу подставляем.
Проверка следит не за вёрсткой, а за смыслом. Дважды уже выходило
так, что цифры верные, а читаются наоборот:

  • рядом с «нейросети не называют вас ни разу» стояло «1-е место
    в поиске Яндекса» — клиент видел единицу и успокаивался, хотя
    разбор ровно об обратном;
  • место бралось лучшее из пяти запросов, и по одной удачной строке
    выходило, что в поиске всё хорошо, хотя по трём другим сайта не
    было вовсе.
"""

import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nejroanaliz import report                    # noqa: E402
from nejroanaliz import run as runner             # noqa: E402

BOLSHIE = '1. Теремъ\n2. Зодчий\n3. Good Wood\n4. Русские Хоромы\n5. Эко-Дом\n'
MESTNYE = '1. Теремъ\n2. Котельники-Строй\n'


def dannye(sosedi=('Котельники-Строй', 'Эко-Дом', 'Дом Ладный'), nazvali=0):
    ai = []
    for i in range(24):
        ai.append({'engine': 'YandexGPT' if i % 2 else 'GigaChat',
                   'query': 'q', 'answer': BOLSHIE if i % 2 else MESTNYE,
                   'mentioned': i < nazvali, 'position': 2 if i < nazvali else None,
                   'error': ''})
    search = [
        {'query': 'строительство деревянных домов и бань Котельники', 'position': 4, 'error': ''},
        {'query': 'строительство деревянных домов Котельники', 'position': 1, 'error': ''},
        {'query': 'строительство бань Котельники', 'position': None, 'error': ''},
        {'query': 'строительство дома Котельники', 'position': 19, 'error': ''},
        {'query': 'строительная компания Котельники', 'position': None, 'error': ''},
    ]
    company = {
        'name': 'БРУСИНА.РУ', 'full_name': 'ООО "БРУСИНА.РУ"', 'brand': 'Брусина',
        'city': 'Котельники', 'industry': 'строительство деревянных домов и бань',
        'kind': 'строительство деревянных домов и бань', 'kind_from_lead': True,
        'names': ['Брусина', 'БРУСИНА.РУ', 'brusina'],
        'sosedi': list(sosedi), 'sosedi_gde': 'Котельники',
    }
    return report.build(company, 'brusina.ru', ai, search)


def main():
    plohо = []
    d = dannye()

    # --- про поиск: ни лучшего места, ни похвалы ---
    stroka = report.search_line(d)
    print('Про поиск:')
    print('  ' + stroka)
    for zapreshcheno in ('лучшее место', 'вы наверху', 'удерживаем'):
        if zapreshcheno in stroka:
            plohо.append('строка про поиск снова хвалит место: «%s»' % zapreshcheno)
    if '2 запросам из 5' not in stroka:
        plohо.append('в строке про поиск нет полной картины: %r' % stroka)
    if d['search_v_top10'] != 2:
        plohо.append('в топ-10 насчитали %d вместо 2' % d['search_v_top10'])

    # --- сколько мест в ответе ---
    print()
    print('Мест в одном ответе нейросети: %d' % d['nazyvayut_v_otvete'])
    if d['nazyvayut_v_otvete'] < 2:
        plohо.append('не посчитали, сколько компаний называет нейросеть')

    # --- соседи отдельно от крупных, без повторов ---
    verhnie = [imya for imya, _ in d['rivals']]
    nizhnie = [imya for imya, _ in d['sosedi']]
    print()
    print('Кого называют вместо вас: %s' % ', '.join(verhnie))
    print('Кто работает рядом:       %s' % ', '.join(nizhnie))
    povtory = [x for x in nizhnie if x in verhnie]
    if povtory:
        plohо.append('соседи попали в оба списка: %s' % ', '.join(povtory))
    if 'Котельники-Строй' not in nizhnie:
        plohо.append('сосед пропал из своего блока: %r' % (nizhnie,))
    if not any(n for _, n in d['sosedi']):
        plohо.append('упоминания соседей не посчитались: %r' % (d['sosedi'],))
    if 'Дом Ладный' not in nizhnie:
        plohо.append('сосед без упоминаний выпал, а он и есть довод')

    # --- итоговая фраза под соседями ---
    print()
    for opisanie, sos, nazvali in (
            ('соседей называют, клиента нет', ('Котельники-Строй', 'Эко-Дом'), 0),
            ('не называют никого', ('Дом Ладный',), 0),
            ('называют и клиента', ('Котельники-Строй',), 6)):
        dd = dannye(sos, nazvali)
        fraza = report.sosedi_line(dd)
        print('  %-30s %s' % (opisanie + ':', fraza))
        if not fraza:
            plohо.append('нет итоговой фразы: %s' % opisanie)
    pusto = report.sosedi_line(dannye((), 0))
    if pusto:
        plohо.append('без соседей фраза быть не должна: %r' % pusto)

    # --- склонения ---
    print()
    pары = [(1, 'компанию'), (2, 'компании'), (5, 'компаний'), (21, 'компанию'), (11, 'компаний')]
    for n, nado in pары:
        bylo = report.sklonenie(n, 'компанию', 'компании', 'компаний')
        if bylo != nado:
            plohо.append('%d %s, а надо %s' % (n, bylo, nado))
    print('  склонений проверено: %d' % len(pары))

    # --- где ищем соседей ---
    print()
    mesta = [
        ((['Заречье'], 'Одинцово'), [('Заречье', 'Одинцово'), ('Одинцово', '')]),
        (([], 'Котельники'), [('Котельники', '')]),
        ((['ЮЗАО', 'Одинцово'], 'Москва'), [('ЮЗАО', 'Москва'), ('Одинцово', 'Москва')]),
        ((['Котельники'], 'Котельники'), [('Котельники', '')]),
        (([], ''), []),
    ]
    for (rajony, gorod), nado in mesta:
        bylo = runner.mesta_poiska(rajony, gorod)
        if bylo != nado:
            plohо.append('места поиска для %r+%r: вышло %r, надо %r'
                         % (rajony, gorod, bylo, nado))
    print('  наборов мест проверено: %d' % len(mesta))

    # --- картинка рисуется и не падает ---
    put = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'otchety')
    os.makedirs(put, exist_ok=True)
    for brand in ('genii', 'prompter'):
        report.draw_png(d, os.path.join(put, 'proverka-%s.png' % brand), brand=brand)
    print()
    print('  картинки нарисованы: otchety/proverka-genii.png и -prompter.png')

    print()
    if plohо:
        print('НЕ В ПОРЯДКЕ:')
        for x in plohо:
            print('  ' + x)
        return 1
    print('Отчёт говорит то, что задумано.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
