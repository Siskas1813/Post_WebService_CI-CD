import sqlite3
from datetime import UTC, datetime

from webmail.security import hash_password


def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _add_column_if_missing(conn: sqlite3.Connection, statement: str):
    try:
        conn.execute(statement)
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


def init_db(db_path: str):
    conn = get_conn(db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            department TEXT,
            role TEXT,
            signature TEXT
        );

        CREATE TABLE IF NOT EXISTS mails (
            id INTEGER PRIMARY KEY,
            sender TEXT,
            recipient TEXT,
            cc TEXT,
            subject TEXT,
            body TEXT,
            status TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY,
            mail_id INTEGER,
            filename TEXT,
            storage_path TEXT,
            uploader TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY,
            username TEXT,
            event_type TEXT,
            details TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY,
            owner TEXT,
            api_key TEXT,
            scope TEXT,
            expires_at TEXT
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY,
            owner TEXT,
            display_name TEXT,
            email TEXT,
            department TEXT,
            trust_level TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS mail_rules (
            id INTEGER PRIMARY KEY,
            owner TEXT,
            name TEXT,
            expression TEXT,
            target_folder TEXT,
            enabled INTEGER
        );
        """
    )

    _add_column_if_missing(conn, "ALTER TABLE users ADD COLUMN title TEXT DEFAULT ''")
    _add_column_if_missing(conn, "ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''")
    _add_column_if_missing(conn, "ALTER TABLE users ADD COLUMN location TEXT DEFAULT ''")
    _add_column_if_missing(conn, "ALTER TABLE users ADD COLUMN avatar_url TEXT DEFAULT ''")
    _add_column_if_missing(conn, "ALTER TABLE users ADD COLUMN last_login TEXT DEFAULT ''")
    _add_column_if_missing(conn, "ALTER TABLE users ADD COLUMN api_quota INTEGER DEFAULT 1000")

    _add_column_if_missing(conn, "ALTER TABLE mails ADD COLUMN priority TEXT DEFAULT 'normal'")
    _add_column_if_missing(conn, "ALTER TABLE mails ADD COLUMN classification TEXT DEFAULT 'internal'")
    _add_column_if_missing(conn, "ALTER TABLE mails ADD COLUMN label TEXT DEFAULT ''")
    _add_column_if_missing(conn, "ALTER TABLE mails ADD COLUMN is_read INTEGER DEFAULT 0")
    _add_column_if_missing(conn, "ALTER TABLE mails ADD COLUMN starred INTEGER DEFAULT 0")
    _add_column_if_missing(conn, "ALTER TABLE mails ADD COLUMN thread_id TEXT DEFAULT ''")

    _add_column_if_missing(conn, "ALTER TABLE attachments ADD COLUMN content_type TEXT DEFAULT ''")
    _add_column_if_missing(conn, "ALTER TABLE attachments ADD COLUMN size_bytes INTEGER DEFAULT 0")

    _add_column_if_missing(conn, "ALTER TABLE api_keys ADD COLUMN last_used TEXT DEFAULT ''")
    _add_column_if_missing(conn, "ALTER TABLE api_keys ADD COLUMN enabled INTEGER DEFAULT 1")

    conn.commit()
    conn.close()


def _exists(conn: sqlite3.Connection, table: str, where: str, value: str) -> bool:
    queries = {
        ("users", "username"): "SELECT 1 FROM users WHERE username = ? LIMIT 1",
        ("mails", "subject"): "SELECT 1 FROM mails WHERE subject = ? LIMIT 1",
        ("api_keys", "owner"): "SELECT 1 FROM api_keys WHERE owner = ? LIMIT 1",
    }
    query = queries[(table, where)]
    return conn.execute(query, (value,)).fetchone() is not None


def seed_data(db_path: str):
    conn = get_conn(db_path)
    c = conn.cursor()

    users = [
        ("employee", hash_password("employee123"), "Ivan Petrov", "Finance", "user", "Sent from Corp Mail", "Financial analyst", "+7 495 100-20-30", "Moscow HQ", "https://i.pravatar.cc/96?img=11", 750),
        ("manager", hash_password("manager123"), "Olga Romanova", "Operations", "manager", "Regards, Manager", "Operations manager", "+7 495 100-20-31", "Moscow HQ", "https://i.pravatar.cc/96?img=32", 1200),
        ("admin", hash_password("admin123"), "Security Admin", "IT", "admin", "SecOps", "Platform administrator", "+7 495 100-20-99", "Data center", "https://i.pravatar.cc/96?img=52", 5000),
    ]
    for user in users:
        if not _exists(conn, "users", "username", user[0]):
            c.execute(
                """
                INSERT INTO users (username, password, full_name, department, role, signature, title, phone, location, avatar_url, api_quota)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                user,
            )
        else:
            c.execute(
                """
                UPDATE users
                SET password=?, full_name=?, department=?, role=?, signature=?, title=?, phone=?, location=?, avatar_url=?, api_quota=?
                WHERE username=?
                """,
                (user[1], user[2], user[3], user[4], user[5], user[6], user[7], user[8], user[9], user[10], user[0]),
            )

    mails = [
        ("ceo@corp.local", "employee", "manager", "Q2 board packet", "Prepare the quarterly finance packet for the board meeting. Include risks, cash-flow and forecast.", "inbox", "high", "confidential", "Board", 0),
        ("hr@corp.local", "employee", "", "Policies update", "Remote work and corporate data classification policies were updated.", "inbox", "normal", "internal", "HR", 0),
        ("soc@corp.local", "employee", "admin", "Suspicious login digest", "SIEM detected sign-ins from new locations. Review the audit log and confirm legitimacy.", "inbox", "high", "restricted", "Security", 0),
        ("manager", "employee", "", "Re: Budget draft", "Accepted. Need more detail on vendor spend and next month forecast.", "inbox", "normal", "internal", "Finance", 1),
        ("employee", "manager", "", "Budget draft", "Sending the budget draft. There are still open licensing questions.", "sent", "normal", "internal", "Finance", 1),
        ("employee", "employee", "", "Draft: incident response note", "Draft note for incident response. Needs IT approval.", "drafts", "normal", "restricted", "Draft", 0),
        ("archive-bot@corp.local", "employee", "", "Archived migration notice", "The message was archived after the migration project was closed.", "archive", "low", "internal", "Archive", 1),
    ]
    for sender, recipient, cc, subject, body, status, priority, classification, label, is_read in mails:
        if not _exists(conn, "mails", "subject", subject):
            c.execute(
                """
                INSERT INTO mails (sender, recipient, cc, subject, body, status, created_at, priority, classification, label, is_read, starred, thread_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (sender, recipient, cc, subject, body, status, datetime.now(UTC).isoformat(timespec="seconds"), priority, classification, label, is_read, f"thread-{abs(hash(subject)) % 10000}"),
            )

    contacts = [
        ("employee", "Olga Romanova", "manager@corp.local", "Operations", "trusted", "Approves budgets and purchasing processes"),
        ("employee", "Security Operations", "soc@corp.local", "IT", "trusted", "Channel for incident notifications"),
        ("employee", "Vendor Desk", "vendors@corp.local", "Procurement", "external", "External suppliers, verify attachments"),
        ("manager", "Ivan Petrov", "employee@corp.local", "Finance", "trusted", "Prepares quarterly reporting"),
    ]
    for contact in contacts:
        if not c.execute("SELECT 1 FROM contacts WHERE owner=? AND email=?", (contact[0], contact[2])).fetchone():
            c.execute(
                "INSERT INTO contacts(owner, display_name, email, department, trust_level, notes) VALUES (?, ?, ?, ?, ?, ?)",
                contact,
            )

    rules = [
        ("employee", "Board priority", "subject contains board", "inbox", 1),
        ("employee", "Vendor quarantine", "sender contains vendor", "archive", 0),
    ]
    for rule in rules:
        if not c.execute("SELECT 1 FROM mail_rules WHERE owner=? AND name=?", (rule[0], rule[1])).fetchone():
            c.execute(
                "INSERT INTO mail_rules(owner, name, expression, target_folder, enabled) VALUES (?, ?, ?, ?, ?)",
                rule,
            )

    if not _exists(conn, "api_keys", "owner", "integration-bot"):
        c.execute(
            """
            INSERT INTO api_keys (owner, api_key, scope, expires_at, last_used, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("integration-bot", "cmk_sample_rotation_required_001", "mail:read mail:send admin:read", "2099-12-31", "", 1),
        )

    conn.commit()
    conn.close()


def run_raw_query(db_path: str, query: str, params: tuple = ()):
    conn = get_conn(db_path)
    try:
        rows = conn.execute(query, params).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()
