# Release checklist

Copy this into the release PR description and fill it in. Automated tests run in CI; the
rows below cover what they cannot (a real Jupyter UI and a real Spark Connect server).

**Version:** `x.y.z`  **Tester:**  **Date:**  **Spark / Jupyter versions:**

## Automated (CI)
- [ ] CI green on the release PR (link the run): 
- [ ] Changelog `[Unreleased]` renamed to `[x.y.z] - YYYY-MM-DD`
- [ ] `__version__` bumped in `src/nbboost/__init__.py`

## Manual – JupyterLab against the Spark Connect cluster
Re-run every cell after upgrading; old outputs embed old widget code.

| Check | Result | Evidence (screenshot / note) |
|---|---|---|
| `nbboost.load()` runs without errors | | |
| `display(spark_df)` and `df.display()` render the table | | |
| Sort, filter, cell / row / column / select-all, copy | | |
| Create a chart, re-run the cell: chart, filters and sort persist | | |
| Column profile side panel opens for a selected column | | |
| `%sql` / `%%sql` runs multiple statements and shows the last result | | |
| `%fs ls`, `%md`, `%sh` work | | |
| Bad SQL shows the short error box; stack trace expands | | |
| A slow query shows the progress bar, then "Command took …" | | |

## Release
- [ ] Release PR merged into `main`
- [ ] Tag `vx.y.z` pushed on the merge commit (triggers the Release workflow)
- [ ] GitHub Release has the test report, `test-results.xml`, `coverage.xml` and dist files attached
