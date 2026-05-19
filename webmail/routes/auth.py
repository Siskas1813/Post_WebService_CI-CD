from flask import Blueprint, render_template, request, session, redirect, url_for, current_app
from webmail.db import get_conn
from webmail.security import safe_redirect_target, verify_password

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def login_page():
    next_url = safe_redirect_target(request.args.get('next', '/dashboard'))
    return render_template('login.html', next_url=next_url)


@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    next_url = safe_redirect_target(request.form.get('next', '/dashboard'))

    conn = get_conn(current_app.config['DB_PATH'])
    row = conn.execute(
        "SELECT username, password, role, full_name, department, title FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    password_ok = bool(row and verify_password(row['password'], password))
    if password_ok:
        conn.execute("UPDATE users SET last_login = datetime('now') WHERE username = ?", (username,))
        conn.commit()
    conn.close()

    if password_ok:
        session['username'] = row['username']
        session['role'] = row['role']
        session['full_name'] = row['full_name']
        session['department'] = row['department']
        session['title'] = row['title']
        return redirect(next_url)

    return render_template('login.html', error='Неверный логин или пароль', next_url=next_url), 401


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login_page'))
