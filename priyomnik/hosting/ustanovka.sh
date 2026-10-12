#!/bin/sh
# =========================================================
# Установка и обновление бота-приёмщика на хостинге.
#
# Бот живёт ОТДЕЛЬНО от сайтов, в домашней папке, а не в папке
# сайта. Это не придирка: в config.ini лежит токен, и всё, что
# лежит в папке сайта, при неудачной настройке может быть отдано
# наружу по прямой ссылке. Здесь такой возможности нет.
#
# Ставится рядом с программой проверки, но в свою папку и со своим
# токеном: это разные боты. Приёмщик разговаривает с клиентами,
# программа проверки — только с менеджерами.
#
# Запуск в Shell-клиенте панели управления:
#   sh -c "$(curl -sSL https://raw.githubusercontent.com/injusticebeast802-coder/taste-skill/main/priyomnik/hosting/ustanovka.sh)"
#
# Повторный запуск обновляет бота и не трогает config.ini.
# =========================================================

set -e

BRANCH="${BRANCH:-main}"
REPO="https://codeload.github.com/injusticebeast802-coder/taste-skill/tar.gz/refs/heads/$BRANCH"
DIR="${PRIYOMNIK_DIR:-$HOME/priyomnik}"

echo "Папка бота: $DIR"
echo

# ---------- Python ----------
PY=""
for v in 3.12 3.11 3.13 3.10 3.14; do
  if [ -x "/opt/python/python-$v/bin/python3" ]; then
    PY="/opt/python/python-$v/bin/python3"; break
  fi
done
[ -z "$PY" ] && command -v python3 >/dev/null 2>&1 && PY="$(command -v python3)"

if [ -z "$PY" ]; then
  echo "ОШИБКА: не нашёл Python. Посмотрите, что есть:"
  echo "  ls -d /opt/python/*/bin/python3"
  exit 1
fi
echo "Python: $PY ($("$PY" -V 2>&1))"

# ---------- файлы ----------
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "Скачиваю свежую версию..."
if command -v curl >/dev/null 2>&1; then
  curl -sSL "$REPO" -o "$TMP/src.tgz"
else
  wget -qO "$TMP/src.tgz" "$REPO"
fi
if ! tar tzf "$TMP/src.tgz" >/dev/null 2>&1; then
  echo "ОШИБКА: скачать не удалось. Проверьте название ветки: $BRANCH"
  exit 1
fi
tar xzf "$TMP/src.tgz" -C "$TMP"

SRC=$(find "$TMP" -maxdepth 2 -type d -name priyomnik | head -n 1)
if [ -z "$SRC" ] || [ ! -f "$SRC/bot.py" ]; then
  echo "ОШИБКА: в архиве не нашлись файлы бота."
  exit 1
fi

mkdir -p "$DIR"
# Настройки переживают обновление: второй раз токен вводить незачем.
[ -f "$DIR/config.ini" ] && cp "$DIR/config.ini" "$TMP/config.keep"

rm -rf "$DIR/hosting"
cp -r "$SRC/hosting" "$DIR/"
cp "$SRC/bot.py" "$SRC/inn.py" "$SRC/proverka.py" "$SRC/requirements.txt" \
   "$SRC/config.example.ini" "$SRC/README.md" "$DIR/"
chmod +x "$DIR/hosting/bot.sh"

if [ -f "$TMP/config.keep" ]; then
  cp "$TMP/config.keep" "$DIR/config.ini"
  echo "Файл config.ini сохранён, токен на месте."
else
  cp "$SRC/config.example.ini" "$DIR/config.ini"
  NOVYJ=1
fi
# Токен читает только владелец: на общем хостинге это не лишнее.
chmod 600 "$DIR/config.ini"

# ---------- библиотеки ----------
if [ ! -x "$DIR/venv/bin/python" ]; then
  echo "Готовлю окружение (это минута)..."
  "$PY" -m venv "$DIR/venv"
fi
echo "Ставлю библиотеки..."
"$DIR/venv/bin/pip" install --quiet --upgrade pip
"$DIR/venv/bin/pip" install --quiet -r "$DIR/requirements.txt"
"$DIR/venv/bin/python" -c "import requests; print('библиотеки на месте')"

# Ход анкеты: что бот спросит и что отправит менеджеру. Сеть и токен
# для этого не нужны, идёт секунду. Проверка нужна потому, что
# сломанную анкету видно только на живом клиенте — то есть поздно.
# Вывод не прячем: отправлять человека запускать проверку второй
# раз, чтобы увидеть, что она сказала, — лишний круг на пустом месте.
if (cd "$DIR" && "$DIR/venv/bin/python" "$DIR/proverka.py" > "$TMP/proverka.txt" 2>&1); then
  echo "анкета в порядке"
else
  echo "ВНИМАНИЕ: анкета сломана. Что сказала проверка:"
  sed 's/^/  /' "$TMP/proverka.txt"
fi

echo
echo "Готово."
echo
if [ -n "$NOVYJ" ]; then
  echo "ДАЛЬШЕ: впишите настройки в $DIR/config.ini"
  echo "  nano $DIR/config.ini"
  echo
  echo "Обязательно: telegram_token (или telegram_api), kanal, chat_zayavok."
  echo "И сделайте бота администратором канала — без этого он не умеет"
  echo "проверять подписку."
  echo
fi
echo "Запустить бота:   sh $DIR/hosting/bot.sh start"
echo "Посмотреть, жив:  sh $DIR/hosting/bot.sh status"
echo "Последние строки: sh $DIR/hosting/bot.sh log"
