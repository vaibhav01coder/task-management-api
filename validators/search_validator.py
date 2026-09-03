from __future__ import annotations

MAX_SEARCH_LENGTH = 200


def validate_search_param(value: str | None) -> tuple[str | None, dict | None]:
    if value is None:
        return None, {"message": "search term must not be blank", "status": 400}

    stripped = value.strip()

    if not stripped:
        return None, {
            "message": "search term must not be blank or consist entirely of whitespace",
            "status": 400,
        }

    if len(stripped) > MAX_SEARCH_LENGTH:
        return None, {
            "message": f"search term must not exceed {MAX_SEARCH_LENGTH} characters (received {len(stripped)})",
            "status": 400,
        }

    return stripped, None
