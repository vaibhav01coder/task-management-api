import logging
import os

from flask import Flask, jsonify

from config import get_config
from extensions import db
from middleware.error_handlers import register_error_handlers
from middleware.logger import register_logger
from routes.tasks import tasks_bp


def create_app(config_object=None):
    """Application factory — used by both runtime and test suite."""
    app = Flask(__name__)

    if config_object is None:
        config_object = get_config()
    app.config.from_object(config_object)

    db.init_app(app)

    register_logger(app)
    register_error_handlers(app)

    app.register_blueprint(tasks_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    application = create_app()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    application.run(host="0.0.0.0", port=port, debug=debug)
