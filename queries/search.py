from __future__ import annotations
from sqlalchemy import or_
from models.task import Task


def build_search_query(base_query, search: str | None, status: str | None, priority: str | None):
    query = base_query

    if search is not None:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(pattern),
                Task.description.ilike(pattern),
            )
        )

    if status is not None:
        query = query.filter(Task.status == status)

    if priority is not None:
        query = query.filter(Task.priority == priority)

    return query
