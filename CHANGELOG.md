# Changelog

All notable changes to **wagtail-comments-report** will be documented
in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] — 2026-05-08

### Added

- **Comments** entry under **Reports** in the Wagtail admin listing
  every page comment site-wide.
- Filters for author, page, date range, and a tri-state Status
  (Open / Resolved / All) that defaults to **Open** so editors land on
  outstanding comments first.
- Per-row Open / Resolved status flag and a link from each row to the
  page editor.
- CSV / XLSX export via Wagtail's `SpreadsheetExportMixin`.
- Automatic deduplication of `Comment` rows that Wagtail can persist
  at the same `(page, user, contentpath)` as a side effect of
  revision saves — only the most recent row per logical comment is
  shown. Implemented with cross-database-portable `Max("id")`
  aggregation, so the package works on both Postgres and SQLite.

[Unreleased]: https://github.com/bartTC/wagtail-comments-report/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/bartTC/wagtail-comments-report/releases/tag/v1.0.0
