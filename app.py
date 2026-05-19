from webmail import create_app
from werkzeug.serving import WSGIRequestHandler

app = create_app()


if __name__ == '__main__':
    WSGIRequestHandler.server_version = 'CorpMail'
    WSGIRequestHandler.sys_version = ''
    app.run(host='127.0.0.1', port=5000, debug=False)
