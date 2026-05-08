# wagtail-comments-report

A Wagtail admin report that lists every page comment across the site in one
place, with filters and dedup.

## Why

Wagtail puts comments inside each page's edit view. There is no built-in
way to scan all open comments across the whole site, which makes it easy to
forget about open threads on pages you rarely touch.

This package adds a **Comments** entry under **Reports** in the Wagtail
admin showing:

- Comment text, page, author, date, and Open / Resolved status, ordered
  newest first.
- Filters: author, page, date range, and a tri-state Status (Open /
  Resolved / All) that defaults to **Open** so editors land on
  outstanding comments first.
- CSV / XLSX export (provided by Wagtail's `SpreadsheetExportMixin`).
- Automatic deduplication of `Comment` rows that Wagtail can stash at
  the same `(page, user, contentpath)` as a side effect of revision
  saves — only the most recent row per logical comment is shown.

## Install

```bash
pip install wagtail-comments-report
```

Add the app to `INSTALLED_APPS` (after `wagtail.admin` so the report
URLs and menu hooks are picked up):

```python
INSTALLED_APPS = [
    # ...
    "wagtail.admin",
    "wagtail",
    "wagtail_comments_report",
    # ...
]
```

No migrations are required — the report reads `wagtail.models.Comment`
directly.

## Configuration

None required. The report appears under **Reports > Comments** in the
Wagtail admin to any user with admin access.

The status filter defaults to **Open**. To link directly to all
comments (or only resolved), pass `?status=all` or `?status=resolved`
on the URL.

## Compatibility

The package itself has no hard pins on Django or Wagtail — `pip` will
install on whatever you've got. What's actively **tested** in CI (defined
in `pyproject.toml` under `[tool.hatch.envs.hatch-test]`):

- Python 3.10, 3.11, 3.12, 3.13, 3.14
- Django 5.2 and 6.0
- Wagtail 6.4+ (with Django 5.2) and Wagtail 7.x (with Django 5.2 or 6.0)
- Postgres or SQLite (the dedup uses portable `Max("id")` aggregation, not `DISTINCT ON`)

Combinations not exercised: Django 6 needs Python 3.12+, and Wagtail 6
doesn't run on Django 6. The matrix excludes those.

It will probably work on older Wagtail/Django too — those just aren't in
the matrix. If you find a real incompatibility, open an issue or a PR
with a CI matrix entry.

## Development

The test matrix is managed by [Hatch](https://hatch.pypa.io/) and
defined in `pyproject.toml` under `[tool.hatch.envs.hatch-test]`. The
fastest way to drive it is with [uv](https://docs.astral.sh/uv/):

```bash
# run the full matrix (note --all; without it hatch only runs ONE env)
uvx hatch test --all

# run one cell
uvx hatch test --include "python=3.13" --include "wagtail=7"

# filter pytest across the whole matrix
uvx hatch test --all -k test_report_dedupes

# lint
uvx hatch fmt --check
```

If you'd rather skip the matrix and just run pytest in one
interpreter:

```bash
uv sync --extra test
uv run pytest src/
```
