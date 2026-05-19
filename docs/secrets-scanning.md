# 4. Secrets scanning - поиск секретов

Secrets scanning применяется для поиска ключей, паролей, токенов и других чувствительных значений в исходном коде, конфигурационных файлах и служебных скриптах.

В проекте используются два инструмента:

- detect-secrets - основной инструмент для поиска потенциальных секретов и формирования baseline.
- Gitleaks - дополнительный независимый сканер, который хорошо подходит для проверки репозиториев и подготовки отчетов.

## Установка detect-secrets

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

## Установка Gitleaks

На Windows:

```powershell
winget install Gitleaks.Gitleaks
```

Проверка установки:

```powershell
gitleaks version
```

Если Gitleaks не установлен, общий скрипт все равно выполнит `detect-secrets`, а для Gitleaks создаст текстовый файл с инструкцией по установке.

## Запуск анализа

Единый запуск `detect-secrets` и Gitleaks:

```powershell
.\scripts\run_secrets.ps1
```

После выполнения отчеты сохраняются в директорию:

```text
reports\secrets
```

Создаются файлы:

| Файл | Назначение |
| --- | --- |
| `reports\secrets\detect-secrets.json` | JSON-результат detect-secrets |
| `reports\secrets\detect-secrets.baseline` | baseline detect-secrets |
| `reports\secrets\gitleaks.json` | JSON-отчет Gitleaks |
| `reports\secrets\gitleaks.sarif` | SARIF-отчет Gitleaks |
| `reports\secrets\gitleaks.txt` | служебная информация по запуску Gitleaks |
| `reports\secrets\summary.md` | краткая Markdown-сводка для вставки в работу |

## Отдельный запуск detect-secrets

```powershell
python -m detect_secrets scan --all-files --exclude-files "(\.venv|reports|uploads|__pycache__|corp_mail\.db|diplom.*\.zip)" app.py webmail templates static scripts docs
```

Сохранение baseline:

```powershell
python -m detect_secrets scan --all-files --exclude-files "(\.venv|reports|uploads|__pycache__|corp_mail\.db|diplom.*\.zip)" app.py webmail templates static scripts docs > reports\secrets\detect-secrets.baseline
```

## Отдельный запуск Gitleaks

```powershell
gitleaks detect --source . --config .gitleaks.toml --no-git
```

Сохранение JSON-отчета:

```powershell
gitleaks detect --source . --config .gitleaks.toml --no-git --report-format json --report-path reports\secrets\gitleaks.json --redact=80
```

Сохранение SARIF-отчета:

```powershell
gitleaks detect --source . --config .gitleaks.toml --no-git --report-format sarif --report-path reports\secrets\gitleaks.sarif --redact=80
```

## Что проверяет detect-secrets

| Объект анализа | Что выявляется |
| --- | --- |
| Python-файлы | пароли, токены, приватные ключи, подозрительные строки |
| HTML/CSS/скрипты | случайно вставленные ключи и токены |
| конфигурационные файлы | секреты в настройках инструментов |
| baseline | список найденных значений для дальнейшего аудита |

## Что проверяет Gitleaks

| Объект анализа | Что выявляется |
| --- | --- |
| рабочая директория | токены, ключи, credentials и секретные строки |
| история Git | секреты в коммитах, если запускать без `--no-git` |
| конфиги и скрипты | ключи и пароли в служебных файлах |
| SARIF-отчет | результат для импорта в GitHub/GitLab/SonarQube |

## Пример оформления результата

```text
На этапе secrets scanning был выполнен поиск секретов в исходном коде и конфигурационных файлах проекта.
В качестве основного инструмента использовался detect-secrets, дополнительно применялся Gitleaks.
detect-secrets сформировал JSON-отчет и baseline, а Gitleaks сформировал JSON и SARIF-отчеты.

Результаты анализа были сохранены в reports/secrets.
Найденные значения были классифицированы по типу правила, файлу и строке расположения.
```
