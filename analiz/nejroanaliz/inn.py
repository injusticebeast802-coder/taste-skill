"""Проверка ИНН.

Номер проверяется по контрольным цифрам, а не только по длине:
менеджер вводит его руками, и опечатка в одной цифре выдала бы
карточку чужой компании либо пустой ответ справочника.
"""


def normalize(raw):
    """Оставляет только цифры. Пробелы и дефисы при копировании обычны."""
    return ''.join(c for c in str(raw) if c.isdigit())


def _checksum(digits, weights):
    total = sum(int(d) * w for d, w in zip(digits, weights))
    return total % 11 % 10


def is_valid(raw):
    """ИНН юрлица — 10 цифр, ИНН предпринимателя — 12."""
    d = normalize(raw)

    if len(d) == 10:
        return _checksum(d, (2, 4, 10, 3, 5, 9, 4, 6, 8)) == int(d[9])

    if len(d) == 12:
        n11 = _checksum(d, (7, 2, 4, 10, 3, 5, 9, 4, 6, 8))
        n12 = _checksum(d, (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8))
        return n11 == int(d[10]) and n12 == int(d[11])

    return False


def explain(raw):
    """Понятная человеку причина отказа — её показывает бот."""
    d = normalize(raw)
    if not d:
        return 'Не вижу цифр. Пришлите ИНН — 10 цифр у компании, 12 у ИП.'
    if len(d) not in (10, 12):
        return 'В ИНН должно быть 10 цифр у компании или 12 у ИП, а здесь %d.' % len(d)
    if not is_valid(d):
        return 'Такой ИНН не существует: не сходится контрольная цифра. Проверьте, нет ли опечатки.'
    return ''
