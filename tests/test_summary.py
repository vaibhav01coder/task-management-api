"""Tests for GET /tasks/summary (FR-07 – FR-10)."""
import pytest
from datetime import date, datetime

from app import create_app
from config import TestingConfig
from extensions import db as _db
from models.task import Task


@pytest.fixture(scope="function")
def app():
    application = create_app(TestingConfig())
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


def _seed(rows):
    _db.session.bulk_save_objects(rows)
    _db.session.commit()


def _task(title, priority, status):
    return Task(
        title=title, description=None, priority=priority, status=status,
        due_date=date(2099, 1, 1),
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )


# ---------------------------------------------------------------------------
# Empty database
# ---------------------------------------------------------------------------

def test_summary_empty_db_returns_zeros(client):
    res = client.get("/tasks/summary")
    assert res.status_code == 200
    body = res.get_json()
    assert body["total"] == 0
    assert body["by_status"] == {}
    assert body["by_priority"] == {}


# ---------------------------------------------------------------------------
# Known distribution
# ---------------------------------------------------------------------------

def test_summary_correct_total(app):
    _seed([
        _task("T1", "high",   "pending"),
        _task("T2", "medium", "in_progress"),
        _task("T3", "low",    "complete"),
    ])
    res = app.test_client().get("/tasks/summary")
    assert res.status_code == 200
    assert res.get_json()["total"] == 3


def test_summary_correct_by_status(app):
    _seed([
        _task("T1", "high",   "pending"),
        _task("T2", "medium", "pending"),
        _task("T3", "low",    "in_progress"),
        _task("T4", "high",   "complete"),
    ])
    body = app.test_client().get("/tasks/summary").get_json()
    assert body["by_status"]["pending"] == 2
    assert body["by_status"]["in_progress"] == 1
    assert body["by_status"]["complete"] == 1


def test_summary_correct_by_priority(app):
    _seed([
        _task("T1", "high",   "pending"),
        _task("T2", "high",   "pending"),
        _task("T3", "medium", "pending"),
        _task("T4", "low",    "complete"),
    ])
    body = app.test_client().get("/tasks/summary").get_json()
    assert body["by_priority"]["high"] == 2
    assert body["by_priority"]["medium"] == 1
    assert body["by_priority"]["low"] == 1


# ---------------------------------------------------------------------------
# Internal consistency (R-5 regression)
# ---------------------------------------------------------------------------

def test_summary_totals_are_internally_consistent(app):
    _seed([_task(f"T{i}", ["high","medium","low"][i%3], ["pending","in_progress","complete"][i%3]) for i in range(9)])
    body = app.test_client().get("/tasks/summary").get_json()
    assert sum(body["by_status"].values()) == body["total"]
    assert sum(body["by_priority"].values()) == body["total"]


# ---------------------------------------------------------------------------
# Query params silently ignored (FR-09)
# ---------------------------------------------------------------------------

def test_summary_ignores_filter_params(app):
    _seed([
        _task("T1", "high",   "pending"),
        _task("T2", "medium", "complete"),
    ])
    c = app.test_client()
    base   = c.get("/tasks/summary").get_json()
    filtered = c.get("/tasks/summary?status=pending&priority=high&search=T1").get_json()
    assert base["total"] == filtered["total"]
    assert base["by_status"] == filtered["by_status"]
    assert base["by_priority"] == filtered["by_priority"]
