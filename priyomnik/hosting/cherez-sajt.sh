#!/bin/sh
# =========================================================
# Перевести бота-приёмщика на дорогу через сайт.
#
# ЗАЧЕМ. До api.telegram.org с этого хостинга хода нет: бот при
# запуске пишет «нет связи» по обеим версиям адресов и дальше молчит.
# А tg.php на сайте до телеграма достаёт — им же уходят заявки с форм.
# Значит, пусть бот ходит туда: бот -> свой сайт -> телеграм.
#
# ЧТО ДЕЛАЕТ. Три правки, которые иначе пришлось бы делать руками в
# трёх файлах, и проверка, что дорога заработала:
#   1. кладёт токен приёмщика в config.php сайта (TG_TOKEN_PRIYOM);
#   2. вписывает адрес посредника в config.ini бота (telegram_api);
#   3. спрашивает у телеграма через эту дорогу имя бота — если имя
#      пришло, дорога рабочая.
#
# Запуск:
#   sh ~/priyomnik/hosting/cherez-sajt.sh
#
# Если сайт лежит не в ~/www/genii-ai.ru:
#   SITE_DIR=/полный/путь sh ~/priyomnik/hosting/cherez-sajt.sh
# =========================================================

set -e

DIR="${PRIYOMNIK_DIR:-$HOME/priyomnik}"
INI="$DIR/config.ini"

# ---------- где сайт ----------
if [ -n "$SITE_DIR" ]; then
  SAJT="$SITE_DIR"
else
  SAJT=""
  for d in "$HOME/www/genii-ai.ru" "$HOME/www/prompter-ai.moscow"; do
    [ -f "$d/tg.php" ] && SAJT="$d" && break
  done
fi

if [ -z "$SAJT" ] || [ ! -f "$SAJT/tg.php" ]; then
  echo "Не нашёл tg.php. Укажите папку сайта:"
  echo "  SITE_DIR=/полный/путь sh $0"
  exit 1
fi
echo "Сайт: $SAJT"

if [ ! -f "$SAJT/config.php" ]; then
  echo "Рядом с tg.php нет config.php. Сначала обновите сайт:"
  echo '  sh -c "$(curl -sSL https://raw.githubusercontent.com/injusticebeast802-coder/taste-skill/main/genii/hosting-ru/deploy.sh)"'
  exit 1
fi

# Посредник до недавнего времени знал одного бота. Старый файл примет
# запрос, но ответит токеном бота отчётов — человек спросит у одного
# бота, а ответит ему другой. Такое глазами не поймаешь.
if ! grep -q 'TG_TOKEN_PRIYOM' "$SAJT/tg.php"; then
  echo "tg.php на сайте старый, он не знает про второго бота."
  echo "Сначала обновите сайт:"
  echo '  sh -c "$(curl -sSL https://raw.githubusercontent.com/injusticebeast802-coder/taste-skill/main/genii/hosting-ru/deploy.sh)"'
  exit 1
fi

[ -f "$INI" ] || { echo "Нет $INI — сначала поставьте бота."; exit 1; }

PY="$DIR/venv/bin/python"
[ -x "$PY" ] || PY=$(command -v python3) || { echo "Нет python."; exit 1; }

# ---------- токен приёмщика из config.ini ----------
TOKEN=$("$PY" - "$INI" <<'EOF'
import re, sys
tekst = open(sys.argv[1], encoding='utf-8', errors='replace').read()
najden = re.search(r'(?m)^\s*telegram_token\s*=\s*(.+?)\s*$', tekst)
znachenie = najden.group(1) if najden else ''
print('' if znachenie in ('', '...') else znachenie)
EOF
)
if [ -z "$TOKEN" ]; then
  echo "В $INI не заполнен telegram_token — без него посреднику нечего подставлять."
  exit 1
fi

# ---------- пароль посредника из config.php ----------
KLYUCH=$("$PY" - "$SAJT/config.php" <<'EOF'
import re, sys
tekst = open(sys.argv[1], encoding='utf-8', errors='replace').read()
najden = re.search(r"define\(\s*'TG_RELAY_KEY'\s*,\s*'([^']*)'", tekst)
print(najden.group(1) if najden else '')
EOF
)

if [ -z "$KLYUCH" ]; then
  # Пароль придумываем сами: он должен совпасть в двух файлах, а оба
  # мы и правим. Человеку придумывать нечего.
  KLYUCH=$("$PY" -c "import secrets; print(secrets.token_hex(20))")
  "$PY" - "$SAJT/config.php" "$KLYUCH" <<'EOF'
