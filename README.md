# teessyt

## Corp Mail Enterprise

Корпоративный веб-почтовый сервис, имитирующий внутренний почтовый продукт компании: рабочие папки, отправку писем, поиск, контакты, правила обработки, профиль сотрудника, центр вложений, административные панели и API.

## Что добавлено

- современный корпоративный интерфейс: боковая навигация, KPI, статусы, классификация писем, бейджи, адаптивная верстка;
- расширенная почтовая модель: `inbox`, `sent`, `drafts`, `archive`, `starred`, `priority`, `classification`, `label`, `thread_id`;
- рабочие разделы: контакты, правила маршрутизации, профиль пользователя, центр вложений;
- админ-разделы: пользователи, аудит, интеграции, диагностика;
- API: поиск писем, просмотр письма, профиль пользователя, токены, журнал, конфигурация;

## Архитектура

- `app.py` - точка входа Flask;
- `webmail/__init__.py` - фабрика приложения и конфигурация;
- `webmail/db.py` - схема SQLite, миграции колонок и сидирование данных;
- `webmail/services/mail_service.py` - сервисный слой почты, контактов, правил и профиля;
- `webmail/routes/auth.py` - вход, выход и сессии;
- `webmail/routes/mailbox.py` - пользовательские страницы почты;
- `webmail/routes/admin.py` - админские панели;
- `webmail/routes/api.py` - API-эндпоинты;
- `templates/` - HTML-шаблоны;
- `static/app.css` - оформление приложения.

## Запуск

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

После старта: `http://127.0.0.1:5000`

Демо-аккаунты:

- `employee / employee123`
- `manager / manager123`
- `admin / admin123`

## CI/CD через GitHub

Автоматизированные security-контроли вынесены в GitHub Actions:

```text
.github/workflows/security-ci.yml
```

Workflow запускает pytest security regression tests, Semgrep, Bandit, pip-audit, Trivy, detect-secrets, Gitleaks и OWASP ZAP. По итогам формируется общий отчет `reports/security-ci-summary.md`, HTML-dashboard `reports/security-dashboard.html` и artifact `security-reports`.

Ручной запуск в GitHub:

```text
Actions -> Security CI/CD -> Run workflow
```

Для публикации красивого HTML-отчета включите GitHub Pages:

```text
Settings -> Pages -> Source -> GitHub Actions
```

Подробная инструкция находится в `docs/ci-cd-security.md`.

## Проверки безопасности

Установка инструментов:

```bash
pip install -r requirements-dev.txt
```

SAST:

```powershell
.\scripts\run_sast.ps1
```

SCA:

```powershell
.\scripts\run_sca.ps1
```

Secrets scanning:

```powershell
.\scripts\run_secrets.ps1
```

DAST:

```powershell
.\scripts\start_app.ps1
.\scripts\run_zap_baseline.ps1
.\scripts\run_zap_full.ps1
.\scripts\run_zap_auth.ps1
```

Authentication and authorization tests:

```powershell
.\scripts\run_authz_tests.ps1
```

API security tests:

```powershell
.\scripts\run_api_tests.ps1
```
