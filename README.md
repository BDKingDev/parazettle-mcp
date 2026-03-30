# Parazettle MCP

A Zettelkasten knowledge management system extended with GTD and PARA workflow support, running as a Model Context Protocol (MCP) server. Fork of [zettelkasten-mcp](https://github.com/entanglr/zettelkasten-mcp).

## What is Parazettle?

Parazettle combines two complementary systems:

**Zettelkasten** — a graph-first knowledge method built on atomic notes, semantic links, and emergent insight. Each note is a discrete idea; meaning grows from the connections between notes.

**GTD + PARA** — a workflow layer on top of the same graph. Tasks, projects, and areas live as first-class note types with statuses, due dates, priorities, energy levels, and GTD contexts. The inbox → ready → active → done lifecycle applies to any note, not just tasks.

The result is one unified vault where knowledge notes and action items share the same ID format, tagging system, and semantic link graph.

---

## Features

- Create atomic notes with unique timestamp-based IDs
- Link notes with typed semantic relationships and inverse-link handling
- Tag notes for categorical organisation
- Search notes by content, tags, type, status, project, area, and more
- Dual storage: Markdown files (source of truth) + SQLite index (fast queries)
- WAL-mode SQLite with in-memory LRU cache for performance
- Tasks with status lifecycle, priorities, energy levels, GTD contexts, and due dates
- Projects linked to areas via the PARA hierarchy
- Today view and reminder surfacing
- Recurring tasks that auto-spawn the next instance on completion

---

## Note Types

| Type | Handle | Description |
| --- | --- | --- |
| Fleeting | `fleeting` | Quick, unprocessed captures |
| Literature | `literature` | Notes from reading material |
| Permanent | `permanent` | Well-formulated, evergreen notes |
| Structure | `structure` | Index/outline notes that organise others |
| Hub | `hub` | Entry points to major topic areas |
| Task | `task` | Atomic actionable item (GTD next action) |
| Project | `project` | Active outcome with a deadline (PARA) |
| Area | `area` | Ongoing responsibility with no end date (PARA) |

## Note Status

Applies to any note type. Tasks flow through the action lifecycle; knowledge notes use `evergreen` and `archived`.

| Status | Meaning |
| --- | --- |
| `inbox` | Captured but not yet triaged |
| `ready` | Triaged and waiting to be picked up |
| `scheduled` | Committed to a specific date |
| `active` | In progress |
| `waiting` | Waiting on someone or something |
| `someday` | Someday/maybe |
| `done` | Completed |
| `cancelled` | Cancelled |
| `archived` | Inactive but retrievable |
| `evergreen` | Mature, stable knowledge note |

## Link Types

### Semantic (knowledge) links

| Primary | Inverse | Relationship |
| --- | --- | --- |
| `reference` | `reference` | Simple reference (symmetric) |
| `extends` | `extended_by` | Builds upon another note |
| `refines` | `refined_by` | Clarifies or improves another |
| `contradicts` | `contradicted_by` | Presents opposing views |
| `questions` | `questioned_by` | Poses questions about another |
| `supports` | `supported_by` | Provides evidence for another |
| `related` | `related` | Generic relationship (symmetric) |

### Structural (PARA/GTD) links

| Primary | Inverse | Relationship |
| --- | --- | --- |
| `part_of` | `has_part` | Task/note belongs to a project or area |
| `blocks` | `blocked_by` | One task blocks another |

---

## Available MCP Tools

All tools are prefixed `pzk_`.

### Knowledge management

| Tool | Description |
| --- | --- |
| `pzk_create_note` | Create a note with title, content, type, and tags |
| `pzk_get_note` | Retrieve a note by ID or title |
| `pzk_update_note` | Update content, type, or tags |
| `pzk_delete_note` | Delete a note |
| `pzk_create_link` | Create a typed link between notes |
| `pzk_remove_link` | Remove a link |
| `pzk_search_notes` | Search by text, tags, type, status, project, area |
| `pzk_get_linked_notes` | Get notes linked to/from a note |
| `pzk_get_all_tags` | List all tags |
| `pzk_find_similar_notes` | Find notes similar to a given note |
| `pzk_find_central_notes` | Find most-connected notes |
| `pzk_find_orphaned_notes` | Find notes with no connections |
| `pzk_list_notes_by_date` | List notes by creation or update date |
| `pzk_rebuild_index` | Rebuild the SQLite index from Markdown files |

### Task management

| Tool | Description |
| --- | --- |
| `pzk_create_task` | Create a task with status, due date, priority, energy, context, reminders |
| `pzk_update_task_status` | Change a task's status; auto-spawns recurring instances |
| `pzk_get_tasks` | Query tasks by status, project, due date, priority |
| `pzk_get_todays_tasks` | Tasks due today + overdue, sorted by priority |
| `pzk_get_reminders` | Notes and tasks with `remind_at` ≤ today |

### Project and area management

| Tool | Description |
| --- | --- |
| `pzk_create_area` | Create an area note with optional review cadence |
| `pzk_list_areas` | List all areas |
| `pzk_create_project` | Create a project linked to an area |
| `pzk_list_projects` | List active projects sorted by deadline |
| `pzk_get_project` | Get a project with task status summary |
| `pzk_get_project_tasks` | Get all tasks for a project |

---

## Storage Architecture

1. **Markdown files** — source of truth. Human-readable, version-controllable, directly editable. Each note is `{id}.md` with YAML frontmatter.
2. **SQLite database** — indexing layer. WAL mode with in-memory LRU cache. Automatically rebuilt from files when needed via `pzk_rebuild_index`.

> **WAL sidecars:** Two small files (`.db-wal`, `.db-shm`) appear alongside the database while it is open. They are cleaned up automatically on shutdown and can be ignored.

---

## Installation

```bash
git clone https://github.com/BDKingDev/parazettle-mcp.git
cd parazettle-mcp

# Install dependencies (creates .venv with Python 3.13)
uv venv --python 3.13
uv sync --extra dev
```

### Connecting to Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "parazettle": {
      "command": "/absolute/path/to/parazettle-mcp/.venv/bin/python",
      "args": ["-m", "parazettle_mcp.main"],
      "env": {
        "ZETTELKASTEN_NOTES_DIR": "/absolute/path/to/parazettle-mcp/data/notes",
        "ZETTELKASTEN_DATABASE_PATH": "/absolute/path/to/parazettle-mcp/data/db/parazettle.db",
        "ZETTELKASTEN_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Connecting to Claude Code (CLI)

Add the same entry to `~/.claude.json` under `mcpServers`.

---

## Configuration

Copy `.env.example` to `.env` and set paths as needed. All paths can also be passed as environment variables or CLI flags:

```bash
python -m parazettle_mcp.main \
  --notes-dir ./data/notes \
  --database-path ./data/db/parazettle.db
```

---

## Running Tests

```bash
uv sync --extra dev
.venv/bin/python -m pytest tests/
```

See [`docs/mcp-testing-guide.md`](docs/mcp-testing-guide.md) for a full tool-by-tool testing walkthrough using the live MCP server.

---

## Documentation

| Document | Description |
| --- | --- |
| [`docs/para-gtd-guide.md`](docs/para-gtd-guide.md) | PARA/GTD workflow — areas, projects, tasks, today view, reminders |
| [`docs/mcp-testing-guide.md`](docs/mcp-testing-guide.md) | All 25 tools with example calls and expected output |
| [`docs/project-knowledge/user/link-types-in-zettelkasten-mcp-server.md`](docs/project-knowledge/user/link-types-in-zettelkasten-mcp-server.md) | Full link type reference |
| [`docs/prompts/system/system-prompt.md`](docs/prompts/system/system-prompt.md) | System prompt for Claude |
| [`docs/prompts/chat/`](docs/prompts/chat/) | Chat prompts for knowledge workflows |

---

## ⚠️ Important Notice

**USE AT YOUR OWN RISK**: This software is experimental and provided as-is without warranty. Always back up your notes regularly.

## Credits

Fork of [zettelkasten-mcp](https://github.com/entanglr/zettelkasten-mcp) by Peter J. Herrel. GTD/PARA extensions developed with Claude.

## License

MIT License
