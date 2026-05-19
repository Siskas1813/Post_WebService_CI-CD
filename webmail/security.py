import hmac
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from flask import current_app, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


ALLOWED_ATTACHMENT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".docx", ".xlsx"}
FORBIDDEN_ATTACHMENT_EXTENSIONS = {".exe", ".php", ".pkl", ".pickle", ".js", ".bat", ".cmd", ".ps1", ".sh"}
ALLOWED_ATTACHMENT_MIME = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".txt": {"text/plain"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
}


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256:100000")


def verify_password(stored_password: str, candidate: str) -> bool:
    if stored_password.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored_password, candidate)
    return hmac.compare_digest(stored_password, candidate)


def is_safe_redirect_target(target: str) -> bool:
    if not target:
        return False
    ref_url = urlsplit(request.host_url)
    test_url = urlsplit(target)
    return not test_url.netloc or test_url.netloc == ref_url.netloc


def safe_redirect_target(target: str, fallback: str = "/dashboard") -> str:
    return target if is_safe_redirect_target(target) else fallback


def current_usernames() -> tuple[str, str]:
    username = session.get("username", "")
    return username, f"{username}@corp.local"


def require_api_user():
    if "username" not in session:
        return None, ({"error": "authentication required"}, 401)
    return session["username"], None


def normalize_attachment(upload):
    original_name = secure_filename(upload.filename or "")
    if not original_name:
        return None, "Не указано имя файла"

    suffixes = [suffix.lower() for suffix in Path(original_name).suffixes]
    final_suffix = suffixes[-1] if suffixes else ""

    if not final_suffix or final_suffix not in ALLOWED_ATTACHMENT_EXTENSIONS:
        return None, "Тип файла не разрешен"
    if any(suffix in FORBIDDEN_ATTACHMENT_EXTENSIONS for suffix in suffixes):
        return None, "Тип файла не разрешен"

    content_type = upload.content_type or "application/octet-stream"
    if content_type not in ALLOWED_ATTACHMENT_MIME.get(final_suffix, set()):
        return None, "MIME-тип файла не разрешен"

    storage_name = f"{uuid4().hex}{final_suffix}"
    return (original_name, storage_name, content_type), None


def save_attachment_file(upload, storage_name: str) -> tuple[str, int]:
    upload_dir = Path(current_app.config["UPLOAD_DIR"]).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = (upload_dir / storage_name).resolve()

    if upload_dir not in destination.parents:
        raise ValueError("Некорректный путь файла")

    upload.save(destination)
    return storage_name, os.path.getsize(destination)


def make_api_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    session.setdefault("api_tokens", {})
    session["api_tokens"][token] = username
    return token
