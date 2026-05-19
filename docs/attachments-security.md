# 8. Проверка загрузки и скачивания вложений

## Цель проверки

Для почтового сервиса вложения являются отдельной поверхностью атаки, потому что пользователь передает приложению имя файла, содержимое файла, размер, расширение и MIME-тип. Также сервис должен безопасно отдавать файл обратно и проверять, что пользователь имеет право скачать конкретное вложение.

## Что проверяем

| Проверка | Пример атаки | Где проверяется |
| --- | --- | --- |
| Запрещенные расширения | `dropper.exe`, `shell.php`, `object.pkl`, `script.js` | `tests/test_attachment_security.py` |
| Обход расширений | `invoice.jpg.php` | `tests/test_attachment_security.py` |
| Directory Traversal при загрузке | `../outside.txt` | `tests/test_attachment_security.py` |
| Перезапись файлов | повторная загрузка `report.txt` | `tests/test_attachment_security.py` |
| Ограничение размера | файл 2 МБ без отказа | `tests/test_attachment_security.py` |
| Content-Type spoofing | `notice.txt` с HTML/JS и `text/html` | `tests/test_attachment_security.py` |
| Directory Traversal при скачивании | `/download?path=C:\...\confidential.txt` | `tests/test_attachment_security.py` |
| IDOR по вложениям | пользователь скачивает файл другого пользователя | `tests/test_attachment_security.py` |

## Инструменты

- Ручные тесты через браузер: загрузка разных файлов в разделе "Вложения".
- `curl` или Postman: повторение загрузки и скачивания без браузера.
- OWASP ZAP: динамическая проверка форм и параметра `path`.
- Semgrep: статический поиск небезопасной обработки файлов.
- `pytest`: воспроизводимые security-тесты для отчета.

## Как установить

Зависимости уже входят в `requirements-dev.txt`. Если окружение еще не подготовлено:

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## Как запустить проверки

```powershell
cd C:\PRogramki\Diplom
.\.venv\Scripts\Activate.ps1
.\scripts\run_attachment_tests.ps1
```

После запуска будут созданы отчеты:

- `reports\attachments\pytest-attachments.txt`
- `reports\attachments\summary.md`

## Реализация тестов

Основной файл:

```text
tests/test_attachment_security.py
```

Скрипт запуска:

```text
scripts/run_attachment_tests.ps1
```

## Найденные слабые места в коде

| Проблема | Файл | Причина |
| --- | --- | --- |
| Нет allowlist расширений | `webmail/routes/mailbox.py` | приложение сохраняет файл с исходным расширением |
| Обход двойным расширением | `webmail/routes/mailbox.py` | имя файла не нормализуется и не проверяется |
| Directory Traversal при загрузке | `webmail/routes/mailbox.py` | `os.path.join(UPLOAD_DIR, upload.filename)` использует имя от пользователя |
| Перезапись файлов | `webmail/routes/mailbox.py` | файл сохраняется под исходным именем без уникального имени |
| Нет лимита размера | `webmail/routes/mailbox.py` | нет `MAX_CONTENT_LENGTH` и проверки размера |
| Content-Type spoofing | `webmail/routes/mailbox.py` | `upload.content_type` сохраняется без проверки содержимого |
| Небезопасное чтение pickle | `webmail/routes/mailbox.py` | `.pkl` файл десериализуется через `pickle.load` |
| Directory Traversal при скачивании | `webmail/routes/mailbox.py` | `/download` принимает произвольный параметр `path` |
| IDOR по файлам | `webmail/routes/mailbox.py` | скачивание не проверяет владельца вложения |

## Как исправить

Рекомендуемая схема защиты:

1. Использовать `secure_filename()` для очистки имени файла.
2. Хранить файл под случайным серверным именем, например через `uuid4`.
3. Разрешить только безопасные расширения: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.txt`, `.docx`, `.xlsx`.
4. Запретить исполняемые и опасные форматы: `.exe`, `.php`, `.pkl`, `.js`, `.bat`, `.cmd`, `.ps1`.
5. Включить лимит размера через `app.config["MAX_CONTENT_LENGTH"]`.
6. Проверять фактический MIME-тип и не доверять только `Content-Type` из запроса.
7. Не использовать `pickle.load` для файлов от пользователя.
8. Скачивать вложение по `attachment_id`, а не по произвольному пути.
9. Перед скачиванием проверять, что текущий пользователь является владельцем письма или имеет нужную роль.
10. Отдавать файлы через `send_from_directory()` или через безопасное хранилище.

Пример безопасного направления исправления:

```python
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import abort, send_from_directory, session

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".docx", ".xlsx"}


def normalize_upload_name(filename):
    clean_name = secure_filename(filename)
    suffix = Path(clean_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        abort(400)
    return f"{uuid4().hex}{suffix}", clean_name


@mailbox_bp.route("/download/<int:attachment_id>")
def download_attachment(attachment_id):
    row = service.get_attachment_for_user(attachment_id, session["username"])
    if not row:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_DIR"], row["storage_name"], as_attachment=True, download_name=row["filename"])
```

Для дипломной работы текущие тесты фиксируют исходное состояние сервиса и показывают, какие проверки должны стать зелеными после внедрения защитных механизмов.
