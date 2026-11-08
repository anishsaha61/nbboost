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

To enable it in every kernel, copy `examples/50-nbboost.py` to
`~/.ipython/profile_default/startup/`.

`nbboost.load(namespace=True, methods=True, sql_magic=True)` lets you opt out of parts.
If you use the `ipython-sql` extension, pass `sql_magic=False` to avoid a `%sql` clash.

## Known limits

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
