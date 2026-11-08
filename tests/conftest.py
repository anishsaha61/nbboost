import pytest

import nbboost._display as disp


@pytest.fixture
def shown(monkeypatch):
    """Collect everything the library would send to IPython's display()."""
    out = []
    monkeypatch.setattr(disp, "_ipy_display", lambda obj, **kw: out.append(obj))
    return out


def html_of(item):
    return item.data if hasattr(item, "data") else str(item)
