# Phase 1 Upstream PR — Data Layer Fixes

---

## Files to include in the PR

- `src/zettelkasten_mcp/models/db_models.py`
- `src/zettelkasten_mcp/storage/note_repository.py`
- `tests/test_note_repository.py`

**Do not include `pyproject.toml` or `uv.lock`** — see explanation at the bottom.

---

## Branch name

Following the repo's `YYYY-MM-DD_author_description` convention — substitute your date and handle:

```
2026-03-26_yourhandle_data-layer-correctness-and-performance
```

---

## Commit message

```
address review feedback: cache safety, content consistency, json serialization, tmp cleanup, pragma scoping

- Return defensive copies from LRU cache: _cache_get() and the cache-miss
  path in get() now return note.model_copy(deep=True) so callers cannot
  mutate cached instances.

- Store rendered content in DB: _index_note() accepts optional
  rendered_content parameter; create() and update() pass
  frontmatter.loads(markdown).content so db_note.content matches the file
  (including # Title heading and ## Links section). Eliminates content
  divergence between get() and DB-backed read paths.

- JSON-safe metadata serialization: add _json_default() handler that
  converts datetime.date/datetime to ISO strings. Used by both
  _index_note() and update() to prevent TypeError on YAML-native types.

- Temp file cleanup: add finally blocks to create() and update() that
  remove .md.tmp on failure, preventing orphaned temp files.

- Connection-scoped PRAGMAs: move synchronous, cache_size, and
  busy_timeout to @event.listens_for(engine, "connect") so they apply
  to every new connection, not just the one opened during init_db().
  WAL mode (persistent) remains as a one-time operation.

- Remove unused imports: create_engine, Session, Base from
  note_repository.py.

Add 3 tests: cache mutation safety, datetime metadata round-trip,
content consistency between search() and get().
```

---

## PR title

```
data layer correctness and performance improvements
```

---

## PR description

~~~markdown
## Summary

Data layer correctness and performance improvements. No new features, no
API changes. All 78 tests pass (55 existing + 23 new).

### SQL injection fix

Six raw SQL DELETE statements used f-string interpolation. Replaced with
parameterized queries in `_index_note()`, `update()`, and `delete()`.

### SQLite WAL mode + connection-scoped PRAGMAs

WAL mode enables concurrent readers + single writer (vs the default
exclusive lock). `synchronous`, `cache_size`, and `busy_timeout` are
applied via `@event.listens_for(engine, "connect")` so they take effect
on every connection, not just the one opened during `init_db()`. WAL
itself is persistent and set once.

### Atomic file writes with failure cleanup

`create()` and `update()` write to a `.md.tmp` temp file first, then
`Path.replace()` (atomic on POSIX). A `finally` block removes the temp
file if `replace()` fails, preventing orphaned `.md.tmp` files.

### In-memory LRU note cache

Module-level `OrderedDict` cache (max 256 entries) keyed by
`(path_str, mtime_ns)`. `get()` returns `note.model_copy(deep=True)` on
both cache hits and misses so callers cannot mutate cached instances.
`update()` and `delete()` evict immediately.

### `metadata_json` column + JSON-safe serialization

Nullable `metadata_json TEXT` column on `DBNote` stores custom frontmatter
as JSON. A `_json_default()` handler converts `datetime.date` and
`datetime.datetime` to ISO strings to prevent `TypeError` on YAML-native
types. Migration in `init_db()` adds the column via `ALTER TABLE` if absent.

### `_note_from_db()` — DB reconstruction for all query paths

Reconstructs a complete `Note` from ORM rows (tags, outgoing links, and
metadata) without touching the filesystem. `search()`, `get_all()`, and
`find_linked_notes()` all use this. `_index_note()` and `update()` store
the rendered markdown body (via `frontmatter.loads(markdown).content`) so
DB content matches the file exactly — `get()` and DB-backed paths return
identical `content`.

### Robust `rebuild_index_if_needed()`

Replaced count comparison with set diff of DB IDs vs file stems to catch
simultaneous add+delete (where counts match but the index is wrong).

### Housekeeping

- `init_db()` return type corrected from `-> None` to `-> Engine`
- Removed deprecated `sqlalchemy.ext.declarative` import (shadowed
  `sqlalchemy.orm` import; deprecated since SQLAlchemy 1.4)
- Removed unused imports (`create_engine`, `Session`, `Base`) from
  `note_repository.py`

## Test plan

23 new tests in `tests/test_note_repository.py`, all passing:

- `test_wal_mode_enabled` — queries `PRAGMA journal_mode` directly
- `test_create_leaves_no_tmp_file` — no `.md.tmp` after create
- `test_update_leaves_no_tmp_file` — no `.md.tmp` after update
- `test_cache_hit_after_get` — repeated get() returns consistent result
- `test_cache_invalidated_on_update` — fresh data visible after update
- `test_cache_invalidated_on_delete` — get() returns None after delete
- `test_cache_returns_independent_copy` — mutating returned note doesn't corrupt cache
- `test_search_returns_correct_content_and_tags` — DB reconstruction correct
- `test_search_returns_links` — outgoing links reconstructed correctly
- `test_rebuild_index_if_needed_detects_missing_file` — file removed, DB not
- `test_rebuild_index_if_needed_detects_extra_file` — file present, DB missing
- `test_metadata_round_trips_through_search` — metadata consistent via search()
- `test_metadata_round_trips_through_get_all` — metadata consistent via get_all()
- `test_metadata_round_trips_through_find_linked_notes` — metadata consistent via find_linked_notes()
- `test_note_without_metadata_returns_empty_dict` — NULL metadata_json returns {}
- `test_metadata_with_datetime_round_trips` — datetime.date/datetime serialize to ISO strings
- `test_search_content_matches_get_content` — DB content matches file content exactly
~~~

