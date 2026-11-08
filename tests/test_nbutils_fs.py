import pytest

from nbboost.nbutils import FileList, fs, nbutils


def test_put_head_ls(tmp_path):
    f = tmp_path / "d" / "a.txt"
    assert fs.put(str(f), "hello") is True
    assert fs.head(str(f)) == "hello"
    assert fs.head(str(f), 2) == "he"
    items = fs.ls(str(tmp_path / "d"))
    assert isinstance(items, FileList) and [i.name for i in items] == ["a.txt"] and items[0].size == 5


def test_put_refuses_overwrite(tmp_path):
    f = str(tmp_path / "a.txt")
    fs.put(f, "1")
    with pytest.raises(FileExistsError):
        fs.put(f, "2")
    fs.put(f, "2", overwrite=True)
    assert fs.head(f) == "2"


def test_ls_marks_directories_and_renders_html(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "<b>.txt").write_text("x")
    items = fs.ls(str(tmp_path))
    assert [i.name for i in items] == ["<b>.txt", "sub/"]
    html = items._repr_html_()
    assert "<table" in html and "&lt;b&gt;.txt" in html and "<b>.txt" not in html


def test_empty_dir_html(tmp_path):
    assert "(empty)" in fs.ls(str(tmp_path))._repr_html_()


def test_cp_mv_rm(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("x")
    (tmp_path / "dir").mkdir()
    fs.cp(str(a), str(tmp_path / "dir"))
    assert (tmp_path / "dir" / "a.txt").exists()
    fs.mv(str(a), str(tmp_path / "b.txt"))
    assert not a.exists() and (tmp_path / "b.txt").exists()
    assert fs.rm(str(tmp_path / "b.txt")) is True
    assert fs.rm(str(tmp_path / "missing")) is False


def test_directory_ops_need_recurse(tmp_path):
    d = tmp_path / "d"
    fs.put(str(d / "x.txt"), "1")
    with pytest.raises(IsADirectoryError):
        fs.cp(str(d), str(tmp_path / "e"))
    with pytest.raises(IsADirectoryError):
        fs.rm(str(d))
    fs.cp(str(d), str(tmp_path / "e"), recurse=True)
    assert (tmp_path / "e" / "x.txt").exists()
    assert fs.rm(str(d), recurse=True) is True and not d.exists()


def test_rm_refuses_root_and_home():
    with pytest.raises(ValueError):
        fs.rm("/", recurse=True)
    with pytest.raises(ValueError):
        fs.rm("~", recurse=True)


def test_file_prefix_and_mkdirs(tmp_path):
    p = tmp_path / "m" / "n"
    assert fs.mkdirs("file:" + str(p)) and p.is_dir()


def test_namespace_object():
    assert nbutils.fs is fs
