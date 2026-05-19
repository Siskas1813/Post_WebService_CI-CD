# 2. SAST - статический анализ исходного кода

SAST применяется до запуска приложения и проверяет исходный код на типовые ошибки безопасности. Для проекта используются два инструмента:

- Semgrep - основной анализатор с готовыми и проектными правилами.
- Bandit - дополнительный анализатор Python-кода.

## Установка

Команды выполняются из корня проекта:

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
```

Если виртуальное окружение еще не создано:

```powershell
cd C:\PRogramki\Diplom
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Запуск анализа

Единый запуск Semgrep и Bandit:

```powershell
.\scripts\run_sast.ps1
```

После выполнения отчеты сохраняются в директорию:

```text
reports\sast
```

Создаются файлы:

| Файл | Назначение |
| --- | --- |
| `reports\sast\semgrep.json` | машинно-читаемый отчет Semgrep |
| `reports\sast\semgrep.sarif` | отчет Semgrep для импорта в GitHub/GitLab/SonarQube |
| `reports\sast\bandit.json` | машинно-читаемый отчет Bandit |
| `reports\sast\bandit.txt` | текстовый отчет Bandit |
| `reports\sast\summary.md` | краткая Markdown-сводка для вставки в работу |

## Отдельный запуск Semgrep

```powershell
semgrep --config auto --config .semgrep.yml app.py webmail templates
```

Сохранение результата в JSON:

```powershell
semgrep --config auto --config .semgrep.yml --json --output reports\sast\semgrep.json app.py webmail templates
```

## Отдельный запуск Bandit

```powershell
python -m bandit -c bandit.yml -r app.py webmail
```

Сохранение результата в JSON:

```powershell
python -m bandit -c bandit.yml -r app.py webmail -f json -o reports\sast\bandit.json
```

## Что проверяет Semgrep

В проект добавлен файл `.semgrep.yml`. Он содержит правила для поиска:

| Правило | Что выявляет |
| --- | --- |
| `flask-debug-enabled` | запуск Flask с `debug=True` |
| `flask-hardcoded-secret-key` | ключ Flask, записанный прямо в коде |
| `flask-hardcoded-sensitive-config` | чувствительные параметры конфигурации в исходниках |
| `sqlite-fstring-query` | SQL-запросы, собранные через f-string |
| `raw-sql-helper-execution` | выполнение SQL-строки напрямую |
| `unsafe-pickle-load` | использование `pickle.load` |
| `send-file-user-controlled-path` | передача пользовательского пути в `send_file` |
| `permissive-cors` | разрешение CORS для всех источников |
| `jinja-safe-filter` | отключение HTML-экранирования через `\|safe` |

## Что проверяет Bandit

Bandit анализирует Python-файлы и ищет типовые проблемы:

| Категория | Примеры |
| --- | --- |
| Небезопасная десериализация | `pickle`, `marshal` |
| Жестко заданные секреты | пароли, ключи, токены |
| Небезопасные вызовы ОС | `subprocess`, shell-команды |
| Небезопасные сетевые настройки | отключение TLS-проверок |
| SQL-инъекции | динамическая сборка SQL-запросов |
| Debug-настройки | запуск приложения в режиме отладки |

## Пример оформления результата

Для дипломной работы результат SAST можно оформить так:

```text
На этапе статического анализа исходного кода были использованы Semgrep и Bandit.
Semgrep применял набор стандартных правил и дополнительный проектный набор `.semgrep.yml`.
Bandit был использован для анализа Python-кода приложения.

Результаты анализа сохранены в директорию `reports/sast`.
Выявленные замечания были классифицированы по уровню критичности, типу ошибки и месту расположения в исходном коде.
```
