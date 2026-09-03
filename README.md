# Task Management REST API

A production-ready REST API for task management built with Flask and SQLAlchemy. Supports full CRUD operations, pagination, filtering, and clean error handling.

---

## Prerequisites

- Python 3.9+
- pip

---

## Installation

```bash
# 1. Clone the repo
git clone <repo-url>
cd task-management-api

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Configure environment
cp .env.example .env
# Edit .env as needed
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///tasks.db` | Database connection URL |
| `FLASK_ENV` | `development` | `development`, `production`, or `testing` |
| `PORT` | `5000` | Port the server listens on |

---

## Run Locally

```bash
python app.py
```

Server starts at `http://localhost:5000`.

---

## Run Tests

```bash
pytest
```

All 39 tests run against an isolated in-memory SQLite database — no file artifacts.

---

## API Reference

### POST /tasks — Create a task

```bash
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk","priority":"low","due_date":"2027-01-01"}'
```

**Response 201:**
```json
{"id":1,"title":"Buy milk","description":null,"priority":"low","status":"pending",
 "due_date":"2027-01-01","created_at":"...","updated_at":"...","completed_at":null}
```

---

### GET /tasks — List tasks (paginated)

```bash
curl "http://localhost:5000/tasks?page=1&limit=10&priority=high&status=pending"
```

**Response 200:**
```json
{"tasks":[...],"total":42,"page":1,"limit":10,"pages":5}
```

---

### GET /tasks/{id} — Get single task

```bash
curl http://localhost:5000/tasks/1
```

---

### PUT /tasks/{id} — Update task

```bash
curl -X PUT http://localhost:5000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy oat milk","status":"in_progress"}'
```

---

### DELETE /tasks/{id} — Delete task

```bash
curl -X DELETE http://localhost:5000/tasks/1
# 204 No Content
```

---

### PATCH /tasks/{id}/complete — Mark complete

```bash
curl -X PATCH http://localhost:5000/tasks/1/complete
```

**Response 200:** task with `"status":"complete"` and `"completed_at"` set.

---

## Project Structure

```
task-management-api/
├── app.py                         # Entry point / application factory
├── config.py                      # DevelopmentConfig / ProductionConfig / TestingConfig
├── extensions.py                  # Shared SQLAlchemy db instance
├── models/task.py                 # Task ORM model
├── routes/tasks.py                # All endpoint handlers (Blueprint)
├── validators/task_validator.py   # Stateless payload validation
├── middleware/
│   ├── logger.py                  # Request/response logging
│   └── error_handlers.py         # Global 400/404/500 handlers
└── tests/test_tasks.py            # 39-test suite (in-memory SQLite)
```
