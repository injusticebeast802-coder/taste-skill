#!/bin/sh
# =========================================================
# Установка и обновление сайта на хостинге одной командой.
#
# Скачивает свежую версию сайта из репозитория и раскладывает
# её в папку сайта. Файл config.php с токеном бота НЕ трогает:
# он создаётся один раз и переживает все обновления.
#
# Запуск в Shell-клиенте панели управления:
#   sh -c "$(curl -sSL https://raw.githubusercontent.com/injusticebeast802-coder/taste-skill/main/prompter-moscow/hosting-ru/deploy.sh)"
#
# Обычно берётся ветка main — то, что считается рабочей версией сайта.
# Чтобы выложить другую ветку (например, посмотреть правку до того,
# как она попала в main), укажите её имя:
#   BRANCH=имя-ветки sh -c "$(curl -sSL .../имя-ветки/prompter-moscow/hosting-ru/deploy.sh)"
# =========================================================

set -e

BRANCH="${BRANCH:-main}"
REPO="https://codeload.github.com/injusticebeast802-coder/taste-skill/tar.gz/refs/heads/$BRANCH"
DIR="${SITE_DIR:-$HOME/www/prompter-ai.moscow}"

echo "Ветка: $BRANCH"
echo "Папка сайта: $DIR"

if [ ! -d "$DIR" ]; then
  echo "ОШИБКА: папки нет. Создайте сайт в панели управления и запустите снова."
  echo "Если папка называется иначе, укажите её так:"
  echo "  SITE_DIR=/полный/путь sh -c \"\$(curl -sSL ...)\""
  exit 1
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "Скачиваю свежую версию..."
if command -v curl >/dev/null 2>&1; then
  curl -sSL "$REPO" -o "$TMP/src.tgz"
else
  wget -qO "$TMP/src.tgz" "$REPO"
fi

# Если ветки с таким именем нет, GitHub отдаёт страницу с ошибкой, а не
# архив. Без этой проверки распаковка падала бы с невнятным сообщением.
if ! tar tzf "$TMP/src.tgz" >/dev/null 2>&1; then
  echo "ОШИБКА: скачать не удалось. Проверьте название ветки: $BRANCH"
  exit 1
fi

tar xzf "$TMP/src.tgz" -C "$TMP"

SRC=$(find "$TMP" -maxdepth 2 -type d -name prompter-moscow | head -n 1)
if [ -z "$SRC" ] || [ ! -f "$SRC/index.html" ]; then
  echo "ОШИБКА: в архиве не нашлись файлы сайта."
  exit 1
fi

# Сохраняем настройки: в них токен бота, второй раз их вводить незачем.
if [ -f "$DIR/config.php" ]; then
  cp "$DIR/config.php" "$TMP/config.keep"
  echo "Файл config.php найден и будет сохранён."
fi

echo "Очищаю папку сайта..."
find "$DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

echo "Раскладываю файлы..."
cp "$SRC/index.html" "$SRC/privacy.html" "$SRC/zayavka.html" "$SRC/style.css" "$SRC/script.js" "$SRC/form.js" "$DIR/"
cp "$SRC/robots.txt" "$SRC/sitemap.xml" "$DIR/"
cp -r "$SRC/assets" "$SRC/img" "$SRC/fonts" "$DIR/"

# Презентации по отраслям: на них ведут карточки раздела «Для кого».
# В репозитории они лежат рядом с описанием, на сайт кладём только
# сами файлы .pptx.
mkdir -p "$DIR/presentations"
cp "$SRC/presentation/"*.pptx "$DIR/presentations/"
cp "$SRC/hosting-ru/lead.php" "$DIR/"
cp "$SRC/hosting-ru/.htaccess" "$DIR/"

if [ -f "$TMP/config.keep" ]; then
  cp "$TMP/config.keep" "$DIR/config.php"
else
  cp "$SRC/hosting-ru/config.example.php" "$DIR/config.php"
  echo
  echo "ВНИМАНИЕ: создан пустой config.php."
  echo "Откройте его в менеджере файлов и впишите TG_TOKEN и TG_CHAT_ID,"
  echo "иначе заявки приходить не будут."
fi

# Счётчики Vercel на этом хостинге не работают — убираем лишние запросы.
sed -i '/_vercel\/insights/d; /_vercel\/speed-insights/d' "$DIR/index.html" "$DIR/privacy.html" "$DIR/zayavka.html" 2>/dev/null || true

chmod 644 "$DIR/config.php"
find "$DIR" -type d -exec chmod 755 {} +
find "$DIR" -type f ! -name config.php -exec chmod 644 {} +

# Итог показываем без конвейера: раньше здесь стояло «ls | head -20»,
# и на хостинге это заканчивалось руганью — head не понимает старую
# запись «-20», а следом ls жаловался на оборванный конвейер. Выглядело
# как сбой деплоя, хотя файлы к этому моменту уже разложены.
echo
echo "Готово. В папке сайта $(ls -1A "$DIR" | wc -l) файлов и папок:"
ls -1A "$DIR"

echo
echo "Презентаций выложено: $(ls -1 "$DIR"/presentations/*.pptx 2>/dev/null | wc -l)"
