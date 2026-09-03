# Design Review — Task Search and Summary API

## Risks & Gaps Identified

### R-1 · No Maximum Length Bound on Search Input

**Risk:** FR-06 explicitly defers a maximum length limit, meaning a client can submit an arbitrarily long search string that is passed directly into an `ilike` pattern, potentially causing excessive memory allocation, CPU time on pattern compilation, or query planner degradation on both SQLite and PostgreSQL.
**Decision:** Enforce a practical server-side maximum (e.g., 200 characters) in `search_validator.py` and return HTTP 400 with a descriptive message; document the limit in the README and revisit with stakeholders to formally close FR-06.

---

### R-2 · `ilike` Full-Table Scan Negates Index Benefit on Description

**Risk:** B-tree indexes on `title` and `description` are not used by leading-wildcard `LIKE`/`ILIKE` patterns (e.g., `%keyword%`), so NFR-03's intent to keep search performant via indexes is architecturally unfulfilled for substring matching on large datasets, and NFR-01's 500 ms p95 target has no structural guarantee.
**Decision:** Document the scan limitation explicitly in the README and DD-13; for PostgreSQL production, replace the B-tree index on `title` and `description` with a `pg_trgm` GIN index (enabling index-accelerated `ILIKE`), and add a note that SQLite dev/test environments will sequential-scan and are not representative of production performance.

---

### R-3 · Summary Endpoint Issues Three Sequential Round-Trips Under Default Configuration

**Risk:** DD-16 describes three focused ORM queries and asserts they "can be sent in one round-trip via connection pooling," but connection pooling does not pipeline independent queries into a single round-trip; each `session.query()` call acquires the connection and executes separately, meaning the 300 ms p95 target (NFR-02) is exposed to three sequential network latencies in production.
**Decision:** Consolidate the summary into a single SQL statement using `func.count()` with conditional aggregation (e.g., `func.sum(case(...))`) or issue all three counts inside one explicit transaction block; update DD-16 to remove the inaccurate pooling claim and reflect the chosen approach.

---

### R-4 · Sanitised Search Term Logging May Still Expose Sensitive Data

**Risk:** NFR-07 and DD-20 specify logging the "sanitised" search term, but the only sanitisation defined is whitespace-stripping; a user searching for a colleague's name, medical term, or credential substring will have that string written to stdout logs in plaintext, creating a data-exposure risk with no defined log-retention or access-control policy.
**Decision:** Define a log-scrubbing policy before the feature ships: either hash/truncate search terms in logs, restrict log access to privileged roles, or explicitly accept the risk with sign-off from the data-privacy stakeholder; update NFR-07 to reflect the agreed approach and add a corresponding entry to the README security notes.

---

### R-5 · `GET /tasks/summary` Has No Cache or Staleness Strategy Under Concurrent Write Load

**Risk:** FR-07 requires counts across *all* tasks and NFR-05 requires "consistent, accurate results under concurrent read load," but the three-query implementation is non-atomic: a task inserted between the total-count query and the GROUP BY queries will produce a response where the `by_status` or `by_priority` sub-totals do not sum to `total`, violating internal consistency without any error being raised.
**Decision:** Wrap the three summary queries in a single serialisable (or at minimum repeatable-read) database transaction so all three counts observe the same snapshot; update `queries/summary.py` and DD-16 to document the isolation level used, and add a test asserting that summary totals are internally consistent.

---

## Agreed Design Decisions

| ID | Decision |
|---|---|
| DD-11 | Extend `GET /tasks` with a `search` query parameter rather than introduce a new `GET /tasks/search` endpoint. |
| DD-12 | Introduce a `queries/` module layer to isolate ORM query construction from route handlers. |
| DD-13 | Use SQLAlchemy `ilike()` with parameterised bind variables for case-insensitive substring matching; supplement with `pg_trgm` GIN index on PostgreSQL to address R-2. |
| DD-14 | `search_validator.py` owns whitespace-blank rejection and whitespace-stripping; query builder trusts validated input. Enforce a server-side maximum length (see R-1). |
| DD-15 | Declare SQLAlchemy `Index` entries in `models/task.py` `__table_args__`; B-tree indexes cover `status` and `priority`; GIN indexes cover `title` and `description` on PostgreSQL. |
| DD-16 | Consolidate summary aggregation into a single atomic transaction at repeatable-read isolation or higher to guarantee internal consistency (see R-3, R-5). |
| DD-17 | `GET /tasks/summary` silently ignores any supplied query parameters per FR-09. |
| DD-18 | No new runtime dependencies introduced; `pg_trgm` is a PostgreSQL built-in extension requiring only `CREATE EXTENSION`. |
| DD-19 | Separate test files `test_search.py` and `test_summary.py`; extend `test_tasks.py` with regression assertions. |
| DD-20 | Log sanitised search terms and response duration in the after-request hook, subject to the data-exposure policy agreed under R-4. |

---

## Architecture Updates Applied

1. **`validators/search_validator.py`** — Add a hard maximum length check (e.g., 200 characters) after the whitespace-blank check; return HTTP 400 with message `"search term must not exceed 200 characters"` on breach. Update the component table and DD-14 to document the limit.

2. **`models/task.py` index strategy** — Replace the proposed B-tree `Index` on `title` and `description` with `Index('ix_task_title_trgm', Task.title, postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'})` and an equivalent for `description`. Retain B-tree indexes on `status` and `priority`. Add a `CREATE EXTENSION IF NOT EXISTS pg_trgm` pre-condition to the production migration notes in `README.md`. Update DD-15 to reflect the dual-index strategy.

3. **`queries/summary.py`** — Replace the three independent `session.query()` calls with a single `with db.session.begin(): ...` block using `isolation_level='REPEATABLE READ'` (PostgreSQL) so all three counts observe an identical database snapshot. Update DD-16 to remove the inaccurate pooling claim and document the isolation level. Add a test in `test_summary.py` asserting `by_status values sum == total == by_priority values sum`.

4. **`middleware/logger.py`** — Before writing the search term to the log, apply a configurable truncation (default: log only the first 32 characters of the term) and tag the log line with `[search_term_truncated]` when truncation occurs. Add `LOG_SEARCH_TERMS=true/false` to `config.py` to allow the feature to be disabled in sensitive environments. Update DD-20 and NFR-07 to reflect the policy.

5. **Data flow diagram update** — Add a "BEGIN REPEATABLE READ / COMMIT" wrapper node around the three summary COUNT steps (S2–S5) to make the transactional boundary visible; add a branch from S1 noting that `pg_trgm` GIN index is engaged for substring queries on PostgreSQL, while SQLite follows a sequential-scan path with an explicit warning annotation.