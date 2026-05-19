# 3. SCA - анализ зависимостей

SCA применяется для проверки сторонних библиотек, которые используются приложением. В отличие от SAST, этот этап анализирует не собственный исходный код, а зависимости проекта и известные уязвимости в них.

В проекте используются два инструмента:

- pip-audit - основной инструмент для Python-зависимостей.
- Trivy - дополнительный сканер зависимостей и файловой структуры проекта.

`pip-audit` проверяет Python-пакеты по Python Packaging Advisory Database и другим источникам advisory-данных, а Trivy позволяет дополнительно проанализировать lock-файлы, requirements-файлы, контейнеры и файловую систему проекта.

## Установка pip-audit

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

## Установка Trivy

На Windows Trivy можно установить через `winget`:

```powershell
winget install AquaSecurity.Trivy
```

После установки проверьте доступность команды:

```powershell
trivy --version
```

Если Trivy не установлен, общий SCA-скрипт все равно выполнит `pip-audit`, а для Trivy создаст текстовый файл с инструкцией по установке.

## Запуск анализа

Единый запуск `pip-audit` и Trivy:

```powershell
.\scripts\run_sca.ps1
```

После выполнения отчеты сохраняются в директорию:

```text
reports\sca
```

Создаются файлы:

| Файл | Назначение |
| --- | --- |
| `reports\sca\pip-audit.json` | машинно-читаемый отчет pip-audit |
| `reports\sca\pip-audit.txt` | текстовый отчет pip-audit |
| `reports\sca\trivy.json` | машинно-читаемый отчет Trivy |
| `reports\sca\trivy.txt` | текстовый отчет Trivy |
| `reports\sca\summary.md` | краткая Markdown-сводка для вставки в работу |

## Отдельный запуск pip-audit

Проверка зависимостей из `requirements.txt`:

```powershell
python -m pip_audit -r requirements.txt --no-deps --disable-pip
```

Сохранение результата в JSON:

```powershell
python -m pip_audit -r requirements.txt --no-deps --disable-pip -f json -o reports\sca\pip-audit.json
```

Проверка установленного виртуального окружения:

```powershell
python -m pip_audit
```

## Отдельный запуск Trivy

Проверка файловой системы проекта:

```powershell
trivy fs --scanners vuln .
```

Сохранение результата в JSON:

```powershell
trivy fs --scanners vuln --format json --output reports\sca\trivy.json .
```

## Что проверяет pip-audit

| Объект анализа | Что выявляется |
| --- | --- |
| `requirements.txt` | известные уязвимости в указанных версиях Python-пакетов |
| установленное окружение | уязвимости в реально установленных пакетах |
| advisory database | CVE, GHSA и другие идентификаторы уязвимостей |
| исправленные версии | версии пакетов, в которых проблема устранена |

## Что проверяет Trivy

| Объект анализа | Что выявляется |
| --- | --- |
| requirements-файлы | уязвимые Python-зависимости |
| lock-файлы | уязвимые зафиксированные версии пакетов |
| контейнерные файлы | уязвимости образов и базовых слоев |
| файловая система проекта | известные уязвимые компоненты |

## Пример оформления результата

```text
На этапе SCA был выполнен анализ сторонних зависимостей приложения.
В качестве основного инструмента использовался pip-audit, который проверяет Python-зависимости по базе Python Packaging Advisory Database.
В качестве дополнительного инструмента использовался Trivy, позволяющий анализировать зависимости и файловую структуру проекта.

Результаты анализа были сохранены в reports/sca в форматах JSON, TXT и Markdown.
Полученные замечания были сопоставлены с используемыми версиями библиотек и доступными исправленными версиями.
```
