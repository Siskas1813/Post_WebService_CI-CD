# 10. Тесты безопасности через pytest

## Цель проверки

Security regression tests фиксируют ожидаемое безопасное поведение приложения. Они нужны не только для поиска уязвимостей, но и для контроля исправлений: после внедрения защиты тесты должны переходить в состояние `PASS` и не позволять вернуть старую ошибку обратно в код.

Такой блок хорошо дополняет SAST, SCA и DAST:

- SAST показывает подозрительные места в исходном коде;
- SCA показывает уязвимые зависимости;
- DAST проверяет запущенное приложение как внешний сканер;
- pytest regression tests проверяют конкретные бизнес-правила безопасности.

## Что проверяем

| Проверка | Ожидаемое безопасное поведение | Тест |
| --- | --- | --- |
| `/dashboard` без сессии | редирект на login | `test_dashboard_without_session_redirects_to_login` |
| Обычный пользователь и `/admin` | пользователь не видит админку | `test_regular_user_cannot_open_admin_area` |
| SQL-инъекция в login | вход не выполняется | `test_sql_injection_in_login_is_rejected` |
| Загрузка `.pkl` | файл отклоняется | `test_pkl_upload_is_forbidden` |
| Скачивание `../../app.py` | доступ запрещен | `test_download_path_traversal_is_forbidden` |
| API без авторизации | ответ `401` | `test_api_without_authorization_returns_401` |
| API чужого письма | ответ `403` или `404` | `test_api_other_users_mail_returns_403_or_404` |

## Как установить

Если окружение еще не подготовлено:

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## Как запустить

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\Activate.ps1
.\scripts\run_security_regression_tests.ps1
```

Отчеты будут сохранены:

- `reports\security-regression\pytest-security-regression.txt`
- `reports\security-regression\summary.md`

## Реализация

Основной файл:

```text
tests/test_security_regression.py
```

Скрипт запуска:

```text
scripts/run_security_regression_tests.ps1
```

## Интерпретация результата

После выполнения раздела 2.3 эти тесты стали обычными regression-тестами без `xfail`.

| Статус | Значение |
| --- | --- |
| `PASSED` | исправление работает |
| `FAILED` | защита сломалась или была удалена |

Такой подход позволяет показать в дипломе не только факт нахождения уязвимостей, но и контроль того, что исправления не будут потеряны при дальнейшей разработке.

## Какие исправления закрепляют тесты

| Тест | Что закреплено |
| --- | --- |
| `test_sql_injection_in_login_is_rejected` | login использует параметризованный запрос и проверку хеша пароля |
| `test_pkl_upload_is_forbidden` | вложения проходят allowlist расширений и MIME-типов |
| `test_download_path_traversal_is_forbidden` | скачивание больше не принимает произвольный путь |
| `test_api_without_authorization_returns_401` | API требует авторизованную сессию |
| `test_api_other_users_mail_returns_403_or_404` | API проверяет владельца письма |

## Пример запуска без скрипта

```powershell
python -m pytest tests\test_security_regression.py -vv
```
