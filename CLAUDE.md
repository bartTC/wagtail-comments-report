# wagtail-comments-report — Claude notes

This package was extracted from a larger Wagtail/Django project into a
reusable third-party app. The notes below capture the things that
weren't obvious from the code and saved time the second time around.

## What the package does

A Wagtail admin **Reports → Comments** view that lists every page
comment site-wide, with filters. The whole app is just one view,
one filterset, one template, and one `wagtail_hooks` registration.

## Repo layout

```
src/
├── wagtail_comments_report/
│   ├── __init__.py
│   ├── apps.py
│   ├── views.py             # CommentsReportView + CommentsReportFilterSet
│   ├── wagtail_hooks.py     # URL + reports menu registration
│   └── templates/wagtail_comments_report/comments_report_results.html
└── tests/
    ├── conftest.py          # root_page / page / admin_user / admin_client
    ├── settings.py          # minimal Wagtail test settings (sqlite :memory:)
    ├── urls.py              # wagtailadmin urls only
    └── test_views.py
```

`pyproject.toml` puts `pythonpath = ["src"]` and `testpaths =
["src/tests"]`, so `pytest` from the repo root just works.

## Things to know about Wagtail's `Comment` model

Wagtail comments live in `wagtail.models.Comment` (defined in
`wagtail/models/pages.py`). Each comment is anchored to a page via
`page` (ParentalKey) and to a position inside that page via
`contentpath`, e.g. `"title"` for a plain field or
`"content.<streamfield-uuid>.items.<block-uuid>"` for a StreamField
position.

Useful fields:

- `page`, `user`, `text`, `contentpath`
- `created_at`, `updated_at`
- `resolved_at` (nullable — `NULL` means open) and `resolved_by`
- `revision_created` (FK to `Revision` — the revision that introduced
  this comment)

## The dedup story (important)

Wagtail can persist **multiple `Comment` rows at the same
`(page, user, contentpath)`** as a side effect of the page-edit form's
revision/save flow. In the production database I extracted this from,
one position had **46 identical rows**. Likely sources:

- The React layer losing a server-assigned comment ID and re-submitting
  it as new on the next save → INSERT instead of UPDATE.
- "Replace current draft from history": modelcluster recreates comment
  rows from the revision payload when the originals are no longer in
  `wagtail_admin_comments`.
- Bulk imports / migrations rerun.

Wagtail's _editor_ hides this from you because the React UI groups by
`contentpath`. The DB does not.

**Wagtail's `CommentFormSet.__init__` does not dedup.** It only filters
out comments whose `contentpath` no longer resolves to a real
field/block on the current page (via `Comment.has_valid_contentpath`).
A flat report would otherwise show all 46 — so this package collapses
them in `CommentsReportView.get_queryset()`:

```python
latest_per_position_ids = (
    Comment.objects.values("page_id", "user_id", "contentpath")
    .annotate(latest_id=Max("id"))
    .values_list("latest_id", flat=True)
)
self.queryset = (
    Comment.objects.filter(id__in=latest_per_position_ids)
    .select_related("page", "user", "resolved_by")
    .order_by("-created_at")
)
```

The original implementation used Postgres `DISTINCT ON
(page_id, user_id, contentpath) ... ORDER BY ..., created_at DESC`. For
this package it was rewritten to a portable `Max("id")` GROUP BY so the
test suite can run on SQLite. Auto-increment monotonicity makes
"max id == latest" reliable in practice.

If users want to _see_ the dupes, document it in the README as a
deliberate choice — don't expose a switch unless someone asks.

## Wagtail report plumbing — quick reference

A custom Wagtail admin report needs four pieces:

1. **A view** subclassing `wagtail.admin.views.reports.base.ReportView`
   (or `PageReportView` if the model is `Page`). Set:
   - `results_template_name`
   - `page_title`, `header_icon`
   - `filterset_class`
   - `index_url_name` and `index_results_url_name` (must match
     `register_admin_urls` names below)
   - `export_headings` and `list_export` for CSV/XLSX
2. **A filter set** subclassing
   `wagtail.admin.filters.WagtailFilterSet`. `Meta.fields` lists
   field names; declared filters at the class level override
   auto-generated ones. The form widgets get Wagtail-styled by
   `WagtailFilterSet.filter_for_lookup` automatically.
3. **A results template** extending
   `wagtailadmin/reports/base_report_results.html` and overriding the
   `{% block results %}` (table) and
   `{% block no_results_message %}` blocks. Use the
   `{% load wagtailadmin_tags %}` helpers like `human_readable_date`
   and `{% status %}`.
4. **`wagtail_hooks.py`** registering:
   - `register_admin_urls` returning two paths: the index and the
     `results_only=True` results endpoint. Wagtail's admin JS fetches
     the latter to swap in just the table fragment when filters
     change — no full reload, but it's Wagtail's own AJAX, not HTMX.
   - `register_reports_menu_item` for the menu entry.

The URL names you give in `register_admin_urls` are flat (no Django
URL namespace). Pick something prefixed enough to avoid clashes with
host projects.

## Defaulting a filter (Status → Open)

`django-filter` has no first-class "default value" hook for filters.
The trick is to override `get_filterset_kwargs` on the view and inject
a default into the `data` dict when the URL has no value for that
filter:

```python
def get_filterset_kwargs(self):
    kwargs = super().get_filterset_kwargs()
    data = kwargs.get("data")
    if data is not None and "status" not in data:
        mutable = data.copy()
        mutable["status"] = COMMENT_STATUS_OPEN
        kwargs["data"] = mutable
    return kwargs
```

A `BooleanFilter` ("Yes/No/All") _cannot_ support "default to No,
allow All" cleanly because "All" submits empty and you can't tell
"empty because user picked All" from "empty because no submit". A
`ChoiceFilter` with explicit `[(open, ...), (resolved, ...), (all, ...)]`
choices does — that's why this package uses it.

## Testing gotchas

- **`@pytest.mark.django_db`** on every test that touches the DB.
- **Comment dedup means tests must use distinct contentpaths.** If
  two test comments share `contentpath="title"`, dedup will drop one
  and the test will fail in surprising ways. Use `"a"`, `"b"`,
  `"content.block-a"`, etc.
- **String matching across the whole HTML body is brittle.** Words
  like `"newer"` / `"older"` appear in chrome (filter labels, dropdown
  options). For ordering assertions, regex out the
  `<table class="listing">` block and search inside that.
- **`text="hello"` etc. in tests** — pick distinctive markers
  (`commentEARLIER`, `from-admin`) so a stray match in chrome doesn't
  pass when the row actually isn't rendered.
- **No CSV/SQLite fixtures here.** Unlike the parent project, this
  package's tests use `:memory:` SQLite and no CSV sync. The
  `root_page` fixture in `tests/conftest.py` creates the wagtail tree
  root and the default `Site`.
- **Wagtail's `Page.add_root` vs `add_child`:** the root must exist
  before any child is added. The fixture handles this with an
  existence check so multiple tests sharing the DB don't blow up.

## Coding conventions

- Type hints on everything (`from __future__ import annotations` is
  not used — Python 3.10+ string-quoted forward refs and `TYPE_CHECKING`
  imports are fine).
- No inline imports unless there's a circular-dep reason.
- `gettext_lazy as _` for any human-visible string.
- Don't introduce extra abstractions for "future flexibility" — the
  whole app is intentionally one view.
