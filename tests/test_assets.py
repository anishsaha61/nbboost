from nbboost._display import _asset


def test_assets_load_and_are_prefixed():
    css, js = _asset("nbboost.css"), _asset("nbboost.js")
    assert ".nbb-root" in css and "__ROOT_ID__" in js
    for text in (css, js):
        assert "dbx" not in text
        assert "databricks" not in text.lower()
