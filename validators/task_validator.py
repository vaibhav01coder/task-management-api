import re
from datetime import date, datetime
from typing import Dict

VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"pending", "in_progress", "complete"}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_title(value, errors: Dict, required: bool = True):
    if required and (value is None or str(value).strip() == ""):
        errors["title"] = "Title is required and cannot be empty."
        return
    if value is not None:
        if str(value).strip() == "":
            errors["title"] = "Title cannot be empty."
        elif len(str(value)) > 255:
            errors["title"] = "Title must not exceed 255 characters."


def _validate_priority(value, errors: Dict, required: bool = True):
    if required and value is None:
        errors["priority"] = f"Priority is required. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}."
        return
    if value is not None and value not in VALID_PRIORITIES:
        errors["priority"] = f"Invalid priority '{value}'. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}."


def _validate_due_date(value, errors: Dict, required: bool = True, check_past: bool = True):
    if required and value is None:
        errors["due_date"] = "due_date is required in YYYY-MM-DD format."
        return
    if value is not None:
        if not isinstance(value, str) or not DATE_PATTERN.match(value):
            errors["due_date"] = "due_date must be a valid date in YYYY-MM-DD format."
            return
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            errors["due_date"] = "due_date must be a valid calendar date in YYYY-MM-DD format."
            return
        if check_past and parsed < date.today():
            errors["due_date"] = "due_date must not be in the past."


def _validate_status(value, errors: Dict):
    if value is not None and value not in VALID_STATUSES:
        errors["status"] = f"Invalid status '{value}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}."


def validate_create_payload(data: dict) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    _validate_title(data.get("title"), errors, required=True)
    _validate_priority(data.get("priority"), errors, required=True)
    _validate_due_date(data.get("due_date"), errors, required=True, check_past=True)
    return errors


def validate_update_payload(data: dict) -> Dict[str, str]:
    errors: Dict[str, str] = {}

    if not data:
        errors["body"] = "Request body must contain at least one field to update."
        return errors

    if "title" in data:
        _validate_title(data["title"], errors, required=False)
    if "priority" in data:
        _validate_priority(data["priority"], errors, required=False)
    if "due_date" in data:
        _validate_due_date(data["due_date"], errors, required=False, check_past=False)
    if "status" in data:
        _validate_status(data["status"], errors)

    return errors
