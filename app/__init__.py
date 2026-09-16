from __future__ import annotations

import os
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_object: type[Config] = Config) -> Flask:
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_path=str(project_root / "instance"),
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
        instance_relative_config=False,
    )
    app.config.from_object(config_object)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "info"

    from .models import User, UserSettings
    from .auth import auth_bp
    from .routes import main_bp
    from .api import api_bp
    from .utils import expects_json, settings_to_dict

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return User.query.get(int(user_id))

    @app.before_request
    def ensure_user_settings() -> None:
        if current_user.is_authenticated and current_user.settings is None:
            current_user.settings = UserSettings()
            db.session.add(current_user)
            db.session.commit()

    @app.context_processor
    def inject_globals():
        if current_user.is_authenticated:
            settings = current_user.settings
            settings_payload = settings_to_dict(settings) if settings else {
                "theme": "dark",
                "volume": 70,
                "playback_speed": 1.0,
            }
            user_payload = {
                "id": current_user.id,
                "username": current_user.username,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            }
        else:
            settings_payload = {"theme": "dark", "volume": 70, "playback_speed": 1.0}
            user_payload = None
        return {
            "current_settings": settings_payload,
            "current_user_payload": user_payload,
        }

    def render_error(status_code: int, message: str, template_name: str):
        if expects_json():
            return jsonify({"error": message, "status": status_code}), status_code
        return render_template(template_name, message=message), status_code

    @app.errorhandler(403)
    def forbidden(_error):
        return render_error(403, "You do not have permission to access that resource.", "403.html")

    @app.errorhandler(404)
    def not_found(_error):
        return render_error(404, "The page you requested could not be found.", "404.html")

    @app.errorhandler(500)
    def server_error(_error):
        app.logger.exception("Unhandled exception")
        return render_error(500, "Something went wrong on the server.", "500.html")

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()

    return app


app = create_app()
