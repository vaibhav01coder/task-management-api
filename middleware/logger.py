import logging
import time

logger = logging.getLogger(__name__)


def register_logger(app):
    @app.before_request
    def _before():
        from flask import g, request
        g._request_start_time = time.monotonic()
        logger.info("→ %s %s", request.method, request.path)

    @app.after_request
    def _after(response):
        from flask import current_app, g, request

        start = getattr(g, "_request_start_time", None)
        duration_ms = f"{(time.monotonic() - start) * 1000:.1f}ms" if start is not None else "?ms"

        log_search = current_app.config.get("LOG_SEARCH_TERMS", True)
        max_chars = current_app.config.get("LOG_SEARCH_TERM_MAX_CHARS", 32)

        search_fragment = ""
        raw_search = request.args.get("search")
        if log_search and raw_search is not None:
            sanitised = raw_search.strip()
            if sanitised:
                display = sanitised[:max_chars]
                truncated = len(sanitised) > max_chars
                search_fragment = f' search={display!r}{"[search_term_truncated]" if truncated else ""}'

        logger.info("← %s %s %s%s (%s)", request.method, request.path, response.status_code, search_fragment, duration_ms)
        return response
