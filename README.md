# nbboost

Supercharge Jupyter notebooks: an interactive, spreadsheet-style table viewer with
charts, filters and column profiling for Spark and pandas DataFrames, a `%sql` magic,
and `df.display()` — with more on the way.

> Independent open-source project. **Not affiliated with, endorsed by, or sponsored by Databricks.**

## Features

- **Interactive table**: virtualized rows, sort, per-column filters, cell/row/column/range selection, copy.
- **Visualizations**: bar, horizontal bar, line, area, combo, scatter, pie, donut, heatmap, box, histogram, funnel, counter, word cloud.
- **Data profile**: summary tab plus a per-column profile side panel.
- **Persistence**: charts, filters and sort order survive re-running a cell (and page refresh), and reflect the latest data.
- **`%sql` / `%%sql` magic** for Spark (`--limit N|all`); result stored in `_sql_df`.
- **`df.display()`** on Spark (classic and Connect), pandas and pandas-on-Spark DataFrames.
- **`nbutils.fs`** and **`%fs`**: `ls` (shown as a table), `head`, `cp`, `mv`, `rm`, `mkdirs`, `put` on the local file system.
- **`%md`** renders Markdown; **`%sh`** runs shell commands with streamed output and exit code.
- **Cleaner Spark errors**: a short red box with the error class and message; the Python/JVM stack trace is folded behind "Show stack trace".
- **Run timing and Spark Jobs**: "Command took 2.3s" after cells that run >= 0.5s, and a collapsible **Spark Jobs** block for slow Spark Connect queries: a live overall bar in the header, and per-query, per-stage progress when expanded. It stays (collapsed) after the cell finishes.
- **`nbutils.widgets`**: text, dropdown, combobox and multiselect inputs; `%%sql` binds `:name` to widget values.
- **`nbutils.notebook.run()` / `exit()`**: run another notebook in a fresh kernel with arguments and get its result back.
- **`nbutils.secrets`**: read credentials from environment variables or a private JSON file; values are hidden in `repr`.
- **`nbutils.data.summarize(df)`**: the table with its Data profile tab already open.
- **Query plan viewer**: `nbutils.data.explain(df)` or `%%sql --explain` shows the plan as a collapsible tree, with shuffles, broadcasts and expensive joins tagged.
- **JupyterLab extension** (installed automatically with the package):
  - a hover bar between cells to insert **+ Code**, **+ Markdown** or **+ SQL** (`%%sql`) cells;
  - a ▶ run button on every cell with **Run cell / Run all above / Run this and all below**;
  - a labelled **Run all** button and a cleaner toolbar;
  - rounded, quieter cell styling that follows the light or dark theme.
- **Catalog autocomplete**: Tab completes databases, tables and columns in `%sql` cells, `spark.table("…")` and `spark.sql("…")`; `nbutils.catalog` lists them.

## Install

```bash
pip install nbboost            # core
pip install "nbboost[spark]"   # + pyspark
pip install "nbboost[all]"     # + pyspark, pandas, ipywidgets (widgets), nbclient + ipykernel (notebook.run)
```

Until the first PyPI release: `pip install git+https://github.com/anishsaha61/nbboost.git`.

## Usage

```python
import nbboost
nbboost.load()          # registers display, show_html, df.display() and %sql

display(df)             # or df.display()
```

```sql
%%sql
select * from my_table
```

```
%fs ls /home/jovyan/data
%fs cp -r data backup
%%md
## Notes
%%sh
ls -la && echo done
```

```python
nbutils.fs.ls("/home/jovyan/data")
nbutils.fs.put("/tmp/a.txt", "hello", overwrite=True)
nbutils.fs.head("/tmp/a.txt")
```

### Widgets and SQL parameters

```python
nbutils.widgets.dropdown("year", "2026", ["2024", "2025", "2026"], "Year")
nbutils.widgets.text("country", "IN")
nbutils.widgets.get("year")          # "2026" -- always a string
nbutils.widgets.show()               # all widgets in one row
```

```sql
%%sql
select * from jobs where year = :year and country = :country
```

Re-running the cell that defines a widget keeps the value you picked. Without `ipywidgets` the
widget is shown as a read-only label.

