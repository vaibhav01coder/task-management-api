from __future__ import annotations
import logging
from sqlalchemy import func
from models.task import Task

logger = logging.getLogger(__name__)


def get_summary(db) -> dict:
    try:
        db.session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    except Exception:
        logger.debug("REPEATABLE READ not supported (SQLite fallback); using default isolation.")

    total: int = db.session.query(func.count(Task.id)).scalar() or 0

    by_status: dict[str, int] = {
        row[0]: row[1]
        for row in db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
    }

    by_priority: dict[str, int] = {
        row[0]: row[1]
        for row in db.session.query(Task.priority, func.count(Task.id)).group_by(Task.priority).all()
    }

    return {"total": total, "by_status": by_status, "by_priority": by_priority}
