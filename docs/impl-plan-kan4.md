# Implementation Plan — Task Search and Summary API

## Tasks

1. **T-1: Add `pg_trgm` extension and update index declarations in `models/task.py`** — Remove proposed B-tree indexes on `title` and `description`. Add GIN trigram indexes via `Index('ix_task_title_trgm', Task.title, postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'})` and an equivalent for `description`. Retain B-tree indexes on `status` and `priority` via `__table_args__`. Add `CREATE EXTENSION IF NOT EXISTS pg_trgm` as a pre-condition note in the production migration section of `README.md`. Depends on: none. Est: 2h

2. **T-2: Implement `validators/search_validator.py`** — Create stateless function `validate_search_param(value: str) -> tuple[str | None, dict | None]`. Logic: (1) if value is `None` or strips to empty string, return `(None, {"message": "search term must not be blank"})` with status 400; (2) if stripped length exceeds 200 characters, return `(None, {"message": "search term must not exceed 200 characters"})` with status 400; (3) otherwise return `(stripped_value, None)`. No external dependencies — stdlib only. Depends on: none. Est: 2h

3. **T-3: Implement `queries/search.py`** — Create `build_search_query(base_query, search: str | None, status: str | None, priority: str | None)` that accepts an existing SQLAlchemy query object and AND-chains: `or_(Task.title.ilike(f"%{search}%"), Task.description.ilike(f"%{search}%"))` when `search` is provided; `Task.status == status` when `status` is provided; `Task.priority == priority` when `priority` is provided. Returns the composed query. SQLAlchemy parameterises `ilike` arguments automatically — no raw string interpolation. Depends on: T-1. Est: 3h

4. **T-4: Implement `queries/summary.py`** — Create `get_summary(db) -> dict` that opens a single explicit transaction at `REPEATABLE READ` isolation using `db.session.connection(execution_options={"isolation_level": "REPEATABLE READ"})` (falls back to default isolation on SQLite, which is documented). Within the transaction block: (1) `SELECT COUNT(*) FROM tasks` → `total`; (2) `SELECT status, COUNT(*) FROM tasks GROUP BY status` → `by_status` dict; (3) `SELECT priority, COUNT(*) FROM tasks GROUP BY priority` → `by_priority` dict. Commits/closes the transaction. Returns `{"total": int, "by_status": {...}, "by_priority": {...}}`. Depends on: T-1. Est: 3h

5. **T-5: Extend `routes/tasks.py` — update `GET /tasks` handler** — Extract `search` from `request.args`. If present, call `validate_search_param(search)`; on validation error, return 400 JSON immediately. Pass validated search string to `build_search_query` alongside existing `status`, `priority` params and the base ORM query. Apply pagination after the composed query. Existing non-search code paths are unchanged. Depends on: T-2, T-3. Est: 2h

6. **T-6: Extend `routes/tasks.py` — register `GET /tasks/summary` handler** — Register route `/tasks/summary` on the existing Blueprint. Handler: ignore all query params per FR-09/DD-17; call `get_summary(db)`; on DB error return 500; on success return 200 with the summary dict. Note: Flask route specificity requires `/tasks/summary` to be registered before any `/tasks/<id>` dynamic route to avoid capture. Depends on: T-4. Est: 2h

7. **T-7: Extend `middleware/logger.py`** — In the after-request hook: (1) read `LOG_SEARCH_TERMS` from config (default `true`); (2) if `true` and `search` param is present in the request, read the sanitised value (from `g` or re-strip from `request.args`), truncate to first 32 characters, and annotate the log line with `[search_term_truncated]` if truncation occurred; (3) log `method`, `path`, sanitised/truncated search term (if applicable), and response duration via `time.monotonic()` delta to stdout using `logging`. If `LOG_SEARCH_TERMS=false`, log only method, path, and duration. Depends on: T-2, T-5. Est: 2h

8. **T-8: Update `config.py`** — Add `LOG_SEARCH_TERMS: bool = os.getenv("LOG_SEARCH_TERMS", "true").lower() == "true"` to the config object. No other changes to config. Depends on: none. Est: 0.5h

9. **T-9: Write `tests/test_search.py`** — pytest file covering: (a) happy path — keyword matches `title` only → 200, task returned; (b) happy path — keyword matches `description` only → 200, task returned; (c) case-insensitivity — uppercase term matches lowercase stored value; (d) combined `search` + `status` filter → AND logic, only intersection returned; (e) combined `search` + `priority` filter → AND logic; (f) valid search term with no matches → 200 with empty `tasks` array; (g) blank string search `search=` → 400 with `message` field; (h) whitespace-only `search=   ` → 400 with `message` field; (i) search term exceeding 200 characters → 400 with `message` field; (j) search with pagination params → correct page/limit/total metadata. All tests use Flask test client with a seeded in-memory SQLite fixture. Depends on: T-5, T-6. Est: 4h

