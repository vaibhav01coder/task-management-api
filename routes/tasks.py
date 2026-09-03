import logging
import math
from datetime import datetime

from flask import Blueprint, jsonify, request

from extensions import db
from models.task import Task
from queries.search import build_search_query
from queries.summary import get_summary
from validators.search_validator import validate_search_param
from validators.task_validator import validate_create_payload, validate_update_payload

logger = logging.getLogger(__name__)

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")

VALID_STATUSES = {"pending", "in_progress", "complete"}
VALID_PRIORITIES = {"low", "medium", "high"}


def _task_not_found(task_id):
    return jsonify({"error": "Task not found", "id": task_id}), 404


@tasks_bp.route("", methods=["POST"])
def create_task():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400
    errors = validate_create_payload(data)
    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 400
    task = Task(
        title=data["title"].strip(),
        description=data.get("description"),
        priority=data["priority"],
        due_date=datetime.strptime(data["due_date"], "%Y-%m-%d").date(),
        status="pending",
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


# Registered BEFORE /<int:task_id> so Flask doesn't try to cast "summary" to int
@tasks_bp.route("/summary", methods=["GET"])
def task_summary():
    try:
        summary = get_summary(db)
    except Exception as exc:
        logger.exception("Failed to retrieve task summary: %s", exc)
        return jsonify({"error": "An unexpected error occurred while retrieving the summary"}), 500
    return jsonify(summary), 200


@tasks_bp.route("", methods=["GET"])
def list_tasks():
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        return jsonify({"error": "Query parameter 'page' must be a positive integer"}), 400
    try:
        limit = max(1, min(int(request.args.get("limit", 20)), 200))
    except ValueError:
        return jsonify({"error": "Query parameter 'limit' must be a positive integer"}), 400

    status_filter = request.args.get("status")
    priority_filter = request.args.get("priority")

    if status_filter and status_filter not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status filter. Must be one of: {', '.join(sorted(VALID_STATUSES))}"}), 400
    if priority_filter and priority_filter not in VALID_PRIORITIES:
        return jsonify({"error": f"Invalid priority filter. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}"}), 400

    raw_search = request.args.get("search")
    search_term = None
    if raw_search is not None:
        search_term, search_error = validate_search_param(raw_search)
        if search_error is not None:
            return jsonify({"message": search_error["message"]}), search_error["status"]

    query = build_search_query(Task.query, search=search_term, status=status_filter, priority=priority_filter)
    total = query.count()
    pages = math.ceil(total / limit) if total > 0 else 1
    tasks = query.order_by(Task.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return jsonify({"tasks": [t.to_dict() for t in tasks], "total": total, "page": page, "limit": limit, "pages": pages}), 200


@tasks_bp.route("/<int:task_id>", methods=["GET"])
def get_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return _task_not_found(task_id)
    return jsonify(task.to_dict()), 200


@tasks_bp.route("/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return _task_not_found(task_id)
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400
    errors = validate_update_payload(data)
    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 400
    if "title" in data:
        task.title = data["title"].strip()
    if "description" in data:
        task.description = data["description"]
    if "priority" in data:
        task.priority = data["priority"]
    if "due_date" in data:
        task.due_date = datetime.strptime(data["due_date"], "%Y-%m-%d").date()
    if "status" in data:
        task.status = data["status"]
    task.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(task.to_dict()), 200


@tasks_bp.route("/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return _task_not_found(task_id)
    db.session.delete(task)
    db.session.commit()
    return "", 204


@tasks_bp.route("/<int:task_id>/complete", methods=["PATCH"])
def complete_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return _task_not_found(task_id)
    task.status = "complete"
    task.completed_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(task.to_dict()), 200
