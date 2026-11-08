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
- **Run timing and progress**: "Command took 2.3s" after cells that run >= 0.5s, and a live progress bar for slow Spark Connect queries.

## Install

```bash
pip install nbboost            # core
pip install "nbboost[spark]"   # + pyspark
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

To enable it in every kernel, copy `examples/50-nbboost.py` to
`~/.ipython/profile_default/startup/`.

`nbboost.load()` accepts `namespace`, `methods`, `sql_magic`, `magics_`, `errors_`, `timing` and `progress`
(all `True` by default) to opt out of parts. Note `%sh` replaces IPython's built-in `%sh`; use `magics_=False` to keep it.
If you use the `ipython-sql` extension, pass `sql_magic=False` to avoid a `%sql` clash.

## Known limits

- `nbutils.fs` works on the notebook machine's local disk only (no `dbfs:`, S3 or HDFS paths). `rm` refuses `/` and your home directory.
- The progress bar needs Spark Connect (`pyspark.sql.connect` sessions); classic Spark shows timing only.

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
