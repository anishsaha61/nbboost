import json
import os

import pytest

from nbboost.secrets import FILE_ENV, Secret, Secrets


@pytest.fixture
def sec(tmp_path, monkeypatch):
    f = tmp_path / "secrets.json"
    f.write_text(json.dumps({"db": {"password": "p@ss", "user": "anish"}, "gemini": {"api-key": "file-key"}}))
    os.chmod(f, 0o600)
    monkeypatch.setenv(FILE_ENV, str(f))
    for k in list(os.environ):
        if k.startswith("NBB_SECRET_"):
            monkeypatch.delenv(k)
    return Secrets()


def test_get_from_file(sec):
    v = sec.get("db", "password")
    assert v == "p@ss" and isinstance(v, Secret)


def test_env_wins_and_names_are_normalised(sec, monkeypatch):
    monkeypatch.setenv("NBB_SECRET_GEMINI_API_KEY", "env-key")
    assert sec.get("gemini", "api-key") == "env-key"


def test_repr_is_redacted_but_value_usable(sec):
    v = sec.get("db", "password")
    assert repr(v) == "'[REDACTED]'" and "p@ss" not in repr([v])
    assert f"postgres://u:{v}@h" == "postgres://u:p@ss@h"


def test_missing_secret_message_has_no_values(sec):
    with pytest.raises(KeyError) as e:
        sec.get("db", "nope")
    msg = str(e.value)
    assert "NBB_SECRET_DB_NOPE" in msg and "p@ss" not in msg


def test_list_and_scopes(sec, monkeypatch):
    monkeypatch.setenv("NBB_SECRET_DB_TOKEN", "t")
    assert [m.key for m in sec.list("db")] == ["password", "token", "user"]
    assert [s.name for s in sec.listScopes()] == ["db", "gemini"]


def test_world_readable_file_warns(sec, tmp_path):
    os.chmod(tmp_path / "secrets.json", 0o644)
    with pytest.warns(UserWarning, match="chmod 600"):
        sec.get("db", "user")


def test_no_file_at_all(tmp_path, monkeypatch):
    monkeypatch.setenv(FILE_ENV, str(tmp_path / "none.json"))
    s = Secrets()
    assert s.listScopes() == [] and s.list("x") == []
    with pytest.raises(KeyError):
        s.get("x", "y")
