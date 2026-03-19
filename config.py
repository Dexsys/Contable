import os

basedir = os.path.abspath(os.path.dirname(__file__))


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def resolve_database_url():
    configured = os.environ.get('DATABASE_URL')
    if not configured:
        return 'sqlite:///' + os.path.join(basedir, 'instance', 'contable.db')

    if configured.startswith('sqlite:///') and not configured.startswith('sqlite:////'):
        relative_path = configured.replace('sqlite:///', '', 1)
        return 'sqlite:///' + os.path.join(basedir, relative_path)

    return configured


os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-env')
    SQLALCHEMY_DATABASE_URI = resolve_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'uploads')
    # Limite total del body HTTP (texto + imagenes) en MB.
    MAX_CONTENT_LENGTH_MB = env_int('MAX_CONTENT_LENGTH_MB', 50)
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH_MB * 1024 * 1024

    # SMTP para recuperación de contraseña
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = env_bool('MAIL_USE_TLS', True)
    MAIL_USE_SSL = env_bool('MAIL_USE_SSL', False)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', False)

    _raw_app_env = (os.environ.get('APP_ENV') or os.environ.get('FLASK_ENV') or '').strip().lower()
    APP_ENVIRONMENT = 'production' if _raw_app_env in ('', 'prod', 'production') else 'development'
    APP_VERSION = (os.environ.get('APP_VERSION') or os.environ.get('RELEASE_VERSION') or '1.2026.0319').strip()
