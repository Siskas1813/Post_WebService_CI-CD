# 9. Проверка конфигурации и HTTP-заголовков

## Цель проверки

Даже если бизнес-логика приложения работает корректно, небезопасная конфигурация HTTP-ответов может облегчить XSS, clickjacking, утечки referrer-данных, подмену MIME-типа, небезопасную работу cookie и раскрытие технической информации. Поэтому конфигурация и заголовки проверяются отдельным блоком.

## Что проверяем

| Проверка | Ожидаемая защита | Где проверяется |
| --- | --- | --- |
| Content-Security-Policy | ограничивает источники скриптов, стилей, картинок и форм | `tests/test_config_headers_security.py` |
| X-Content-Type-Options | `nosniff` | `tests/test_config_headers_security.py` |
| X-Frame-Options или frame-ancestors | защита от clickjacking | `tests/test_config_headers_security.py` |
| Referrer-Policy | ограничивает передачу referrer | `tests/test_config_headers_security.py` |
| Permissions-Policy | отключает лишние browser capabilities | `tests/test_config_headers_security.py` |
| Cookie flags | `HttpOnly`, `SameSite`, `Secure` | `tests/test_config_headers_security.py` |
| Debug mode | не должен быть включен в стартовом файле | `tests/test_config_headers_security.py` |
| Stack trace пользователю | внутренние ошибки не должны раскрываться | `tests/test_config_headers_security.py` |
| Версия сервера | ответ не должен раскрывать лишнюю информацию о сервере | ручная проверка через `curl` / ZAP |

## Инструменты

- OWASP ZAP: пассивные правила находят отсутствие security headers.
- `curl`: быстрая проверка заголовков ответа.
- Browser DevTools: вкладка Network показывает response headers и cookies.
- `pytest`: воспроизводимые проверки для отчета.

## Как установить

Зависимости уже входят в `requirements-dev.txt`. Если окружение еще не подготовлено:

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## Как запустить pytest-проверки

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\Activate.ps1
.\scripts\run_config_headers_tests.ps1
```

После запуска будут созданы отчеты:

- `reports\config-headers\pytest-config-headers.txt`
- `reports\config-headers\summary.md`

## Ручная проверка через curl

Сначала запустить приложение:

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\Activate.ps1
python app.py
```

В другом терминале:

```powershell
curl.exe -I http://127.0.0.1:5000/
curl.exe -I http://127.0.0.1:5000/dashboard
curl.exe -i http://127.0.0.1:5000/api/v1/config
```

Что смотреть в ответе:

```text
Content-Security-Policy
X-Content-Type-Options
X-Frame-Options
Referrer-Policy
Permissions-Policy
Set-Cookie
Server
```

Если заголовки отсутствуют, это фиксируется как недостаток конфигурации. Если `Server` раскрывает конкретную технологию и версию, это также можно указать как информационное раскрытие.

## Ручная проверка через браузер

1. Открыть `http://127.0.0.1:5000`.
2. Открыть DevTools.
3. Перейти во вкладку Network.
4. Выбрать HTML-запрос.
5. Проверить блок Response Headers.
6. Во вкладке Application / Cookies проверить флаги `HttpOnly`, `Secure`, `SameSite`.

## Найденные слабые места в проекте

| Проблема | Файл | Причина |
| --- | --- | --- |
| Нет глобальных security headers | `webmail/__init__.py` | не настроен `after_request` обработчик |
| Cookie без `Secure` | `webmail/__init__.py` | не задан `SESSION_COOKIE_SECURE=True` |
| Cookie без `SameSite` | `webmail/__init__.py` | не задан `SESSION_COOKIE_SAMESITE` |
| Debug mode включен при запуске | `app.py` | `app.run(..., debug=True)` |
| Внутренние ошибки показываются пользователю | `webmail/routes/admin.py` | SQL-консоль выводит `str(exc)` |
| Слишком открытые CORS-заголовки API | `webmail/routes/api.py` | `Access-Control-Allow-Origin: *` и `Access-Control-Allow-Headers: *` |

## Как исправить

Пример базовой настройки заголовков:

```python
@app.after_request
def set_security_headers(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response
```

Пример настройки cookie:

```python
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
```

Пример безопасного запуска:

```python
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
```

Для production-запуска лучше использовать WSGI-сервер и reverse proxy, а debug-режим оставлять только для локальной разработки.

## Как интерпретировать результаты

В текущем состоянии тесты показывают наличие конфигурационных проблем. После исправления ожидаемое поведение должно измениться:

- security headers должны присутствовать в HTML и API-ответах;
- session cookie должна иметь `HttpOnly`, `Secure`, `SameSite`;
- debug mode должен быть выключен;
- пользователь не должен видеть внутренние SQL-ошибки или stack trace;
- API не должен отдавать `Access-Control-Allow-Origin: *` без необходимости.
