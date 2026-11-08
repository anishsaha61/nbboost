import pytest
from IPython.core.interactiveshell import InteractiveShell

from nbboost import magics
from nbboost.nbutils import FileList


@pytest.fixture
def shown(monkeypatch):
    out = []
    monkeypatch.setattr(magics, "_ipy_display", lambda o, **k: out.append(o))
    return out


def test_fs_ls_returns_filelist(tmp_path):
    (tmp_path / "a").write_text("1")
    r = magics.run_fs(f"ls {tmp_path}")
    assert isinstance(r, FileList) and r[0].name == "a"


def test_fs_roundtrip_with_quoted_paths(tmp_path, capsys):
    d = tmp_path / "my dir"
    assert magics.run_fs(f'mkdirs "{d}"') is True
    assert magics.run_fs(f'put "{d}/f.txt" hello world') is True
    magics.run_fs(f'head "{d}/f.txt"')
    assert capsys.readouterr().out == "hello world\n"
    assert magics.run_fs(f'cp "{d}/f.txt" "{d}/g.txt"') is True
    assert magics.run_fs(f'mv "{d}/g.txt" "{d}/h.txt"') is True
    assert magics.run_fs(f'rm -r "{d}"') is True


def test_fs_errors_are_one_line_not_tracebacks(tmp_path, capsys):
    assert magics.run_fs(f"head {tmp_path}/nope") is None
    assert "FileNotFoundError" in capsys.readouterr().out


def test_fs_usage(capsys):
    magics.run_fs("")
    magics.run_fs("bogus")
    assert capsys.readouterr().out.count("usage:") == 2


def test_fs_cell_runs_each_line_and_displays_listings(tmp_path, shown):
    magics.fs_magic("", f"mkdirs {tmp_path}/x\n# comment\nls {tmp_path}")
    assert len(shown) == 1 and shown[0][0].name == "x/"


def test_md_renders_markdown(shown):
    magics.md_magic("", "# Title")
    assert shown[0].data == "# Title"
    magics.md_magic("**hi**")
    assert shown[1].data == "**hi**"


def test_sh_streams_output_and_reports_exit_code(capsys):
    magics.sh_magic("", "echo out; echo err 1>&2; exit 3")
    out = capsys.readouterr().out
    assert "out" in out and "err" in out and "[exit code 3]" in out


def test_sh_success_has_no_exit_line(capsys):
    magics.sh_magic("echo ok")
    assert capsys.readouterr().out == "ok\n"


def test_sh_empty_is_noop(capsys):
    magics.sh_magic("   ")
    assert capsys.readouterr().out == ""


def test_register_adds_magics_overriding_builtin_sh():
    ip = InteractiveShell.instance()
    magics.register(ip)
    for k in ("fs", "md", "sh"):
        assert k in ip.magics_manager.magics["line"] and k in ip.magics_manager.magics["cell"]
    assert ip.magics_manager.magics["cell"]["sh"] is magics.sh_magic or ip.magics_manager.magics["cell"]["sh"].__name__ == "sh_magic"
