"""YandexGPT: задаём вопрос и получаем ответ текстом."""

import requests

URL = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'


class AIError(Exception):
    pass


def ask(question, folder_id, api_key, model='yandexgpt-lite', timeout=60):
    body = {
        'modelUri': 'gpt://%s/%s/latest' % (folder_id, model),
        # Низкая температура: нужен обычный, а не выдуманный ответ.
        # При высокой нейросеть чаще сочиняет названия, и проверка
        # показывала бы погоду, а не присутствие компании.
        'completionOptions': {'stream': False, 'temperature': 0.2, 'maxTokens': 1200},
        'messages': [{'role': 'user', 'text': question}],
    }
    r = requests.post(
        URL, json=body,
        headers={'Authorization': 'Api-Key ' + api_key,
                 'x-folder-id': folder_id,
                 'Content-Type': 'application/json'},
        timeout=timeout,
    )
    if r.status_code == 401:
        raise AIError('YandexGPT не принял ключ. Проверьте yandex_api_key.')
    if r.status_code == 403:
        raise AIError('YandexGPT: нет доступа к каталогу. Проверьте yandex_folder_id и права ключа.')
    if r.status_code != 200:
        raise AIError('YandexGPT ответил ошибкой %d: %s' % (r.status_code, r.text[:200]))

    data = r.json() or {}
    alts = ((data.get('result') or {}).get('alternatives') or [])
    if not alts:
        raise AIError('YandexGPT вернул пустой ответ.')
    return ((alts[0].get('message') or {}).get('text') or '').strip()
