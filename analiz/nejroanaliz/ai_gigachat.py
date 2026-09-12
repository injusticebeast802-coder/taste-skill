"""GigaChat: сначала берём временный пропуск, потом задаём вопрос.

Пропуск живёт полчаса, поэтому храним его в памяти и обновляем,
когда истёк: иначе на каждый из двенадцати вопросов уходил бы
лишний запрос к сбербанковскому серверу.
"""

import time
import uuid

import requests

# Когда проверка сертификата снята намеренно (gigachat_verify = no),
# urllib3 предупреждает об этом на каждом обращении. На 24 вопросах
# это сорок строк, за которыми не видно самой проверки.
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

OAUTH = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'

# Обычный адрес. У Сбера их несколько: старый — gigachat.devices…,
# новый, для моделей третьего поколения, — api.giga.chat. Путь у них
# разный (у старого есть /api/), поэтому в config.ini задаётся весь
# адрес целиком, а не кусок: гадать, куда подставлять /api/, не надо.
CHAT = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions'


class AIError(Exception):
    pass


_token = {'value': '', 'until': 0}


def _get_token(auth_key, scope, verify, timeout=30):
    now = time.time()
    if _token['value'] and _token['until'] > now + 60:
        return _token['value']

    try:
        return _request_token(auth_key, scope, verify, timeout, now)
    except requests.exceptions.SSLError as e:
        raise AIError('GigaChat: не сошёлся сертификат сервера. Сбер подписывает '
                      'свой сервер российским сертификатом, которого нет в Windows. '
                      'Поставьте в config.ini строку gigachat_verify = no '
                      'или установите сертификат с gu.ru. (%s)' % str(e)[:120])
    except requests.exceptions.RequestException as e:
        raise AIError('GigaChat недоступен: сервер ngw.devices.sberbank.ru не ответил. '
                      'Обычно это или сертификат — тогда поможет gigachat_verify = no, — '
                      'или блокировка порта 9443 у провайдера. (%s)' % str(e)[:120])


def _request_token(auth_key, scope, verify, timeout, now):
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


def _sprosit(url, tok, model, question, verify, timeout):
    return requests.post(
        url,
        headers={'Authorization': 'Bearer ' + tok,
                 'Content-Type': 'application/json',
                 'Accept': 'application/json'},
        json={'model': model,
              'messages': [{'role': 'user', 'content': question}],
              'temperature': 0.2, 'max_tokens': 1200},
        timeout=timeout, verify=verify,
    )


def ask(question, auth_key, scope='GIGACHAT_API_PERS', verify=True,
        model='GigaChat', timeout=90, url=''):
    chat = (url or '').strip() or CHAT
    tok = _get_token(auth_key, scope, verify)

    try:
        r = _sprosit(chat, tok, model, question, verify, timeout)
        if r.status_code == 401:
            # Пропуск мог протухнуть раньше срока — пробуем ещё раз, один
            _token['value'] = ''
            tok = _get_token(auth_key, scope, verify)
            r = _sprosit(chat, tok, model, question, verify, timeout)
    except requests.exceptions.RequestException as e:
        raise AIError('GigaChat: не достучались до %s. (%s)' % (chat, str(e)[:150]))

    if r.status_code == 404:
        raise AIError('GigaChat не знает такого адреса или модели (404). '
                      'Адрес: %s, модель: %s. Проверьте строки gigachat_url и '
                      'gigachat_model в config.ini.' % (chat, model))
    if r.status_code == 403:
        raise AIError('GigaChat отказал в доступе к модели «%s» (403). Модели '
                      'третьего поколения выдают не всем: Ultra в бесплатном '
                      'режиме доступна только физическим лицам. Уберите строку '
                      'gigachat_model, чтобы вернуться к обычной модели. (%s)'
                      % (model, r.text[:150]))
    if r.status_code != 200:
        raise AIError('GigaChat ответил ошибкой %d: %s' % (r.status_code, r.text[:200]))

    choices = (r.json() or {}).get('choices') or []
    if not choices:
        raise AIError('GigaChat вернул пустой ответ.')
    return ((choices[0].get('message') or {}).get('content') or '').strip()
