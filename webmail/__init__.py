import os
import secrets

from flask import Flask, abort, request, session
from .db import init_db, seed_data
from .routes.auth import auth_bp
from .routes.mailbox import mailbox_bp
from .routes.admin import admin_bp
from .routes.api import api_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder='../templates', static_folder='../static', static_url_path='/static')

    app.config['SECRET_KEY'] = os.environ.get('CORP_MAIL_SECRET_KEY') or secrets.token_urlsafe(32)
    app.config['DB_PATH'] = os.environ.get('CORP_MAIL_DB_PATH', 'corp_mail.db')
    app.config['UPLOAD_DIR'] = os.environ.get('CORP_MAIL_UPLOAD_DIR', 'uploads')
    app.config['SMTP_PASSWORD'] = os.environ.get('CORP_MAIL_SMTP_PASSWORD', '')
    app.config['APP_BRAND'] = 'Corp Mail Enterprise'
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('CORP_MAIL_COOKIE_SECURE', '0') == '1'

    init_db(app.config['DB_PATH'])
    seed_data(app.config['DB_PATH'])

    @app.context_processor
    def csrf_context():
        def csrf_token():
            token = session.get('csrf_token')
            if not token:
                token = secrets.token_urlsafe(32)
                session['csrf_token'] = token
            return token

        return {'csrf_token': csrf_token}

    @app.before_request
    def validate_csrf_token():
        if app.config.get('TESTING') or os.environ.get('CORP_MAIL_DISABLE_CSRF_FOR_DAST') == '1' or request.method != 'POST':
            return None
        expected = session.get('csrf_token')
        provided = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not expected or not provided or not secrets.compare_digest(expected, provided):
            abort(400)
        return None

    app.register_blueprint(auth_bp)
    app.register_blueprint(mailbox_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    @app.after_request
    def set_security_headers(response):
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https://i.pravatar.cc; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
        response.headers['Cache-Control'] = 'no-store, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers.pop('Server', None)
        return response

    return app
