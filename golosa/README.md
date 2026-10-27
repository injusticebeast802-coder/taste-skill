# Голоса для озвучки

Русская озвучка текста, работает локально, без подписок. Девять голосов и
девять эффектов. Примеры лежат в `demo/`: файлы `1_golos_*` — чистые голоса,
`2_effekt_*` — эффекты на голосах Дмитрия и Ксюши.

## Голоса и лицензии

| Голос | Движок | Можно в рекламу |
|---|---|---|
| denis, dmitri (мужские) | Piper | да, CC0 |
| irina (женский) | Piper | лицензия не указана, лучше не брать |
| ruslan (мужской) | Piper | нет, только некоммерческое использование |
| aidar, eugene (мужские), baya, kseniya, xenia (женские) | Silero v4 | нет, только некоммерческое использование |

Для роликов Промптера и ГенИИ бери **denis** или **dmitri**.

## Эффекты

`clean` — чистый голос, `android` — андроид, `robot` — робот, `villain` — злодей,
`cartoon` — мультяшный, `giant` — великан, `radio` — рация, `phone` — телефон,
`whisper` — эхо в пещере, `announcer` — диктор.

## Как озвучить

```bash
pip install piper-tts torch --index-url https://download.pytorch.org/whl/cpu   # torch нужен только для Silero
bash download_models.sh
python3 say.py "Текст для озвучки" --voice dmitri --fx android -o golos.mp3
python3 say.py --list
```

Модели весят около 290 МБ, поэтому в git не лежат. `download_models.sh`
скачивает их в `models/`.
