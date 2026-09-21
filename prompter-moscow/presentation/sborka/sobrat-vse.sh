#!/bin/sh
# Пересборка общей презентации целиком: pptx, pdf для клиента и pdf с
# полями, которые менеджер правит прямо в смотрелке.
#
#   sh sobrat-vse.sh
#
# Нужны python3 с python-pptx, pillow, cairosvg, fonttools и pikepdf,
# а также soffice (LibreOffice) для перевода в pdf.
set -e
cd "$(dirname "$0")"
RYADOM=..

echo '== обычная презентация'
python3 sobrat.py
soffice --headless --convert-to pdf obshchaya.pptx >/dev/null

echo '== версия с полями для менеджера'
python3 sobrat.py --polya --fajl pustaya.pptx
soffice --headless --convert-to pdf pustaya.pptx >/dev/null
python3 polya_pdf.py pustaya.pdf dlya-menedzhera.pdf polya.json

cp obshchaya.pptx       "$RYADOM/prompter-obshchaya.pptx"
cp obshchaya.pdf        "$RYADOM/prompter-obshchaya.pdf"
cp dlya-menedzhera.pdf  "$RYADOM/prompter-obshchaya-dlya-menedzhera.pdf"
echo '== готово, файлы лежат в presentation/'
