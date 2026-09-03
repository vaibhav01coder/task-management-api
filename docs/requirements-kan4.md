# Requirements — Task Search and Summary API

## User Story
As a user, I want to search and summarize tasks so I can quickly find tasks by keyword and see status/priority counts at a glance.

## Clarifying Q&A

| # | Question | Answer |
|---|----------|--------|
| 1 | Should search matching be partial (contains) or exact? And match title AND description? | Partial (contains), case-insensitive, matches both title and description. |
| 2 | When search is combined with status/priority filters, are all conditions AND-ed together? | Yes, all filters AND together. |
| 3 | Should `GET /tasks/summary` respect filters or always return counts across ALL tasks? | Always across all tasks — no filter parameters on the summary endpoint. |
| 4 | Should a search with no matches return 200 empty list or 404? | 200 with empty tasks array. |
| 5 | What is the minimum character length for a search term? | 1 character minimum; blank or whitespace-only search term returns 400. |

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | The `GET /tasks` endpoint SHALL accept an optional `search` query parameter to filter tasks by keyword. |
| FR-02 | Keyword matching SHALL be partial (substring contains), case-insensitive, and applied against both the `title` and `description` fields. A task is included if the keyword matches either field. |
| FR-03 | The `search` parameter SHALL combine with existing `status`, `priority`, and pagination parameters using AND logic; only tasks satisfying all provided conditions are returned. |
| FR-04 | A `search` value consisting entirely of whitespace characters SHALL return HTTP 400 with a descriptive error message indicating the search term is invalid. |
| FR-05 | A valid `search` term that matches no tasks SHALL return HTTP 200 with an empty `tasks` array (not HTTP 404). |
| FR-06 | The `search` parameter SHALL accept a minimum of 1 non-whitespace character. No maximum length is defined at this time. |
| FR-07 | The `GET /tasks/summary` endpoint SHALL return aggregate counts across ALL tasks in the system, regardless of any query parameters. |
| FR-08 | The `GET /tasks/summary` response SHALL include: total task count, count per each distinct `status` value, and count per each distinct `priority` value. |
| FR-09 | The `GET /tasks/summary` endpoint SHALL NOT accept or apply any filter parameters; if supplied, they SHALL be silently ignored. |
| FR-10 | Both `GET /tasks` (with search) and `GET /tasks/summary` SHALL return HTTP 200 on success. |

## Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-01 | Performance | Keyword search queries SHOULD return results within 500 ms at p95 under normal load. |
| NFR-02 | Performance | The summary endpoint SHOULD return results within 300 ms at p95. |
| NFR-03 | Scalability | Search queries SHALL remain performant as the dataset grows; DB indexes on `title`, `description`, `status`, and `priority` SHOULD be maintained. |
| NFR-04 | Security | Search input SHALL be sanitised before use in any database query to prevent injection attacks. |
| NFR-05 | Reliability | Both endpoints SHALL return consistent, accurate results under concurrent read load. |
| NFR-06 | Usability | HTTP 400 error responses SHALL include a human-readable `message` field identifying the invalid parameter. |
| NFR-07 | Observability | Search terms (sanitised) and response times SHOULD be logged for monitoring and debugging. |

## Out of Scope

- Full-text search ranking, relevance scoring, or fuzzy/typo-tolerant matching
- Searching fields other than `title` and `description`
- A dedicated search history or saved-search feature
- Real-time or streaming search results
- `GET /tasks/summary` supporting filtered/scoped summaries
- Paginating or sorting the summary response
- Any changes to task creation, update, or deletion endpoints