### Running notebooks from notebooks

```python
result = nbutils.notebook.run("ingest.ipynb", timeout_seconds=600,
                              arguments={"date": "2026-11-09"},
                              output_path="runs/ingest-2026-11-09.ipynb")   # optional: keep the executed copy
```

```python
# inside ingest.ipynb
d = nbutils.widgets.get("date")
...
nbutils.notebook.exit(f"rows={n}")   # stops here and returns the string
```

The child runs in a **new kernel** started in its own folder: it doesn't share variables with the
caller and needs its own `spark` session (an IPython startup file that creates one is the easy way).
A failure raises `NotebookRunError` naming the cell and error; going past `timeout_seconds` stops the
child kernel and raises `TimeoutError`.

### Secrets

```python
key = nbutils.secrets.get("gemini", "api-key")
```

Looked up as the environment variable `NBB_SECRET_GEMINI_API_KEY`, then in
`~/.nbboost/secrets.json` (`{"gemini": {"api-key": "..."}}`, or set `NBBOOST_SECRETS_FILE`; keep it
`chmod 600`). `nbutils.secrets.list("gemini")` and `listScopes()` show names only.
The value's `repr` is `'[REDACTED]'`, but `print(key)` still prints it: Jupyter does not scrub output.

### Data and plans

```python
nbutils.data.summarize(df)              # profile tab open
nbutils.data.explain(df)                # or explain(df, mode="formatted")
nbutils.data.explain("select ...")      # SQL is explained, not executed
nbutils.catalog.databases(); nbutils.catalog.tables("jobs_ingest_prod"); nbutils.catalog.columns("jobs_ingest_prod.jobs_raw")
```

```sql
%%sql --explain formatted
select * from jobs_ingest_prod.jobs_raw where company = 'Citi'
```

To enable it in every kernel, copy `examples/50-nbboost.py` to
`~/.ipython/profile_default/startup/`.

`nbboost.load()` accepts `namespace`, `methods`, `sql_magic`, `magics_`, `errors_`, `timing`, `progress` and `autocomplete`
(all `True` by default) to opt out of parts. Note `%sh` replaces IPython's built-in `%sh`; use `magics_=False` to keep it.
If you use the `ipython-sql` extension, pass `sql_magic=False` to avoid a `%sql` clash.

### JupyterLab extension

Installing nbboost into the environment that runs JupyterLab adds the extension; reload the browser
tab (restart JupyterLab if it was already running). Commands are also in the command palette:
*Insert SQL Cell Below/Above* and *Insert Markdown Cell Below*. To turn it off:
`jupyter labextension disable nbboost`.

## Known limits

- `nbutils.fs` works on the notebook machine's local disk only (no `dbfs:`, S3 or HDFS paths). `rm` refuses `/` and your home directory.
- The progress bar needs Spark Connect (`pyspark.sql.connect` sessions); classic Spark shows timing only.
- Widgets live in the kernel: they reset when the kernel restarts, and appear in the cell that creates them (there is no fixed bar at the top of the notebook).
- `notebook.run` starts a new kernel per call, so expect a few seconds of start-up plus Spark session creation.
- Autocomplete waits at most 1.5 s for the catalog; names are cached for 60 s and refreshed after `CREATE`/`DROP`/`ALTER`/`USE`. Use `nbutils.catalog.refresh()` to force it.

- Output HTML embeds the widget code, so previously rendered outputs keep their old
  version until the cell is re-run.
- Default display limit is 10,000 rows (`display(df, limit=...)`).

## Development

```bash
pip install -e ".[test]"
python -m playwright install chromium   # only for the browser smoke tests
pytest
```

## License

MIT — see [LICENSE](LICENSE).

### JupyterLab extension

The TypeScript source is in `labextension/`; the built files are committed in
`src/nbboost/labextension/` so that installing from git needs no Node.js. After changing the source:

```bash
pip install "jupyterlab>=4,<5"
cd labextension && npm ci && npm run build      # then commit src/nbboost/labextension
pip install .                                   # a regular install puts it in share/jupyter/labextensions
pytest -m jupyterlab                            # end-to-end test in a real JupyterLab
```

CI fails if the committed build doesn't match the source.
