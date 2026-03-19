import os

from dotenv import load_dotenv
from flask import Flask

from config import Config
from extensions import db, migrate
import models  # noqa: F401
from routes import register_blueprints

load_dotenv()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    register_blueprints(app)

    @app.context_processor
    def inject_app_meta():
        app_env = (app.config.get("APP_ENVIRONMENT") or "production").strip().lower()
        is_development = app_env != "production"
        return {
            "app_version": app.config.get("APP_VERSION") or "-",
            "app_environment": app_env,
            "is_development": is_development,
        }

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5200)