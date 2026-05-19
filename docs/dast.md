# 5. DAST - динамический анализ веб-приложения

DAST применяется к уже запущенному веб-приложению и проверяет его поведение через HTTP-запросы. В отличие от SAST, анализатор не читает исходный код, а взаимодействует с приложением как внешний клиент.

В проекте используются три режима OWASP ZAP:

- OWASP ZAP Baseline Scan - быстрая пассивная проверка.
- OWASP ZAP Full Scan - более глубокая проверка с активным сканированием.
- Authenticated ZAP Scan - проверка приложения после входа в систему.

## Подготовка

Для запуска используется Docker-образ OWASP ZAP:

```powershell
docker --version
```

Если Docker установлен, приложение можно запустить командой:

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\activate
.\scripts\start_app.ps1
```

После запуска приложение доступно на хосте:

```text
http://127.0.0.1:5000
```

Для контейнера ZAP используется адрес:

```text
http://host.docker.internal:5000
```

## OWASP ZAP Baseline Scan

Baseline Scan выполняет spider и пассивный анализ. Он подходит для быстрой проверки HTTP-заголовков, cookies, форм, базовых проблем конфигурации и доступных страниц.

Запуск:

```powershell
.\scripts\run_zap_baseline.ps1
```

Создаваемые отчеты:

```text
reports\dast\zap-baseline.html
reports\dast\zap-baseline.json
reports\dast\zap-baseline.md
```

## OWASP ZAP Full Scan

Full Scan выполняет более глубокое сканирование и активные проверки. Он отправляет тестовые запросы к приложению и может занимать больше времени.

Запуск:

```powershell
.\scripts\run_zap_full.ps1
```

Создаваемые отчеты:

```text
reports\dast\zap-full.html
reports\dast\zap-full.json
reports\dast\zap-full.md
```

## Авторизованный ZAP scan

Авторизованный режим нужен для проверки страниц, доступных только после входа пользователя. Для этого используется ZAP Automation Framework и файл плана, который генерируется скриптом `run_zap_auth.ps1`.
В плане используется обычный spider, passive scan и active scan. AJAX spider не включен, так как приложение отдает серверные HTML-страницы и не требует отдельного обхода SPA-интерфейса.

Используемая учетная запись:

```text
employee / employee123
```

Запуск:

```powershell
$env:ZAP_AUTH_USERNAME = "employee"
$env:ZAP_AUTH_PASSWORD = "<пароль тестового пользователя>"
.\scripts\run_zap_auth.ps1
```

Создаваемые отчеты:

```text
reports\dast\zap-auth.html
reports\dast\zap-auth.json
reports\dast\zap-auth.md
reports\dast\zap-auth-plan.yaml
```

После успешного запуска ZAP дополнительно формируется краткая сводка:

```text
reports\dast\summary.md
```

## Полный запуск всех DAST-проверок

```powershell
.\scripts\run_dast_all.ps1
```

Скрипт последовательно:

1. Запускает Flask-приложение.
2. Выполняет ZAP Baseline Scan.
3. Выполняет ZAP Full Scan.
4. Выполняет авторизованный ZAP scan.

## Что проверяет ZAP

| Режим | Что проверяется |
| --- | --- |
| Baseline Scan | доступные страницы, HTTP-заголовки, cookies, пассивные security findings |
| Full Scan | активные проверки, инъекции, небезопасные параметры, ошибки конфигурации |
| Authenticated Scan | страницы и функции, доступные после входа пользователя |

## Пример оформления результата

```text
На этапе DAST веб-приложение было запущено локально, после чего к нему были применены проверки OWASP ZAP.
Baseline Scan использовался для быстрой пассивной проверки доступных страниц.
Full Scan применялся для более глубокого анализа поведения приложения.
Отдельно был выполнен авторизованный scan, в котором ZAP входил в приложение под учетной записью employee.

Результаты анализа были сохранены в reports/dast в форматах HTML, JSON и Markdown.
```
