import logging

logger = logging.getLogger(__name__)


def register_logger(app):
    @app.before_request
    def _before():
        from flask import request
        logger.info("→ %s %s", request.method, request.path)

    @app.after_request
    def _after(response):
        from flask import request
        logger.info("← %s %s %s", request.method, request.path, response.status_code)
        return response
