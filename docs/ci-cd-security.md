# Внедрение автоматизированных контролей безопасности в CI/CD-конвейер

## Назначение

В проект добавлен GitHub Actions workflow:

```text
.github/workflows/security-ci.yml
```

Он запускает автоматизированные проверки безопасности при `push`, `pull_request` и ручном запуске через `workflow_dispatch`. Основной сценарий использования - проверять проект через GitHub, без ручного запуска инструментов на локальной машине.

## Что запускается в GitHub Actions

| Уровень контроля | Инструменты | Реализация в CI/CD |
| --- | --- | --- |
| Статический анализ исходного кода | Semgrep | `scripts/ci_run_sast.sh` |
| Анализ Python-кода | Bandit | `scripts/ci_run_sast.sh` |
| Анализ зависимостей | pip-audit, Trivy | `scripts/ci_run_sca.sh` |
| Поиск секретов | detect-secrets, Gitleaks | `scripts/ci_run_secrets.sh` |
| Динамический анализ | OWASP ZAP Baseline, Full, Authenticated | `scripts/ci_run_dast.sh` |
| Проверка API | pytest | `python -m pytest tests -q` |
| Проверка аутентификации и авторизации | pytest | `python -m pytest tests -q` |
| Проверка вложений | pytest | `python -m pytest tests -q` |
| Проверка конфигурации и HTTP-заголовков | pytest, ZAP | `python -m pytest tests -q`, `scripts/ci_run_dast.sh` |
| Регрессионные security-тесты | pytest | `python -m pytest tests -q` |

## Security gate

После формирования отчетов запускается контрольный шаг:

```text
scripts/ci_security_gate.py
```

Он останавливает pipeline, если:

- Semgrep или Bandit нашли SAST finding;
- pip-audit или Trivy нашли известную уязвимость зависимости;
- detect-secrets или Gitleaks нашли секрет;
- OWASP ZAP нашел `Medium` или `High` risk alert.

Информационные и low-risk DAST-предупреждения сохраняются в отчете, но не блокируют pipeline. Это удобно для дипломной работы: отчет остается подробным, но сборка падает только на действительно значимых проблемах.

## Красивый отчет

Workflow формирует единый HTML-dashboard:

```text
reports/security-dashboard.html
```

В нем есть:

- общая оценка состояния проверок;
- карточки SAST, SCA, Secrets, DAST и pytest;
- распределение ZAP-находок по уровню риска;
- таблица всех контролей;
- ссылки на исходные отчеты Semgrep, Bandit, pip-audit, Trivy, Gitleaks и OWASP ZAP.

Этот dashboard публикуется двумя способами:

- как artifact `security-reports` внутри каждого запуска GitHub Actions;
- как GitHub Pages dashboard после запусков на `main` или `master`, если GitHub Pages включен в настройках репозитория.

## Как запустить самому через GitHub

1. Загрузить проект в GitHub-репозиторий.
2. Открыть `Settings -> Secrets and variables -> Actions`.
3. Добавить repository secret:

```text
ZAP_AUTH_PASSWORD
```

Значение должно соответствовать паролю тестового пользователя для авторизованного ZAP-сканирования. Для текущих демонстрационных данных это пароль пользователя `employee`.

4. Открыть `Settings -> Pages`.
5. В поле `Source` выбрать `GitHub Actions`.
6. Перейти в `Actions`.
7. Выбрать workflow `Security CI/CD`.
8. Нажать `Run workflow`.
9. Выбрать ветку и подтвердить запуск.

После этого GitHub сам установит зависимости, запустит pytest, SAST, SCA, secrets scanning и DAST, соберет отчеты и выполнит security gate.

## Где смотреть результат

После завершения запуска:

- `Actions -> Security CI/CD -> выбранный run -> Summary` - краткий Markdown-отчет прямо на странице запуска;
- `Artifacts -> security-reports` - полный архив отчетов;
- `security-reports/reports/security-dashboard.html` - современный HTML-dashboard;
- `Security -> Code scanning alerts` - SARIF-находки Semgrep;
- `Deployments -> github-pages` или ссылка в job `Publish Security Dashboard` - опубликованная HTML-страница отчета.

Успешный результат для защищенной версии проекта:

```text
pytest: все тесты passed
SAST: 0 blocking findings
SCA: 0 blocking findings
Secrets: 0 blocking findings
DAST: 0 Medium/High findings
Security gate: passed
```

## Артефакты

В artifact `security-reports` сохраняется папка:

```text
reports/
```

Основные файлы:

- `reports/security-ci-summary.md`;
- `reports/security-dashboard.html`;
- `reports/pytest/security-tests.txt`;
- `reports/sast/summary.md`;
- `reports/sast/semgrep.sarif`;
- `reports/sca/summary.md`;
- `reports/secrets/summary.md`;
- `reports/dast/summary.md`;
- `reports/dast/zap-baseline.html`;
- `reports/dast/zap-full.html`;
- `reports/dast/zap-auth.html`.

## Значение для диплома

В результате проверки безопасности встроены в CI/CD-конвейер. Каждое изменение проекта автоматически проходит статический анализ, анализ зависимостей, поиск секретов, динамическое сканирование, API/security regression tests и итоговый security gate. Это показывает не только разовое устранение уязвимостей, но и механизм предотвращения их повторного появления.
