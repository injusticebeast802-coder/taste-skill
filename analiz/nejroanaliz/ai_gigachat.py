"""GigaChat: сначала берём временный пропуск, потом задаём вопрос.

Пропуск живёт полчаса, поэтому храним его в памяти и обновляем,
когда истёк: иначе на каждый из двенадцати вопросов уходил бы
лишний запрос к сбербанковскому серверу.
"""

import time
import uuid

import requests

OAUTH = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
CHAT = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions'


class AIError(Exception):
    pass


_token = {'value': '', 'until': 0}


def _get_token(auth_key, scope, verify, timeout=30):
    now = time.time()
    if _token['value'] and _token['until'] > now + 60:
        return _token['value']

    r = requests.post(
        OAUTH,
        headers={'Authorization': 'Basic ' + auth_key,
                 'RqUID': str(uuid.uuid4()),
                 'Content-Type': 'application/x-www-form-urlencoded',
                 'Accept': 'application/json'},
        data={'scope': scope},
        timeout=timeout, verify=verify,
    )
    if r.status_code == 401:
        raise AIError('GigaChat не принял ключ авторизации. Проверьте gigachat_auth_key.')
    if r.status_code != 200:
        raise AIError('GigaChat не выдал пропуск, ошибка %d: %s' % (r.status_code, r.text[:200]))

    data = r.json() or {}
    tok = data.get('access_token')
    if not tok:
        raise AIError('GigaChat вернул ответ без пропуска.')

    # expires_at приходит в миллисекундах
    _token['value'] = tok
    _token['until'] = (data.get('expires_at') or 0) / 1000.0 or (now + 1500)
    return tok


def ask(question, auth_key, scope='GIGACHAT_API_PERS', verify=True, model='GigaChat', timeout=90):
    tok = _get_token(auth_key, scope, verify)
    r = requests.post(
        CHAT,
        headers={'Authorization': 'Bearer ' + tok,
                 'Content-Type': 'application/json',
                 'Accept': 'application/json'},
        json={'model': model,
              'messages': [{'role': 'user', 'content': question}],
              'temperature': 0.2, 'max_tokens': 1200},
        timeout=timeout, verify=verify,
    )
    if r.status_code == 401:
        # Пропуск мог протухнуть раньше срока — пробуем ещё раз, один
        _token['value'] = ''
        tok = _get_token(auth_key, scope, verify)
        r = requests.post(
            CHAT,
            headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'},
            json={'model': model, 'messages': [{'role': 'user', 'content': question}],
                  'temperature': 0.2, 'max_tokens': 1200},
            timeout=timeout, verify=verify,
        )
    if r.status_code != 200:
        raise AIError('GigaChat ответил ошибкой %d: %s' % (r.status_code, r.text[:200]))

    choices = (r.json() or {}).get('choices') or []
    if not choices:
        raise AIError('GigaChat вернул пустой ответ.')
    return ((choices[0].get('message') or {}).get('content') or '').strip()
