#!/bin/bash
# Скачивает модели голосов в models/ (в git не лежат, ~290 МБ)
set -e
cd "$(dirname "$0")"; mkdir -p models; cd models
for v in denis dmitri irina ruslan; do
  for ext in onnx onnx.json; do
    curl -sL -o ru_RU-$v-medium.$ext "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/$v/medium/ru_RU-$v-medium.$ext"
  done
done
curl -sL -o silero_v4_ru.pt https://models.silero.ai/models/tts/ru/v4_ru.pt
echo "готово"