---

## Why not include pyproject.toml and uv.lock

Neither file changed under the correct development workflow. Both are
artifacts of a setup mistake, not the code changes.

**`pyproject.toml`** — pytest was already declared in
`[project.optional-dependencies] dev`. The change appeared because
`uv add --dev pytest` was run instead of `uv sync --extra dev`, which
added a redundant `[dependency-groups]` section. Using the venv correctly
from the start (`uv sync --extra dev`) installs pytest without touching
`pyproject.toml`. **Do not include this change.**

**`uv.lock`** — the lock file was regenerated entirely because
`uv run --python 3.13` was used, which detected a Python version mismatch
with the existing `.venv` and tore it down to rebuild it, re-resolving all
700+ packages. Using `uv sync --extra dev` against the already-correct
`.venv` (Python 3.13) does not regenerate the lock file at all.
**Do not include this change.**

**To submit the PR cleanly**, copy only the three changed source files to
your checkout of the original repo, or cherry-pick just those file changes.

# Fix 1 — Unused imports
gh api repos/BDKingDev/parazettle-mcp/pulls/1/comments \
  -f body="Fixed — removed \`create_engine\`, \`Session\`, and \`Base\` from the import block." \
  -F in_reply_to=2997571060

# Fix 2 — Mutable cache
gh api repos/BDKingDev/parazettle-mcp/pulls/1/comments \
  -f body="Good catch. \`_cache_get()\` now returns \`note.model_copy(deep=True)\`, and \`get()\` also returns a copy on cache-miss (so the stored instance is never leaked). Added a test that mutates a returned note and verifies subsequent \`get()\` calls are unaffected." \
  -F in_reply_to=2997571092

# Fix 3 — DB content inconsistency (_index_note)
gh api repos/BDKingDev/parazettle-mcp/pulls/1/comments \
  -f body="Fixed. \`_index_note()\` now accepts an optional \`rendered_content\` parameter. \`create()\` passes \`frontmatter.loads(markdown).content\` so the DB stores the same body that was written to the file (including the \`# Title\` heading and \`## Links\` section). The \`rebuild_index()\` path is unaffected since \`_parse_note_from_markdown()\` already returns the rendered body." \
  -F in_reply_to=2997571115

# Fix 4 — DB content inconsistency (update)
gh api repos/BDKingDev/parazettle-mcp/pulls/1/comments \
  -f body="Fixed — \`update()\` now computes \`rendered_body = frontmatter.loads(markdown).content\` after \`_note_to_markdown()\` and stores that in \`db_note.content\`, consistent with the file. Added \`test_search_content_matches_get_content\` to verify." \
  -F in_reply_to=2997571140

# Fix 5 — json.dumps TypeError (_index_note)
gh api repos/BDKingDev/parazettle-mcp/pulls/1/comments \
  -f body="Fixed. Added a \`_json_default()\` handler that converts \`datetime.date\` and \`datetime.datetime\` to ISO strings. Both \`_index_note()\` and \`update()\` now use \`json.dumps(note.metadata, default=_json_default)\`. Added \`test_metadata_with_datetime_round_trips\` verifying round-trip through search." \
  -F in_reply_to=2997571175

# Fix 6 — json.dumps TypeError (update)
gh api repos/BDKingDev/parazettle-mcp/pulls/1/comments \
  -f body="Same fix applied here — uses the shared \`_json_default()\` handler." \
  -F in_reply_to=2997571198

# Fix 7 — Temp file cleanup (create)
gh api repos/BDKingDev/parazettle-mcp/pulls/1/comments \
  -f body="Fixed. Added a \`finally\` block that calls \`tmp_path.unlink()\` if the file still exists (wrapped in \`try/except OSError\` to avoid masking the original error). On success \`replace()\` already removes \`tmp_path\`, so the \`finally\` is a no-op in the happy path." \
  -F in_reply_to=2997571215

# Fix 8 — Temp file cleanup (update)
gh api repos/BDKingDev/parazettle-mcp/pulls/1/comments \
  -f body="Same \`finally\` cleanup applied here." \
  -F in_reply_to=2997571260

# Fix 9 — Connection-scoped PRAGMAs
gh api repos/BDKingDev/parazettle-mcp/pulls/1/comments \
  -f body="Good point — \`cache_size\` and \`busy_timeout\` are connection-scoped unlike WAL which is persistent. Moved them to a \`@event.listens_for(engine, \"connect\")\` handler so they apply to every new connection. WAL and the migration remain as one-time operations." \
  -F in_reply_to=2997571301