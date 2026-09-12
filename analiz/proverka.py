#!/usr/bin/env python3
"""Проверка одной компании без телеграма — из командной строки.

    python proverka.py 7707083893

Нужна, чтобы убедиться, что ключи заведены правильно, не поднимая
бота: ошибки видно сразу в окне.
"""

import sys
import os

# Вывод в utf-8: на Windows консоль по умолчанию в cp866, и русские
# сообщения превращались бы в мусор или роняли программу.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import load_config          # noqa: E402
from nejroanaliz import run as runner  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print('Укажите ИНН: python proverka.py 7707083893')
        return 1

    cfg = load_config()
    try:
        data = runner.analyze(sys.argv[1], cfg, progress=lambda m: print(m))
    except runner.RunError as e:
        print('\n%s' % e)
        return 1
    except Exception as e:
        # Всё остальное — тоже человеку, а не простынёй из питона.
        print('\nНе получилось: %s' % e)
        print('\nЕсли непонятно, в чём дело, пришлите эти две строки —')
        print('разберёмся.')
        return 1

    print('\n' + runner.as_text(data))
    print('\nКартинка: %s' % os.path.abspath(data['png']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
