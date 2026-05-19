# 7. Проверка API

API необходимо проверять отдельно, так как программные эндпоинты часто возвращают больше данных, чем HTML-интерфейс, и могут обходить ограничения пользовательского интерфейса.

Используемые инструменты:

- curl или Postman;
- OWASP ZAP;
- Semgrep;
- pytest.

## Что проверяется

| Проверка | Пример |
| --- | --- |
| Доступ к API без авторизации | запрос к `/api/v1/mail/1` без cookie |
| Доступ к чужим объектам | чтение письма другого пользователя по ID |
| SQL-инъекции в параметрах API | параметр `recipient` или `q` в поиске |
| Избыточные данные в ответе | поле `password`, `role`, `api_quota` в профиле |
| Раскрытие конфигурации | `/api/v1/config` |
| Отсутствие rate limit | многократные запросы к `/api/v1/token` |
| Небезопасные токены | base64-токен без криптографической подписи |
| CORS | разрешение запросов с любых источников |

## Запуск pytest API security tests

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
.\scripts\run_api_tests.ps1
```

Или напрямую:

```powershell
python -m pytest tests\test_api_security.py -vv
```

Отчеты сохраняются в:

```text
reports\api
```

Создаются файлы:

| Файл | Назначение |
| --- | --- |
| `reports\api\pytest-api.txt` | полный вывод pytest |
| `reports\api\summary.md` | краткая Markdown-сводка |

## Проверка через curl

### Доступ к конфигурации

```powershell
curl.exe -i http://127.0.0.1:5000/api/v1/config
```

### Получение токена

```powershell
curl.exe -i "http://127.0.0.1:5000/api/v1/token?user=employee"
```

### Чтение письма без авторизации

```powershell
curl.exe -i http://127.0.0.1:5000/api/v1/mail/1
```

### Поиск по почте

```powershell
curl.exe -i "http://127.0.0.1:5000/api/v1/mail/search?recipient=employee&q=report"
```

### Проверка SQL-инъекции в API

```powershell
curl.exe -i "http://127.0.0.1:5000/api/v1/mail/search?recipient=employee'%20OR%20'1'%3D'1&q=x"
```

### Проверка избыточных данных пользователя

```powershell
curl.exe -i http://127.0.0.1:5000/api/v1/users/employee
```

### Проверка mass assignment

```powershell
curl.exe -i -X PUT http://127.0.0.1:5000/api/v1/users/employee -H "Content-Type: application/json" -d "{\"role\":\"admin\",\"api_quota\":99999}"
```

### Проверка rate limit

```powershell
1..20 | ForEach-Object { curl.exe -s -o NUL -w "%{http_code}`n" "http://127.0.0.1:5000/api/v1/token?user=employee" }
```

## Проверка через OWASP ZAP

ZAP проверяет API в рамках DAST-сканов:

```powershell
.\scripts\run_zap_baseline.ps1
.\scripts\run_zap_full.ps1
.\scripts\run_zap_auth.ps1
```

Для API полезно отдельно смотреть:

- найденные параметры;
- SQL injection findings;
- missing security headers;
- CORS findings;
- ответы, доступные без авторизации.

## Проверка через Semgrep

API-код дополнительно анализируется SAST-правилами:

```powershell
.\scripts\run_sast.ps1
```

Особенно важные файлы:

```text
webmail\routes\api.py
webmail\db.py
```

Semgrep помогает найти:

- динамическую сборку SQL;
- раскрытие чувствительной конфигурации;
- небезопасную работу с токенами;
- небезопасный CORS.

## Пример оформления результата

```text
На этапе проверки API были выполнены ручные и автоматизированные проверки программных эндпоинтов сервиса.
Через curl проверялся доступ к API без авторизации, раскрытие конфигурации, чтение писем по ID, SQL-инъекции в параметрах поиска и массовое изменение пользовательских полей.
Через pytest были автоматизированы проверки IDOR, избыточных данных в ответах, небезопасного формата токена, отсутствия rate limit и permissive CORS.
Дополнительно API был охвачен SAST-анализом Semgrep и DAST-анализом OWASP ZAP.
```
