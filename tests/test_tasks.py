"""
Unit tests for the Task Management REST API.
All tests run against an in-memory SQLite database; no file artifacts are created.
"""
import pytest
from datetime import date, timedelta

from app import create_app
from extensions import db as _db
from config import TestingConfig


@pytest.fixture(scope="function")
def app():
    application = create_app(TestingConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


def tomorrow():
    return (date.today() + timedelta(days=1)).isoformat()


def yesterday():
    return (date.today() - timedelta(days=1)).isoformat()


def make_task(client, **overrides):
    payload = {
        "title": "Test Task",
        "description": "A sample description",
        "priority": "medium",
        "due_date": tomorrow(),
        **overrides,
    }
    return client.post("/tasks", json=payload)


class TestCreateTask:
    def test_create_task_success_returns_201(self, client):
        res = make_task(client)
        assert res.status_code == 201
        data = res.get_json()
        assert data["id"] is not None
        assert data["title"] == "Test Task"
        assert data["priority"] == "medium"
        assert data["status"] == "pending"
        assert data["completed_at"] is None
        assert data["created_at"] is not None
        assert data["updated_at"] is not None

    def test_create_task_without_description(self, client):
        res = make_task(client, description=None)
        assert res.status_code == 201
        assert res.get_json()["description"] is None

    def test_create_task_missing_title_returns_400(self, client):
        res = client.post("/tasks", json={"priority": "low", "due_date": tomorrow()})
        assert res.status_code == 400
        body = res.get_json()
        assert "error" in body
        assert "title" in body["fields"]

    def test_create_task_empty_title_returns_400(self, client):
        res = make_task(client, title="   ")
        assert res.status_code == 400
        assert "title" in res.get_json()["fields"]

    def test_create_task_title_too_long_returns_400(self, client):
        res = make_task(client, title="x" * 256)
        assert res.status_code == 400
        assert "title" in res.get_json()["fields"]

    def test_create_task_missing_priority_returns_400(self, client):
        res = client.post("/tasks", json={"title": "T", "due_date": tomorrow()})
        assert res.status_code == 400
        assert "priority" in res.get_json()["fields"]

    def test_create_task_invalid_priority_returns_400(self, client):
        res = make_task(client, priority="urgent")
        assert res.status_code == 400
        assert "priority" in res.get_json()["fields"]

    def test_create_task_missing_due_date_returns_400(self, client):
        res = client.post("/tasks", json={"title": "T", "priority": "low"})
        assert res.status_code == 400
        assert "due_date" in res.get_json()["fields"]

    def test_create_task_past_due_date_returns_400(self, client):
        res = make_task(client, due_date=yesterday())
        assert res.status_code == 400
        assert "due_date" in res.get_json()["fields"]

    def test_create_task_invalid_date_format_returns_400(self, client):
        res = make_task(client, due_date="01/12/2099")
        assert res.status_code == 400
        assert "due_date" in res.get_json()["fields"]

    def test_create_task_non_json_body_returns_400(self, client):
        res = client.post("/tasks", data="not json", content_type="text/plain")
        assert res.status_code == 400

    def test_create_task_all_priorities_accepted(self, client):
        for priority in ("low", "medium", "high"):
            res = make_task(client, title=f"Task {priority}", priority=priority)
            assert res.status_code == 201, f"Expected 201 for priority={priority}"


class TestListTasks:
    def test_list_tasks_empty_returns_200(self, client):
        res = client.get("/tasks")
        assert res.status_code == 200
        body = res.get_json()
        assert body["tasks"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["limit"] == 20
        assert "pages" in body

    def test_list_tasks_returns_created_task(self, client):
        make_task(client)
        res = client.get("/tasks")
        assert res.status_code == 200
        assert len(res.get_json()["tasks"]) == 1

    def test_list_tasks_pagination_metadata(self, client):
        for i in range(5):
            make_task(client, title=f"Task {i}")
        res = client.get("/tasks?page=1&limit=3")
        body = res.get_json()
        assert body["total"] == 5
        assert body["page"] == 1
        assert body["limit"] == 3
        assert body["pages"] == 2
        assert len(body["tasks"]) == 3

    def test_list_tasks_page_2(self, client):
        for i in range(5):
            make_task(client, title=f"Task {i}")
        res = client.get("/tasks?page=2&limit=3")
        body = res.get_json()
        assert body["page"] == 2
        assert len(body["tasks"]) == 2

    def test_list_tasks_filter_by_status(self, client):
        make_task(client, title="Pending Task")
        create_res = make_task(client, title="Complete Task")
        task_id = create_res.get_json()["id"]
        client.patch(f"/tasks/{task_id}/complete")

        res = client.get("/tasks?status=complete")
        body = res.get_json()
        assert body["total"] == 1
        assert body["tasks"][0]["status"] == "complete"

    def test_list_tasks_filter_by_priority(self, client):
        make_task(client, title="High Task", priority="high")
        make_task(client, title="Low Task", priority="low")
        res = client.get("/tasks?priority=high")
        body = res.get_json()
        assert body["total"] == 1
        assert body["tasks"][0]["priority"] == "high"

    def test_list_tasks_invalid_status_filter_returns_400(self, client):
        res = client.get("/tasks?status=invalid")
        assert res.status_code == 400
        assert "error" in res.get_json()

    def test_list_tasks_invalid_priority_filter_returns_400(self, client):
        res = client.get("/tasks?priority=invalid")
        assert res.status_code == 400
        assert "error" in res.get_json()


class TestGetTask:
    def test_get_task_success(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.get(f"/tasks/{task_id}")
        assert res.status_code == 200
        assert res.get_json()["id"] == task_id

    def test_get_task_unknown_id_returns_404(self, client):
        res = client.get("/tasks/99999")
        assert res.status_code == 404
        body = res.get_json()
        assert "error" in body
        assert body["id"] == 99999


class TestUpdateTask:
    def test_update_task_title(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.put(f"/tasks/{task_id}", json={"title": "Updated Title"})
        assert res.status_code == 200
        assert res.get_json()["title"] == "Updated Title"

    def test_update_task_priority(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.put(f"/tasks/{task_id}", json={"priority": "high"})
        assert res.status_code == 200
        assert res.get_json()["priority"] == "high"

    def test_update_task_status(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.put(f"/tasks/{task_id}", json={"status": "in_progress"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "in_progress"

    def test_update_task_multiple_fields(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.put(f"/tasks/{task_id}", json={
            "title": "New Title",
            "priority": "low",
            "status": "in_progress",
        })
        assert res.status_code == 200
        body = res.get_json()
        assert body["title"] == "New Title"
        assert body["priority"] == "low"
        assert body["status"] == "in_progress"

    def test_update_task_unknown_id_returns_404(self, client):
        res = client.put("/tasks/99999", json={"title": "Nope"})
        assert res.status_code == 404
        assert "error" in res.get_json()

    def test_update_task_invalid_priority_returns_400(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.put(f"/tasks/{task_id}", json={"priority": "critical"})
        assert res.status_code == 400
        assert "priority" in res.get_json()["fields"]

    def test_update_task_invalid_status_returns_400(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.put(f"/tasks/{task_id}", json={"status": "done"})
        assert res.status_code == 400
        assert "status" in res.get_json()["fields"]

    def test_update_task_title_too_long_returns_400(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.put(f"/tasks/{task_id}", json={"title": "x" * 256})
        assert res.status_code == 400
        assert "title" in res.get_json()["fields"]

    def test_update_task_non_json_returns_400(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.put(f"/tasks/{task_id}", data="bad", content_type="text/plain")
        assert res.status_code == 400


class TestDeleteTask:
    def test_delete_task_success_returns_204(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.delete(f"/tasks/{task_id}")
        assert res.status_code == 204
        assert res.data == b""

    def test_delete_task_is_gone_afterwards(self, client):
        task_id = make_task(client).get_json()["id"]
        client.delete(f"/tasks/{task_id}")
        res = client.get(f"/tasks/{task_id}")
        assert res.status_code == 404

    def test_delete_task_unknown_id_returns_404(self, client):
        res = client.delete("/tasks/99999")
        assert res.status_code == 404
        assert "error" in res.get_json()


class TestCompleteTask:
    def test_complete_task_sets_status_and_timestamp(self, client):
        task_id = make_task(client).get_json()["id"]
        res = client.patch(f"/tasks/{task_id}/complete")
        assert res.status_code == 200
        body = res.get_json()
        assert body["status"] == "complete"
        assert body["completed_at"] is not None

    def test_complete_task_idempotent(self, client):
        task_id = make_task(client).get_json()["id"]
        client.patch(f"/tasks/{task_id}/complete")
        res = client.patch(f"/tasks/{task_id}/complete")
        assert res.status_code == 200
        assert res.get_json()["status"] == "complete"

    def test_complete_task_unknown_id_returns_404(self, client):
        res = client.patch("/tasks/99999/complete")
        assert res.status_code == 404
        body = res.get_json()
        assert "error" in body
        assert body["id"] == 99999


class TestErrorHandling:
    def test_404_response_has_error_field(self, client):
        res = client.get("/tasks/99999")
        assert "error" in res.get_json()

    def test_400_response_has_error_field(self, client):
        res = client.post("/tasks", json={})
        assert "error" in res.get_json()
