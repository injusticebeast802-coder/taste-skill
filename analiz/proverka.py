#!/usr/bin/env python3
"""Проверка одной компании без телеграма — из командной строки.

    python proverka.py 7707083893

Нужна, чтобы убедиться, что ключи заведены правильно, не поднимая
бота: ошибки видно сразу в окне.
"""

import sys
import os

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

    print('\n' + runner.as_text(data))
    print('\nКартинка: %s' % os.path.abspath(data['png']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
