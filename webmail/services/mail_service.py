from datetime import datetime, UTC

from webmail.db import get_conn


MAIL_FOLDERS = {"inbox", "sent", "drafts", "archive", "starred"}
MAILBOX_COLUMNS = "id, sender, recipient, subject, status, created_at, priority, classification, label, is_read, starred"
ACCESS_CLAUSE = "(recipient IN (?, ?) OR sender IN (?, ?) OR cc = ? OR cc LIKE ? OR cc LIKE ?)"


class MailService:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @staticmethod
    def _user_mail(username: str) -> str:
        return f"{username}@corp.local"

    @staticmethod
    def _access_params(username: str) -> tuple:
        user_mail = f"{username}@corp.local"
        return (username, user_mail, username, user_mail, username, f"%,{username}", f"%{username},%")

    def mailbox_stats(self, username: str):
        conn = get_conn(self.db_path)
        user_mail = self._user_mail(username)
        stats = {}
        for folder in ["inbox", "sent", "drafts", "archive"]:
            if folder == "sent":
                stats[folder] = conn.execute(
                    "SELECT COUNT(*) FROM mails WHERE sender IN (?, ?) AND status = 'sent'",
                    (username, user_mail),
                ).fetchone()[0]
            else:
                stats[folder] = conn.execute(
                    "SELECT COUNT(*) FROM mails WHERE recipient IN (?, ?) AND status = ?",
                    (username, user_mail, folder),
                ).fetchone()[0]
        stats["unread"] = conn.execute(
            "SELECT COUNT(*) FROM mails WHERE recipient IN (?, ?) AND is_read = 0",
            (username, user_mail),
        ).fetchone()[0]
        stats["starred"] = conn.execute(
            "SELECT COUNT(*) FROM mails WHERE recipient IN (?, ?) AND starred = 1",
            (username, user_mail),
        ).fetchone()[0]
        conn.close()
        return stats

    def list_mailbox(self, username: str, folder: str = "inbox"):
        folder = folder if folder in MAIL_FOLDERS else "inbox"
        conn = get_conn(self.db_path)
        user_mail = self._user_mail(username)
        if folder == "sent":
            rows = conn.execute(
                """
                SELECT id, sender, recipient, subject, status, created_at, priority, classification, label, is_read, starred
                FROM mails
                WHERE sender IN (?, ?) AND status = 'sent'
                ORDER BY created_at DESC
                """,
                (username, user_mail),
            ).fetchall()
        elif folder == "starred":
            rows = conn.execute(
                """
                SELECT id, sender, recipient, subject, status, created_at, priority, classification, label, is_read, starred
                FROM mails
                WHERE recipient IN (?, ?) AND starred = 1
                ORDER BY created_at DESC
                """,
                (username, user_mail),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, sender, recipient, subject, status, created_at, priority, classification, label, is_read, starred
                FROM mails
                WHERE recipient IN (?, ?) AND status = ?
                ORDER BY created_at DESC
                """,
                (username, user_mail, folder),
            ).fetchall()
        conn.close()
        return rows

    def search(self, username: str, q: str):
        conn = get_conn(self.db_path)
        user_mail = self._user_mail(username)
        pattern = f"%{q}%"
        rows = conn.execute(
            """
            SELECT id, sender, recipient, subject, body, created_at, priority, classification, label
            FROM mails
            WHERE (recipient IN (?, ?) OR sender IN (?, ?))
              AND (subject LIKE ? OR body LIKE ? OR sender LIKE ?)
            ORDER BY created_at DESC
            """,
            (username, user_mail, username, user_mail, pattern, pattern, pattern),
        ).fetchall()
        conn.close()
        return rows

    def get_mail(self, mail_id: str, username: str, role: str = "user"):
        conn = get_conn(self.db_path)
        params = (mail_id,)
        if role == "admin":
            row = conn.execute("SELECT * FROM mails WHERE id = ?", params).fetchone()
        else:
            row = conn.execute(
                """
                SELECT *
                FROM mails
                WHERE id = ?
                  AND (recipient IN (?, ?) OR sender IN (?, ?) OR cc = ? OR cc LIKE ? OR cc LIKE ?)
                """,
                params + self._access_params(username),
            ).fetchone()

        attachments = []
        if row:
            attachments = conn.execute("SELECT * FROM attachments WHERE mail_id = ?", (mail_id,)).fetchall()
            conn.execute("UPDATE mails SET is_read = 1 WHERE id = ?", (mail_id,))
            conn.commit()
        conn.close()
        return row, attachments

    def compose(self, sender: str, recipient: str, cc: str, subject: str, body: str, priority: str, classification: str, label: str):
        conn = get_conn(self.db_path)
        created_at = datetime.now(UTC).isoformat(timespec="seconds")
        thread_id = f"thread-{abs(hash(subject + recipient)) % 10000}"
        values = (sender, recipient, cc, subject, body, created_at, priority, classification, label, thread_id)
        conn.execute(
            """
            INSERT INTO mails(sender, recipient, cc, subject, body, status, created_at, priority, classification, label, is_read, starred, thread_id)
            VALUES (?, ?, ?, ?, ?, 'inbox', ?, ?, ?, ?, 0, 0, ?)
            """,
            values,
        )
        conn.execute(
            """
            INSERT INTO mails(sender, recipient, cc, subject, body, status, created_at, priority, classification, label, is_read, starred, thread_id)
            VALUES (?, ?, ?, ?, ?, 'sent', ?, ?, ?, ?, 1, 0, ?)
            """,
            values,
        )
        conn.commit()
        conn.close()

    def toggle_star(self, mail_id: str, username: str, role: str = "user"):
        conn = get_conn(self.db_path)
        if role == "admin":
            conn.execute("UPDATE mails SET starred = CASE starred WHEN 1 THEN 0 ELSE 1 END WHERE id = ?", (mail_id,))
        else:
            conn.execute(
                """
                UPDATE mails
                SET starred = CASE starred WHEN 1 THEN 0 ELSE 1 END
                WHERE id = ?
                  AND (recipient IN (?, ?) OR sender IN (?, ?) OR cc = ? OR cc LIKE ? OR cc LIKE ?)
                """,
                (mail_id,) + self._access_params(username),
            )
        conn.commit()
        conn.close()

    def move_mail(self, mail_id: str, folder: str, username: str, role: str = "user"):
        folder = folder if folder in MAIL_FOLDERS - {"starred"} else "archive"
        conn = get_conn(self.db_path)
        if role == "admin":
            conn.execute("UPDATE mails SET status = ? WHERE id = ?", (folder, mail_id))
        else:
            conn.execute(
                """
                UPDATE mails
                SET status = ?
                WHERE id = ?
                  AND (recipient IN (?, ?) OR sender IN (?, ?) OR cc = ? OR cc LIKE ? OR cc LIKE ?)
                """,
                (folder, mail_id) + self._access_params(username),
            )
        conn.commit()
        conn.close()

    def contacts(self, owner: str):
        conn = get_conn(self.db_path)
        rows = conn.execute("SELECT * FROM contacts WHERE owner = ? ORDER BY display_name", (owner,)).fetchall()
        conn.close()
        return rows

    def add_contact(self, owner: str, display_name: str, email: str, department: str, trust_level: str, notes: str):
        conn = get_conn(self.db_path)
        conn.execute(
            "INSERT INTO contacts(owner, display_name, email, department, trust_level, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (owner, display_name, email, department, trust_level, notes),
        )
        conn.commit()
        conn.close()

    def rules(self, owner: str):
        conn = get_conn(self.db_path)
        rows = conn.execute("SELECT * FROM mail_rules WHERE owner = ? ORDER BY id DESC", (owner,)).fetchall()
        conn.close()
        return rows

    def add_rule(self, owner: str, name: str, expression: str, target_folder: str, enabled: str):
        conn = get_conn(self.db_path)
        enabled_value = 1 if str(enabled) == "1" else 0
        conn.execute(
            "INSERT INTO mail_rules(owner, name, expression, target_folder, enabled) VALUES (?, ?, ?, ?, ?)",
            (owner, name, expression, target_folder, enabled_value),
        )
        conn.commit()
        conn.close()

    def update_profile(self, username: str, full_name: str, title: str, phone: str, signature: str):
        conn = get_conn(self.db_path)
        conn.execute(
            "UPDATE users SET full_name = ?, title = ?, phone = ?, signature = ? WHERE username = ?",
            (full_name, title, phone, signature, username),
        )
        conn.commit()
        conn.close()

    def profile(self, username: str):
        conn = get_conn(self.db_path)
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        return row

    def save_audit(self, username: str, event_type: str, details: str):
        conn = get_conn(self.db_path)
        conn.execute(
            "INSERT INTO audit_logs(username, event_type, details, created_at) VALUES (?, ?, ?, ?)",
            (username, event_type, details, datetime.now(UTC).isoformat(timespec="seconds")),
        )
        conn.commit()
        conn.close()

    def add_attachment(self, mail_id: int, filename: str, storage_name: str, uploader: str, content_type: str, size_bytes: int):
        conn = get_conn(self.db_path)
        conn.execute(
            """
            INSERT INTO attachments(mail_id, filename, storage_path, uploader, content_type, size_bytes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (mail_id, filename, storage_name, uploader, content_type, size_bytes),
        )
        conn.commit()
        conn.close()

    def attachments_for_user(self, username: str, role: str = "user"):
        conn = get_conn(self.db_path)
        if role == "admin":
            rows = conn.execute("SELECT * FROM attachments ORDER BY id DESC").fetchall()
        else:
            rows = conn.execute(
                """
                SELECT a.*
                FROM attachments a
                JOIN mails m ON m.id = a.mail_id
                WHERE a.uploader = ? OR m.recipient IN (?, ?) OR m.sender IN (?, ?)
                ORDER BY a.id DESC
                """,
                (username, username, self._user_mail(username), username, self._user_mail(username)),
            ).fetchall()
        conn.close()
        return rows

    def get_attachment_for_user(self, attachment_id: int, username: str, role: str = "user"):
        conn = get_conn(self.db_path)
        if role == "admin":
            row = conn.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
        else:
            row = conn.execute(
                """
                SELECT a.*
                FROM attachments a
                JOIN mails m ON m.id = a.mail_id
                WHERE a.id = ?
                  AND (a.uploader = ? OR m.recipient IN (?, ?) OR m.sender IN (?, ?))
                """,
                (attachment_id, username, username, self._user_mail(username), username, self._user_mail(username)),
            ).fetchone()
        conn.close()
        return row
