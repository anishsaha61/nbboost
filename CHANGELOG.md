# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/), versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- JupyterLab extension, installed with the package:
  - hover bar between cells to insert Code, Markdown or SQL (`%%sql`) cells;
  - per-cell run button with Run cell / Run all above / Run this and all below;
  - labelled Run all button and a cleaner notebook toolbar;
  - refreshed cell styling for light and dark themes;
  - command-palette entries for inserting SQL and Markdown cells.

## [0.3.0] - 2026-11-09

### Added
- `nbutils.widgets` (text, dropdown, combobox, multiselect) with `:name` SQL parameters in `%%sql`.
- `nbutils.notebook.run()` / `exit()`: run a notebook in a fresh kernel with arguments, a timeout and an optional saved output copy.
- `nbutils.secrets` from environment variables or `~/.nbboost/secrets.json`, with redacted `repr`.
- `nbutils.data.summarize(df)` opens the Data profile tab.
- Query plan viewer: `nbutils.data.explain(df_or_sql)` and `%%sql --explain [mode]` show a collapsible, annotated tree.
- Catalog autocomplete for `%sql`, `spark.table()` and `spark.sql()`, plus `nbutils.catalog` listings; `load(autocomplete=False)` turns it off.
- Install extras: `widgets`, `notebook`, `all`.

### Changed
- Requires IPython 8.6 or later (for the completion API).
- `%%sql` rejects unknown options instead of ignoring them.
- The Spark Connect progress bar is now a collapsible "Spark Jobs" block: one per cell, with an overall bar in the header and per-query, per-stage progress when expanded. It stays (collapsed) after the cell finishes instead of disappearing, and keeps its open/closed state while it updates. Stages that were never reported complete are dimmed.

### Fixed
- The error box no longer triggers PySpark's `FutureWarning: Deprecated in 4.0.0, use getCondition instead`.

## [0.2.1] - 2026-11-08

### Fixed
- Spark errors no longer also print PySpark's huge JSON error log (message + JVM stack trace) in red; only the short error box is shown. Turn off with `load(errors_=False)`.

## [0.2.0] - 2026-11-08

### Added
- `nbutils.fs` and `%fs` / `%%fs` (ls, head, cp, mv, rm, mkdirs, put).
- `%md` and `%sh` magics.
- Collapsible Spark error box replacing long tracebacks.
- "Command took" timing line and live Spark Connect progress bar.
- `nbboost.load()` options: `magics_`, `errors_`, `timing`, `progress`.

## 0.1.0 - 2026-11-08 (internal, never tagged)

### Added
- Interactive table viewer, charts, filters, column profiling and persistence.
- `%sql` / `%%sql` magic and `df.display()`.

[Unreleased]: https://github.com/anishsaha61/nbboost/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/anishsaha61/nbboost/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/anishsaha61/nbboost/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/anishsaha61/nbboost/releases/tag/v0.2.0
