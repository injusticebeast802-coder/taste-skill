#!/bin/sh
# =========================================================
# Установка и обновление программы проверки на хостинге.
#
# Программа живёт ОТДЕЛЬНО от сайтов, в домашней папке, а не в
# папке сайта. Это не придирка: в config.ini лежат ключи, и всё,
# что лежит в папке сайта, при неудачной настройке может быть
# отдано наружу по прямой ссылке. Здесь такой возможности нет.
#
# Запуск в Shell-клиенте панели управления:
#   sh -c "$(curl -sSL https://raw.githubusercontent.com/injusticebeast802-coder/taste-skill/main/analiz/hosting/ustanovka.sh)"
#
# Повторный запуск обновляет программу и не трогает config.ini.
# =========================================================

set -e

BRANCH="${BRANCH:-main}"
REPO="https://codeload.github.com/injusticebeast802-coder/taste-skill/tar.gz/refs/heads/$BRANCH"
DIR="${ANALIZ_DIR:-$HOME/analiz}"

echo "Папка программы: $DIR"
echo

# ---------- Python ----------
# Берём из тех, что стоят на хостинге. Порядок не случаен: самые
# свежие версии иногда выходят раньше, чем под них собирают Pillow,
# и установка падает на сборке из исходников. 3.12 и 3.11 проверены.
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

SRC=$(find "$TMP" -maxdepth 2 -type d -name analiz | head -n 1)
if [ -z "$SRC" ] || [ ! -f "$SRC/bot.py" ]; then
  echo "ОШИБКА: в архиве не нашлись файлы программы."
  exit 1
fi

mkdir -p "$DIR"
# Настройки переживают обновление: второй раз ключи вводить незачем.
[ -f "$DIR/config.ini" ] && cp "$DIR/config.ini" "$TMP/config.keep"

rm -rf "$DIR/nejroanaliz" "$DIR/cloudflare" "$DIR/hosting" "$DIR/shrifty"
# shrifty — шрифт для картинки отчёта. Возим с собой: на хостинге
# системных шрифтов может не быть, и кириллица выйдет квадратиками.
cp -r "$SRC/nejroanaliz" "$SRC/cloudflare" "$SRC/hosting" "$SRC/shrifty" "$DIR/"
cp "$SRC/bot.py" "$SRC/proverka.py" "$SRC/proverka_marshruta.py" \
   "$SRC/requirements.txt" \
   "$SRC/config.example.ini" "$SRC/README.md" "$DIR/"
chmod +x "$DIR/hosting/bot.sh"

if [ -f "$TMP/config.keep" ]; then
  cp "$TMP/config.keep" "$DIR/config.ini"
  echo "Файл config.ini сохранён, ключи на месте."
else
  cp "$SRC/config.example.ini" "$DIR/config.ini"
  NOVYJ=1
fi
# Ключи читает только владелец: на общем хостинге это не лишнее.
chmod 600 "$DIR/config.ini"

# ---------- библиотеки ----------
if [ ! -x "$DIR/venv/bin/python" ]; then
  echo "Готовлю окружение (это минута)..."
  "$PY" -m venv "$DIR/venv"
fi
echo "Ставлю библиотеки..."
"$DIR/venv/bin/pip" install --quiet --upgrade pip
"$DIR/venv/bin/pip" install --quiet -r "$DIR/requirements.txt"
"$DIR/venv/bin/python" -c "import requests, PIL; print('библиотеки на месте')"

# Проверяем шрифт сразу, а не когда менеджер отправит клиенту отчёт
# из квадратиков. Мерим ширину русского слова: у шрифта без кириллицы
# оно либо нулевой ширины, либо ровно такой же, как латинское, —
# потому что рисуются одинаковые пустые квадратики.
cd "$DIR" && "$DIR/venv/bin/python" -c "
from nejroanaliz import report
f = report._font(20)
ru, lat = f.getlength('Проверка'), f.getlength('Proverka')
if ru < 10 or abs(ru - lat) < 0.5:
    raise SystemExit('ВНИМАНИЕ: шрифт без кириллицы, отчёт выйдет квадратиками.')
print('шрифт с кириллицей на месте')
"

# Маршруты бота: что уходит в работу, а что в справку. Ключи не нужны,
# идёт секунду. Проверка нужна потому, что справка и сторож на входе
# один раз уже разъехались: справка предлагала прислать название через
# запятую, а бот такие сообщения молча отбивал этой же справкой.
if (cd "$DIR" && "$DIR/venv/bin/python" "$DIR/proverka_marshruta.py" >/dev/null 2>&1); then
  echo "маршруты бота в порядке"
else
  echo "ВНИМАНИЕ: бот принимает не то, что обещает его справка."
  echo "Подробности:  $DIR/venv/bin/python $DIR/proverka_marshruta.py"
fi

echo
echo "Готово."
echo
if [ -n "$NOVYJ" ]; then
  echo "ДАЛЬШЕ: впишите ключи в $DIR/config.ini"
  echo "  nano $DIR/config.ini"
  echo
  echo "Обязательно: dadata_token, yandex_api_key, yandex_folder_id,"
  echo "yandex_search_key, gigachat_auth_key, telegram_api, allowed_chats."
  echo
fi
echo "Запустить бота:   sh $DIR/hosting/bot.sh start"
echo "Посмотреть, жив:  sh $DIR/hosting/bot.sh status"
echo "Последние строки: sh $DIR/hosting/bot.sh log"
