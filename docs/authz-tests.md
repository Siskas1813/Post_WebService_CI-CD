# 6. Проверка аутентификации и авторизации

Этот этап относится к ручным и полуавтоматическим проверкам. Его цель - проверить не отдельные зависимости и не исходный код, а фактическое поведение механизмов входа, сессий, ролей и доступа к объектам.

Используемые способы проверки:

- вручную через браузер;
- через curl или Postman;
- через OWASP ZAP;
- через pytest security tests.

## Что проверяется

| Проверка | Пример |
| --- | --- |
| Доступ без авторизации | открыть `/dashboard` без входа |
| IDOR | пользователь A пытается открыть письмо пользователя B |
| Проверка ролей | обычный пользователь пытается зайти в `/admin` |
| Сессии | `logout` реально завершает сессию |
| Cookie flags | проверка `HttpOnly`, `Secure`, `SameSite` |
| Brute-force защита | проверка лимита попыток входа |

## Установка зависимостей для тестов

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Запуск pytest security tests

```powershell
.\scripts\run_authz_tests.ps1
```

Или напрямую:

```powershell
python -m pytest tests\test_authz_security.py -vv
```

Отчеты сохраняются в:

```text
reports\authz
```

Создаются файлы:

| Файл | Назначение |
| --- | --- |
| `reports\authz\pytest-authz.txt` | полный вывод pytest |
| `reports\authz\summary.md` | краткая Markdown-сводка |

## Ручная проверка через браузер

### Доступ без авторизации

1. Открыть браузер в режиме без сохраненной сессии.
2. Перейти на:

```text
http://127.0.0.1:5000/dashboard
```

Ожидаемый результат: перенаправление на страницу входа.

### Проверка ролей

1. Войти как `employee / employee123`.
2. Открыть:

```text
http://127.0.0.1:5000/admin/users
http://127.0.0.1:5000/admin/sql
```

Ожидаемый результат: обычный пользователь не должен получить полноценный доступ к административным функциям.

### Logout

1. Войти в приложение.
2. Нажать `Выйти`.
3. Попробовать снова открыть `/dashboard`.

Ожидаемый результат: пользователь снова отправляется на страницу входа.

## Проверка через curl

### Доступ без авторизации

```powershell
curl.exe -i http://127.0.0.1:5000/dashboard
```

### Авторизация и cookie

```powershell
curl.exe -i -c cookies.txt -X POST http://127.0.0.1:5000/login -d "username=employee&password=employee123&next=/dashboard"
```

### Доступ с cookie

```powershell
curl.exe -i -b cookies.txt http://127.0.0.1:5000/dashboard
```

### Logout

```powershell
curl.exe -i -b cookies.txt -c cookies.txt http://127.0.0.1:5000/logout
curl.exe -i -b cookies.txt http://127.0.0.1:5000/dashboard
```

### Проверка IDOR

```powershell
curl.exe -i -b cookies.txt http://127.0.0.1:5000/mail/1
curl.exe -i -b cookies.txt http://127.0.0.1:5000/mail/2
curl.exe -i -b cookies.txt http://127.0.0.1:5000/api/v1/mail/1
```

## Проверка через OWASP ZAP

Для DAST-проверки авторизованных областей используется:

```powershell
$env:ZAP_AUTH_USERNAME = "employee"
$env:ZAP_AUTH_PASSWORD = "<пароль тестового пользователя>"
.\scripts\run_zap_auth.ps1
```

ZAP выполняет вход под учетной записью:

```text
employee / employee123
```

После проверки формируются:

```text
reports\dast\zap-auth.html
reports\dast\zap-auth.json
reports\dast\zap-auth.md
```

## Что фиксировать в дипломе

```text
На этапе проверки аутентификации и авторизации были выполнены ручные и полуавтоматические проверки.
Через браузер и curl проверялся доступ к защищенным страницам без входа, завершение сессии после logout и доступ к административным разделам.
Через pytest были автоматизированы проверки ролей, cookie flags, IDOR, API-доступа без авторизации, brute-force поведения и SQL injection в форме входа.
Через OWASP ZAP был выполнен авторизованный scan под учетной записью employee.
```
