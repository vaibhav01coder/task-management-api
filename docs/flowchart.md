# Task Management API — Architecture Flowchart

```
┌─────────────────────────────────────────────────────────────┐
│                        HTTP CLIENT                          │
│              (curl / browser / Postman)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP Request
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    app.py  ·  create_app()                  │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  middleware/    │  │  extensions/ │  │    config.py  │  │
│  │  logger.py      │  │  db (SQLAlch)│  │  Dev/Test/Prod│  │
│  │  ① log request  │  │              │  │  LOG_SEARCH_  │  │
│  └────────┬────────┘  └──────────────┘  │  TERMS flag   │  │
│           │                             └───────────────┘  │
└───────────┼─────────────────────────────────────────────────┘
            │  before_request hook
            ▼
┌─────────────────────────────────────────────────────────────┐
│               routes/tasks.py  ·  tasks_bp                  │
│                                                             │
│   POST /tasks ──────────────────────────────────────┐      │
│   GET  /tasks ──────────────────┐                   │      │
│   GET  /tasks/summary ──────┐   │                   │      │
│   GET  /tasks/<id>  ─────┐  │   │                   │      │
│   PUT  /tasks/<id>  ─────┤  │   │                   │      │
│   DELETE /tasks/<id> ────┤  │   │                   │      │
│   PATCH /tasks/<id>/     │  │   │                   │      │
│         complete ────────┘  │   │                   │      │
└─────────────────────────────┼───┼───────────────────┼──────┘
                              │   │                   │
           ┌──────────────────┘   │                   │
           │  GET /tasks          │ GET /tasks/summary │  POST/PUT /tasks
           ▼                      ▼                    ▼
┌──────────────────┐  ┌─────────────────────┐  ┌──────────────────────┐
│ validators/      │  │ queries/summary.py  │  │ validators/          │
│ search_validator │  │                     │  │ task_validator.py    │
│                  │  │ REPEATABLE READ     │  │                      │
│ ✗ blank → 400    │  │ COUNT total         │  │ _validate_title()    │
│ ✗ whitespace→400 │  │ COUNT by_status     │  │ _validate_priority() │
│ ✗ >200 chars→400 │  │ COUNT by_priority   │  │ _validate_due_date() │
│ ✓ valid → strip  │  │  (SQLite fallback)  │  │ _validate_status()   │
└────────┬─────────┘  └──────────┬──────────┘  └──────────┬───────────┘
         │                       │                          │
         ▼                       │                          │
┌──────────────────┐             │                          │
│ queries/search.py│             │                          │
│                  │             │                          │
│ build_search_    │             │                          │
│ query()          │             │                          │
│                  │             │                          │
│ Task.title       │             │                          │
│  .ilike(%kw%)    │             │                          │
│ OR               │             │                          │
│ Task.description │             │                          │
│  .ilike(%kw%)    │             │                          │
│                  │             │                          │
│ AND status == ?  │             │                          │
│ AND priority == ?│             │                          │
└────────┬─────────┘             │                          │
         │                       │                          │
         └───────────────────────┴──────────────┬───────────┘
                                                │
                                                ▼
                               ┌────────────────────────────┐
                               │  models/task.py  · Task    │
                               │                            │
                               │  id, title, description    │
                               │  priority, status          │
                               │  due_date, created_at      │
                               │  updated_at, completed_at  │
                               │                            │
                               │  Indexes:                  │
                               │  • ix_tasks_status         │
                               │  • ix_tasks_priority       │
                               │  • ix_tasks_status_priority│
                               │  • ix_tasks_title_trgm     │  ← PostgreSQL GIN
                               │  • ix_tasks_desc_trgm      │  ← SQLite B-tree
                               └──────────────┬─────────────┘
                                              │
                                              ▼
                               ┌────────────────────────────┐
                               │  extensions.py  · db       │
                               │  SQLAlchemy ORM            │
                               │                            │
                               │  SQLite  (dev / test)      │
                               │  PostgreSQL  (production)  │
                               └──────────────┬─────────────┘
                                              │
                          ┌───────────────────┘
                          │  after_request hook
                          ▼
         ┌────────────────────────────────────────┐
         │  middleware/logger.py                  │
         │  ② log response + duration             │
         │  ③ truncate & log search term (≤32ch)  │
         └────────────────┬───────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────────────┐
         │  middleware/error_handlers.py          │
         │  400 → {"error": "..."}                │
         │  404 → {"error": "Resource not found"} │
         │  500 → {"error": "Internal error"}     │
         └────────────────┬───────────────────────┘
                          │  JSON Response
                          ▼
                    HTTP CLIENT
```

---

## File Responsibilities

| File | Role |
|---|---|
| `app.py` | Application factory — wires Flask, DB, middleware, blueprint |
| `config.py` | Dev / Test / Prod config classes; reads env vars |
| `extensions.py` | Shared `db = SQLAlchemy()` instance (avoids circular imports) |
| `models/task.py` | ORM model + indexes + `to_dict()` serialiser |
| `routes/tasks.py` | All HTTP endpoints — routing, pagination, filter validation |
| `validators/task_validator.py` | Validates create/update request body fields |
| `validators/search_validator.py` | Validates `?search=` query param (blank / whitespace / length) |
| `queries/search.py` | Builds `ilike` OR-filter + status/priority AND-chain |
| `queries/summary.py` | Three COUNT queries wrapped in REPEATABLE READ |
| `middleware/logger.py` | Logs every request/response with duration and search term |
| `middleware/error_handlers.py` | Converts Flask HTTP exceptions to JSON error responses |

---

## Request Lifecycle (step by step)

```
1. Request arrives
       │
2. logger.py before_request  →  logs "→ METHOD /path"
       │
3. routes/tasks.py           →  matched to endpoint function
       │
4a. (search)  search_validator.py  →  validate ?search= param
4b. (search)  queries/search.py    →  build ilike OR-filter query
4c. (summary) queries/summary.py   →  run 3 COUNT queries
4d. (create)  task_validator.py    →  validate request body
       │
5. models/task.py + extensions.db  →  execute SQL via SQLAlchemy
       │
6. Route function              →  return jsonify(...), status_code
       │
7. logger.py after_request    →  logs "← METHOD /path STATUS (Xms)"
       │
8. JSON Response sent to client
```
