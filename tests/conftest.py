import os
import shutil
import tempfile

import pytest

from webmail import create_app


@pytest.fixture()
def app():
    db_fd, db_path = tempfile.mkstemp(prefix="corp_mail_test_", suffix=".db")
    os.close(db_fd)
    upload_root = tempfile.mkdtemp(prefix="corp_mail_uploads_")
    upload_dir = os.path.join(upload_root, "uploads")

    app = create_app()
    app.config.update(
        TESTING=True,
        DB_PATH=db_path,
        UPLOAD_TEST_ROOT=upload_root,
        UPLOAD_DIR=upload_dir,
        WTF_CSRF_ENABLED=False,
    )

    from webmail.db import init_db, seed_data

    init_db(db_path)
    seed_data(db_path)

    yield app

    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass
    shutil.rmtree(upload_root, ignore_errors=True)


@pytest.fixture()
def client(app):
    return app.test_client()