10. **T-10: Write `tests/test_summary.py`** — pytest file covering: (a) empty DB → 200, `total=0`, all status counts 0, all priority counts 0; (b) seeded DB with known distribution → correct `total`, correct `by_status` map, correct `by_priority` map; (c) consistency assertion: `sum(by_status.values()) == total == sum(by_priority.values())`; (d) query params supplied to summary endpoint are silently ignored → response identical to no-param call; (e) concurrent read simulation — two simultaneous summary calls return identical, internally consistent snapshots (using `threading.Thread` within the test). Depends on: T-6. Est: 3h

11. **T-11: Extend `tests/test_tasks.py` with regression assertions** — Add assertions confirming: (a) `GET /tasks` without `search` param continues to return all tasks unfiltered; (b) existing `status` and `priority` filter behaviour is unchanged; (c) existing pagination metadata fields are unchanged in shape; (d) `GET /tasks/summary` route does not interfere with `GET /tasks/<id>` dynamic route resolution. Depends on: T-5, T-6. Est: 1.5h

12. **T-12: Update `README.md`** — Add sections: (a) `search` query parameter — description, minimum 1 non-whitespace character, maximum 200 characters, 400 behaviour, case-insensitive substring matching on `title` and `description`, curl examples; (b) `GET /tasks/summary` — response schema with field descriptions, note that filter params are silently ignored, curl example; (c) Index strategy — note B-tree indexes on `status`/`priority`, GIN trigram indexes on `title`/`description` for PostgreSQL, `CREATE EXTENSION IF NOT EXISTS pg_trgm` pre-condition, sequential-scan behaviour on SQLite dev/test and its non-representativeness of production performance; (d) Security notes — `LOG_SEARCH_TERMS` env var, 32-character log truncation policy, plain-text log risk acknowledgement. Depends on: T-1 through T-11. Est: 2h

---

## Milestones

| Milestone | Tasks | Deliverable |
|---|---|---|
| M-1: Data & Validation Layer | T-1, T-2, T-8 | Updated `models/task.py` with correct index strategy; `search_validator.py` with blank, whitespace, and max-length checks; `config.py` with `LOG_SEARCH_TERMS` flag. Foundation is stable for all upstream work. |
| M-2: Query Layer | T-3, T-4 | `queries/search.py` with `ilike` + AND-chained filter composition; `queries/summary.py` with single REPEATABLE READ transaction issuing three COUNT queries. All ORM logic independently testable without HTTP context. |
| M-3: Route & Middleware Integration | T-5, T-6, T-7 | Extended `GET /tasks` handler with search validation and query delegation; new `GET /tasks/summary` handler; after-request logger emitting sanitised/truncated search terms and response duration. Both endpoints fully wired and manually smoke-testable. |
| M-4: Test Coverage | T-9, T-10, T-11 | Full pytest suites for search (10 cases), summary (5 cases including consistency assertion), and regression suite for existing task endpoints. CI green on all three test files. |
| M-5: Documentation & Release Readiness | T-12 | Updated `README.md` covering search parameter contract, summary response schema, index migration instructions, and security/logging notes. Feature is auditable, operable, and ready for stakeholder review. |

---

## Risk Mitigations

| Risk | Mitigation | Owner |
|---|---|---|
| Leading-wildcard `ILIKE` causes full-table scan on large datasets (R-2), breaching NFR-01 500 ms p95 target | Replace B-tree indexes on `title`/`description` with `pg_trgm` GIN indexes on PostgreSQL (T-1, DD-13, DD-15); document that SQLite dev environments will sequential-scan and are not representative; load-test against PostgreSQL before go-live | Tech Lead |
| Three sequential COUNT queries produce internally inconsistent summary totals under concurrent writes (R-3, R-5) | Wrap all three counts in a single `REPEATABLE READ` transaction in `queries/summary.py` (T-4, DD-16); add consistency assertion test `sum(by_status.values()) == total` (T-10c) | Backend Engineer |
| Arbitrarily long search strings cause memory pressure or query planner degradation (R-1) | Enforce 200-character hard cap in `search_validator.py` returning HTTP 400 (T-2, DD-14); document limit in README (T-12) | Backend Engineer |
| Logging raw search terms exposes sensitive user data in plaintext log streams (R-4) | Truncate logged search terms to 32 characters with `[search_term_truncated]` annotation; add `LOG_SEARCH_TERMS=false` kill-switch in config (T-7, T-8, DD-20); obtain data-privacy stakeholder sign-off before production deployment | Tech Lead |
| `/tasks/summary` route captured by existing `/tasks/<id>` dynamic route pattern | Register `/tasks/summary` route before `/tasks/<id>` in the Flask Blueprint (T-6); add regression test asserting correct route resolution (T-11d) | Backend Engineer |
| SQLite isolation level fallback silently degrades consistency guarantee in test environments | Document the SQLite fallback behaviour in `queries/summary.py` inline comments and in README (T-4, T-12); integration tests run against PostgreSQL in CI to validate the REPEATABLE READ path | Backend Engineer |
| `pg_trgm` extension absent from production PostgreSQL instance blocks `db.create_all()` index creation | Add `CREATE EXTENSION IF NOT EXISTS pg_trgm` as a required pre-migration step in README and production runbook (T-12); fail fast in a startup check or Alembic `env.py` if extension is not present | Tech Lead |