import io, re, sys
put, klyuch = sys.argv[1], sys.argv[2]
tekst = io.open(put, encoding='utf-8').read()
novyj = re.sub(r"define\(\s*'TG_RELAY_KEY'\s*,\s*''\s*\)",
               "define('TG_RELAY_KEY', '%s')" % klyuch, tekst, count=1)
if novyj == tekst:
    novyj = tekst.rstrip() + "\n\ndefine('TG_RELAY_KEY', '%s');\n" % klyuch
io.open(put, 'w', encoding='utf-8').write(novyj)
EOF
  echo "Пароль посредника был пуст — придумал новый и вписал."
fi

# ---------- токен приёмщика в config.php ----------
"$PY" - "$SAJT/config.php" "$TOKEN" <<'EOF'
import io, re, sys
put, token = sys.argv[1], sys.argv[2]
tekst = io.open(put, encoding='utf-8').read()
stroka = "define('TG_TOKEN_PRIYOM', '%s');" % token
novyj, skolko = re.subn(r"define\(\s*'TG_TOKEN_PRIYOM'\s*,\s*'[^']*'\s*\);",
                        stroka.replace('\\', '\\\\'), tekst, count=1)
if not skolko:
    novyj = tekst.rstrip() + "\n\n/* Токен бота-приёмщика: вписан\n   cherez-sajt.sh. */\n" + stroka + "\n"
io.open(put, 'w', encoding='utf-8').write(novyj)
print('Токен приёмщика на месте в config.php.')
EOF

# ---------- адрес посредника в config.ini ----------
SAJT_IMYA=$(basename "$SAJT")
ADRES="https://$SAJT_IMYA/tg.php?k=$KLYUCH"

"$PY" - "$INI" "$ADRES" <<'EOF'
import io, re, sys
put, adres = sys.argv[1], sys.argv[2]
tekst = io.open(put, encoding='utf-8').read()
novyj, skolko = re.subn(r'(?m)^\s*telegram_api\s*=.*$',
                        'telegram_api = ' + adres.replace('\\', '\\\\'),
                        tekst, count=1)
if not skolko:
    novyj = tekst.rstrip() + '\n\ntelegram_api = ' + adres + '\n'
io.open(put, 'w', encoding='utf-8').write(novyj)
print('Адрес посредника на месте в config.ini.')
EOF
chmod 600 "$INI"

# ---------- проверка дороги ----------
# Спрашиваем у телеграма имя бота через ту самую дорогу, которой
# дальше пойдёт бот. Пришло имя — работает всё: и пароль посредника,
# и токен, и ход с хостинга наружу.
echo
echo "Проверяю дорогу: бот -> $SAJT_IMYA -> телеграм…"
OTVET=$("$PY" - "$ADRES" <<'EOF'
import json, sys, urllib.request
adres = sys.argv[1] + '&m=getMe&b=priyom'
try:
    with urllib.request.urlopen(adres, timeout=40) as svyaz:
        telo = svyaz.read().decode('utf-8', 'replace')
except Exception as e:
    print('НЕТ: до посредника не достучался — %s' % e)
    sys.exit(0)
try:
    razbor = json.loads(telo)
except ValueError:
    print('НЕТ: посредник ответил не по-телеграмски — %s' % telo[:300])
    sys.exit(0)
if razbor.get('ok'):
    print('ДА: %s' % (razbor['result'].get('username') or razbor['result'].get('id')))
else:
    print('НЕТ: %s' % razbor.get('description'))
EOF
)

case "$OTVET" in
  "ДА: "*)
    echo "Дорога рабочая, телеграм отвечает про бота @${OTVET#ДА: }"
    echo
    sh "$DIR/hosting/bot.sh" restart
    echo
    echo "Через полминуты посмотрите журнал:"
    echo "  sh $DIR/hosting/bot.sh log"
    ;;
  *)
    echo "$OTVET"
    echo
    echo "Бота не перезапускаю: он упрётся в то же самое."
    echo "Что смотреть дальше — страница самопроверки посредника:"
    echo "  $ADRES&m=proverka"
    echo "Она покажет, какие адреса телеграма отвечают с хостинга и"
    echo "нужен ли работник Cloudflare."
    exit 1
    ;;
esac
