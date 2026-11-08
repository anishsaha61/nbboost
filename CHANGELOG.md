# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/), versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- `nbutils.fs` and `%fs` / `%%fs` (ls, head, cp, mv, rm, mkdirs, put).
- `%md` and `%sh` magics.
- Collapsible Spark error box replacing long tracebacks.
- "Command took" timing line and live Spark Connect progress bar.
- `nbboost.load()` options: `magics_`, `errors_`, `timing`, `progress`.

## [0.1.0]

### Added
- Interactive table viewer, charts, filters, column profiling and persistence.
- `%sql` / `%%sql` magic and `df.display()`.
