#!/bin/sh
# Пересборка пресс-кита: pptx и pdf.
#
#   sh sobrat-vse.sh
#
# Нужны python3 с python-pptx, pillow, fonttools и qrcode, а также
# soffice (LibreOffice Impress) для перевода в pdf.
set -e
cd "$(dirname "$0")"

python3 sobrat.py
soffice --headless --convert-to pdf --outdir . press-kit.pptx >/dev/null

cp press-kit.pptx ../press-kit-genii-prompter.pptx
cp press-kit.pdf  ../press-kit-genii-prompter.pdf
echo '== готово, файлы лежат в pressa/'
