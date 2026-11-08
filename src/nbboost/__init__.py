"""nbboost: power-ups for Jupyter notebooks (interactive tables and charts, %sql, %fs, %md, %sh, df.display())."""
from ._display import display, show_html
from ._shell import install_methods, load
from .nbutils import nbutils

__version__ = "0.1.0"
__all__ = ["display", "show_html", "install_methods", "load", "nbutils", "__version__"]
