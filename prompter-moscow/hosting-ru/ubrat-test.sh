#!/bin/sh
# =========================================================
# Убрать тестовую копию сайта: test.prompter-ai.moscow.
#
# Зачем. Тестовая копия — это весь сайт целиком под вторым адресом.
# Для поисковика это не черновик, а второй такой же сайт, и он
# показывает в выдаче то один, то другой. По запросу с именем
# управляющего партнёра наверх выходила именно тестовая копия.
#
# Папку копии скрипт очищает и оставляет в ней одно правило: любой
# адрес отвечает «переехало навсегда» и ведёт на боевой сайт. Просто
# удалить папку хуже: адрес ещё месяцами висит в выдаче, отдавая
# ошибку, а накопленный вес никуда не передаётся.
#
# Запуск в Shell-клиенте панели управления:
#   sh -c "$(curl -sSL https://raw.githubusercontent.com/injusticebeast802-coder/taste-skill/main/prompter-moscow/hosting-ru/ubrat-test.sh)"
#
# Если папка называется иначе:
#   SITE_DIR=/полный/путь sh -c "$(curl -sSL ...)"
# =========================================================

set -e

BOEVOJ="https://prompter-ai.moscow"
DIR="${SITE_DIR:-$HOME/www/test.prompter-ai.moscow}"

echo "Папка тестовой копии: $DIR"

if [ ! -d "$DIR" ]; then
  echo "ОШИБКА: папки нет. Посмотрите её имя в панели управления и укажите:"
  echo "  SITE_DIR=/полный/путь sh -c \"\$(curl -sSL ...)\""
  exit 1
fi

# Три проверки подряд: скрипт стирает папку целиком, и ошибка в пути
# здесь стоит дороже, чем лишняя строка кода.
case "$DIR" in
  *test*) ;;
  *) echo "ОШИБКА: в пути нет слова test. Это не похоже на тестовую копию."; exit 1 ;;
esac
if [ "$DIR" = "$HOME" ] || [ "$DIR" = "$HOME/www" ] || [ "$DIR" = "/" ]; then
  echo "ОШИБКА: так можно стереть лишнее."; exit 1
fi
if [ -d "$HOME/www/prompter-ai.moscow" ] && [ "$DIR" = "$HOME/www/prompter-ai.moscow" ]; then
  echo "ОШИБКА: это папка боевого сайта."; exit 1
fi

echo "Очищаю..."
find "$DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

cat > "$DIR/.htaccess" <<'HTACCESS'
# Тестовая копия закрыта: всё уводим на боевой сайт.
# Папка .well-known остаётся доступной — через неё продлевается
# сертификат, и без исключения он перестал бы обновляться.
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteCond %{REQUEST_URI} !^/\.well-known/
  RewriteRule ^(.*)$ https://prompter-ai.moscow/$1 [R=301,L]
</IfModule>
<IfModule !mod_rewrite.c>
  RedirectMatch 301 ^/(?!\.well-known/)(.*)$ https://prompter-ai.moscow/$1
</IfModule>
HTACCESS

# Запасной вариант на случай, если переадресация почему-то не
# сработает: пустая страница с запретом на индексацию и ссылкой.
cat > "$DIR/index.html" <<'STRANICA'
<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="robots" content="noindex, nofollow">
<link rel="canonical" href="https://prompter-ai.moscow/">
<meta http-equiv="refresh" content="0; url=https://prompter-ai.moscow/">
<title>Переехало на prompter-ai.moscow</title>
<p>Сайт переехал: <a href="https://prompter-ai.moscow/">prompter-ai.moscow</a></p>
STRANICA

cat > "$DIR/robots.txt" <<'ROBOTS'
User-agent: *
Disallow: /
ROBOTS

chmod 644 "$DIR/.htaccess" "$DIR/index.html" "$DIR/robots.txt"

echo
echo "Готово. В папке осталось:"
ls -1A "$DIR"
echo
echo "Проверить в браузере: https://test.prompter-ai.moscow/"
echo "Должен открыться $BOEVOJ — адрес в строке меняется сам."
echo
echo "Дальше, в Яндекс Вебмастере:"
echo "  1. Добавьте test.prompter-ai.moscow, если его там нет."
echo "  2. «Индексирование» → «Переезд сайта» — укажите главным"
echo "     prompter-ai.moscow."
echo "  3. «Инструменты» → «Удаление страниц» — уберите адреса копии,"
echo "     которые уже в выдаче."
echo "Через пару недель, когда копия пропадёт из поиска, подпапку и"
echo "сам поддомен можно удалить в панели управления."
