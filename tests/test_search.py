"""Tests for GET /tasks keyword search (FR-01 – FR-06)."""
import pytest
from datetime import date, datetime, timedelta

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


@pytest.fixture(scope="function")
def seeded(app):
    """Return test client with 5 known tasks pre-inserted."""
    rows = [
        Task(title="Fix login bug",        description="Users cannot log in with special chars", priority="high",   status="pending",     due_date=date(2099,6,1),  created_at=datetime(2025,1,1), updated_at=datetime(2025,1,1)),
        Task(title="Write unit tests",     description="Cover the authentication module",        priority="medium", status="in_progress", due_date=date(2099,6,15), created_at=datetime(2025,1,2), updated_at=datetime(2025,1,2)),
        Task(title="Deploy to staging",    description="Run login service deployment pipeline",  priority="high",   status="pending",     due_date=date(2099,7,1),  created_at=datetime(2025,1,3), updated_at=datetime(2025,1,3)),
        Task(title="Update documentation", description="Add API reference for new endpoints",    priority="low",    status="complete",    due_date=date(2099,5,30), created_at=datetime(2025,1,4), updated_at=datetime(2025,1,4)),
        Task(title="Refactor DB layer",    description="Improve query performance",              priority="medium", status="pending",     due_date=date(2099,8,1),  created_at=datetime(2025,1,5), updated_at=datetime(2025,1,5)),
    ]
    _db.session.bulk_save_objects(rows)
    _db.session.commit()
    return app.test_client()


# ---------------------------------------------------------------------------
# Happy-path matching
# ---------------------------------------------------------------------------

def test_search_matches_title(seeded):
    res = seeded.get("/tasks?search=login")
    assert res.status_code == 200
    body = res.get_json()
    titles = [t["title"] for t in body["tasks"]]
    assert "Fix login bug" in titles
    assert "Deploy to staging" in titles   # description contains "login"

def test_search_matches_description_only(seeded):
    res = seeded.get("/tasks?search=authentication")
    assert res.status_code == 200
    tasks = res.get_json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Write unit tests"

def test_search_case_insensitive(seeded):
    res = seeded.get("/tasks?search=LOGIN")
    assert res.status_code == 200
    assert res.get_json()["total"] >= 2

def test_search_combined_with_status(seeded):
    res = seeded.get("/tasks?search=login&status=in_progress")
    assert res.status_code == 200
    body = res.get_json()
    # "Fix login bug" is pending, "Deploy to staging" is pending — none in_progress for "login"
    # But "Write unit tests" has "authentication" not "login" — so 0 results
    for t in body["tasks"]:
        assert t["status"] == "in_progress"
        assert "login" in t["title"].lower() or "login" in (t["description"] or "").lower()

def test_search_combined_with_priority(seeded):
    res = seeded.get("/tasks?search=login&priority=high")
    assert res.status_code == 200
    for t in res.get_json()["tasks"]:
        assert t["priority"] == "high"
        assert "login" in t["title"].lower() or "login" in (t["description"] or "").lower()

def test_search_no_match_returns_200_empty(seeded):
    res = seeded.get("/tasks?search=xyzzy_no_match_abc")
    assert res.status_code == 200
    body = res.get_json()
    assert body["tasks"] == []
    assert body["total"] == 0

def test_search_with_pagination_metadata(seeded):
    res = seeded.get("/tasks?search=e&page=1&limit=2")
    body = res.get_json()
    assert res.status_code == 200
    assert "total" in body
    assert "pages" in body
    assert len(body["tasks"]) <= 2


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

def test_search_blank_string_returns_400(client):
    res = client.get("/tasks?search=")
    assert res.status_code == 400
    assert "message" in res.get_json()

def test_search_whitespace_only_returns_400(client):
    res = client.get("/tasks?search=   ")
    assert res.status_code == 400
    assert "message" in res.get_json()

def test_search_over_200_chars_returns_400(client):
    long_term = "a" * 201
    res = client.get(f"/tasks?search={long_term}")
    assert res.status_code == 400
    assert "message" in res.get_json()

def test_search_exactly_200_chars_is_valid(client):
    exact = "a" * 200
    res = client.get(f"/tasks?search={exact}")
    assert res.status_code == 200
