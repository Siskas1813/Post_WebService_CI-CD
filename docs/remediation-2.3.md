# 2.3. Устранение уязвимостей в исходном коде и конфигурации

## Цель раздела

После выявления уязвимостей на этапах SAST, SCA, DAST, проверки API, авторизации, вложений и HTTP-конфигурации в проект были внесены изменения, направленные на снижение риска эксплуатации. Исправления закреплены автоматическими security regression tests.

## Сводная таблица исправлений

| Уязвимость | Где была проблема | Что изменено |
| --- | --- | --- |
| SQL-инъекция в авторизации | `webmail/routes/auth.py` | вход выполняется через параметризованный SQL-запрос, пароль проверяется отдельно |
| Пароли в открытом виде | `webmail/db.py` | демонстрационные пароли сохраняются в виде хеша Werkzeug |
| Open redirect после login | `webmail/routes/auth.py` | параметр `next` проверяется как локальный URL |
| IDOR при просмотре писем | `webmail/routes/mailbox.py`, `webmail/services/mail_service.py` | письмо выдается только отправителю, получателю, участнику CC или администратору |
| IDOR в API писем | `webmail/routes/api.py` | API требует сессию и проверяет принадлежность объекта пользователю |
| API без авторизации | `webmail/routes/api.py` | все чувствительные API-методы требуют авторизации, админские методы требуют роль `admin` |
| SQL-инъекции в поиске и админке | `webmail/services/mail_service.py`, `webmail/routes/admin.py`, `webmail/routes/api.py` | пользовательские параметры передаются через placeholders `?` |
| Mass assignment в API | `webmail/routes/api.py` | обновлять можно только разрешенный список полей |
| Избыточные данные API | `webmail/routes/api.py` | поле `password` и секреты не возвращаются в ответах |
| Permissive CORS | `webmail/routes/api.py` | удалены wildcard-заголовки `*`, разрешается только текущий origin |
| Небезопасная загрузка файлов | `webmail/routes/mailbox.py`, `webmail/security.py` | добавлены allowlist расширений, проверка MIME-типа, `secure_filename`, серверное имя файла |
| Загрузка `.pkl` и `pickle.load` | `webmail/routes/mailbox.py` | десериализация пользовательских файлов полностью удалена |
| Directory Traversal при скачивании | `webmail/routes/mailbox.py` | скачивание выполняется по `attachment_id`, а не по параметру `path` |
| Перезапись файлов | `webmail/security.py` | файл хранится под уникальным UUID-именем |
| XSS через шаблоны | `templates/*.html` | удалены небезопасные `|safe` для пользовательских данных |
| CSRF для HTML-форм | `webmail/__init__.py`, `templates/*.html` | добавлен session-based CSRF token для POST-форм |
| Отсутствие HTTP security headers | `webmail/__init__.py` | добавлены CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` |
| Небезопасные cookie-флаги | `webmail/__init__.py` | включены `HttpOnly` и `SameSite=Lax`; `Secure` включается через production-переменную |
| Debug mode | `app.py` | `debug=False`, запуск только на `127.0.0.1` |
| Раскрытие внутренних SQL-ошибок | `webmail/routes/admin.py` | пользователю возвращается общее сообщение без деталей БД |
| Уязвимые версии зависимостей | `requirements.txt` | обновлены Flask, Jinja2 и Werkzeug до версий без известных CVE |

## Основные изменения в коде

### Авторизация

Было: SQL-запрос собирался через f-string и позволял обойти вход конструкцией вида `employee' --`.

Стало:

```python
row = conn.execute(
    "SELECT username, password, role, full_name, department, title FROM users WHERE username = ?",
    (username,),
).fetchone()
```

Пароль теперь проверяется через `verify_password`, а не участвует в SQL-условии.

### Доступ к письмам

Метод `get_mail` теперь принимает пользователя и роль. Для обычного пользователя добавлено условие доступа:

```python
recipient IN (?, ?) OR sender IN (?, ?) OR cc = ?
```

Если письмо не принадлежит пользователю, веб-интерфейс и API возвращают `404`.

### API

Для API добавлены функции:

```python
_require_api_auth()
_require_admin_api()
```

Они отделяют обычные методы от административных. Ответы API больше не раскрывают пароль пользователя, конфигурационные секреты и данные чужих писем.

### Вложения

Загрузка перенесена на безопасную схему:

1. исходное имя очищается через `secure_filename`;
2. расширение проверяется по allowlist;
3. MIME-тип проверяется по разрешенному списку;
4. файл сохраняется под UUID-именем;
5. скачивание выполняется через `/download/<attachment_id>`.

Таким образом пользователь больше не управляет путем файла на сервере.

### Конфигурация HTTP

В `create_app` добавлен `after_request` обработчик, который выставляет защитные заголовки:

```python
Content-Security-Policy
X-Content-Type-Options
X-Frame-Options
Referrer-Policy
Permissions-Policy
```

Для cookie включены:

```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
```

Для production-режима дополнительно включается:

```powershell
$env:CORP_MAIL_COOKIE_SECURE = "1"
```

### Зависимости

По результатам SCA обновлены пакеты:

```text
Flask 3.0.3 -> 3.1.3
Jinja2 3.1.4 -> 3.1.6
Werkzeug 3.0.3 -> 3.1.6
```

После обновления `pip-audit` и Trivy не показывают известных уязвимостей в Python-зависимостях.

## Проверка исправлений

Команда полного запуска security-тестов:

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\Activate.ps1
python -m pytest tests -q
```

Ожидаемый результат после исправлений:

```text
40 passed
```

Дополнительные проверки:

```powershell
.\scripts\run_sast.ps1
.\scripts\run_sca.ps1
.\scripts\run_secrets.ps1
$env:ZAP_AUTH_USERNAME = "employee"
$env:ZAP_AUTH_PASSWORD = "<пароль тестового пользователя>"
.\scripts\run_dast_all.ps1
```

Ожидаемый результат после исправлений:

```text
SAST: 0 findings
SCA: 0 findings
Secrets: 0 findings
DAST: 0 fail/high/medium alerts, residual alerts are informational or low
```

После повторного DAST-сканирования ZAP больше не показывает SQL injection, XSS, path traversal, отсутствие CSP, отсутствие anti-clickjacking, отсутствие `X-Content-Type-Options`, debug error disclosure или утечки версии Werkzeug/Python через `Server`. Остаточные пункты относятся к информационным событиям сканера (`Authentication Request Identified`, `Session Management Response Identified`, `User Agent Fuzzer`, `Non-Storable Content`) и одному low-risk эвристическому предупреждению `Cookie Slack Detector`.

Отдельно можно запустить regression suite:

```powershell
.\scripts\run_security_regression_tests.ps1
```

## Вывод

В результате раздела 2.3 проект был переведен из состояния демонстрации найденных уязвимостей в состояние с реализованными защитными механизмами. Исправления не только внесены в исходный код, но и закреплены автоматическими тестами, которые можно запускать локально и в будущем CI/CD pipeline.
