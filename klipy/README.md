# Клипы из пресс-конференции 20.10.2026

Вертикальные клипы 1080×1920 для TikTok и VK Клипов с выступлением Руслана
Демина. Исходник: запись Телемоста на Яндекс Диске
(https://disk.yandex.ru/i/X8_vF9ofOXpJJQ).

## Что здесь

| Путь | Что это |
|---|---|
| `teksty_k_klipam.txt` | описания и хэштеги к каждому клипу, порядок публикации |
| `covers/` | обложки для VK Клипов |
| `specs/*.json` | разметка клипа: таймкоды, заголовок, вырезанные куски, кадры инфографики |
| `specs/*.words.json` | субтитры по словам (Whisper medium, вычищены вручную) |
| `tools/render_clip.py` | сборка клипа: фон, карточка, субтитры, плашка, призыв в конце |
| `tools/beats.py` | инфографика в карточке: счётчик, точки, полосы, цепочка, список |
| `tools/sheet.py` | лист кадров для проверки клипа |
| `tools/covers.py` | обложки |
| `tools/make_avatar.py` | аватарка из фото, фон вырезается через rembg |
| `assets/` | аватарка, вырезанная фигура Руслана, маска карточки |

Сами видео в git не лежат, они слишком тяжёлые. Их можно пересобрать из
разметки.

## Как пересобрать клип

```bash
pip install faster-whisper "rembg[cpu]"   # если нужно заново распознать речь или сделать аватарку
python3 tools/render_clip.py specs/01_kapery.json
python3 tools/sheet.py 01_kapery           # проверить кадры
```

В `render_clip.py` пути `S` (рабочая папка с `input.mp4`, `fonts/`,
`assets/`) и `REPO` прописаны в начале файла. Поменяй их под свою машину.
Шрифты берутся из `analiz/shrifty`, фон из
`prompter-moscow/presentation/konferenciya/fon.jpg`, логотипы из
`prompter-moscow/assets/logo.png` и `genii/assets/mark.png`.
