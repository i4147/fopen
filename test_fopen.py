import os
import sys
import time
import importlib
from datetime import datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def wo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    if "fopen" in sys.modules:
        del sys.modules["fopen"]
    module = importlib.import_module("fopen")
    yield module
    monkeypatch.chdir(os.path.dirname(tmp_path))


def test_align_text_left(wo):
    assert wo.align_text("hi", "left") == "hi"


def test_align_text_center(wo):
    out = wo.align_text("hi", "center")
    assert out.strip() == "hi"


def test_colorize_bold(wo):
    out = wo.colorize("hi", bold=True)
    assert "\x1b[1m" in out and out.endswith("\x1b[0m")


def test_loop_progress_basic(wo):
    assert "1/2" in wo.loop_progress(1, 2)


def test_loop_progress_count(wo):
    assert wo.loop_progress(3, 10, mode_="count") == "⟳ [ 3/10 ]"


def test_parse_date_string(wo):
    dt = wo.parse_date_string("2024-01-02 03:04:05")
    assert dt.year == 2024 and dt.month == 1


def test_time_ago_recent(wo):
    assert wo.time_ago(datetime.now()) == "just now"


def test_time_ago_future(wo):
    out = wo.time_ago(datetime.now() + timedelta(minutes=5))
    assert out.startswith("in ")


def test_future_datetime_seconds(wo):
    out = wo.future_datetime(10, "s", with_date=True)
    assert len(out) > 0


def test_write_and_read_1d(wo):
    wo.w("mylist", [1, 2, 3], is2d=False)
    assert wo.r("mylist") == [1, 2, 3]


def test_write_and_read_2d(wo):
    wo.w("matrix", [[1, 2], [3, 4]], is2d=True)
    assert wo.r("matrix") == [[1, 2], [3, 4]]


def test_read_with_index(wo):
    wo.w("mylist", [10, 20, 30], is2d=False)
    assert wo.r("mylist", index=1) == 20


def test_read_missing_returns_default(wo):
    assert wo.r("nope", default=[]) == []


def test_append_1d(wo):
    wo.w("log", [1], is2d=False)
    wo.a("log", [2, 3], is2d=False)
    assert wo.r("log") == [1, 2, 3]


def test_append_2d(wo):
    wo.w("grid", [[1, 2]], is2d=True)
    wo.a("grid", [[3, 4]], is2d=True)
    assert wo.r("grid") == [[1, 2], [3, 4]]


def test_delete_1d_all(wo):
    wo.w("nums", [1, 2, 3, 4], is2d=False)
    removed, remaining = wo.d("nums", del_list=[2, 4], index=None)
    assert removed == 2
    assert remaining == [1, 3]


def test_delete_2d_all(wo):
    wo.w("rows", [["a", 1], ["b", 2], ["c", 3]], is2d=True)
    removed, remaining = wo.d("rows", del_list=["b"], index=[0])
    assert removed == 1
    assert ["b", 2] not in remaining


def test_delete_auto_trim(wo):
    wo.w("trim", [1, 2, 3, 4, 5], is2d=False)
    removed, remaining = wo.d("trim", del_list=[0], auto_trim_len=3)
    assert remaining == [3, 4, 5]


def test_remove_file(wo, capsys):
    wo.w("tmpfile", [1], is2d=False)
    wo.remove("tmpfile", display=False)
    assert "tmpfile" not in wo.listdir(display=False)


def test_listdir_contains_file(wo):
    wo.w("listed", [1], is2d=False)
    assert "listed" in wo.listdir(display=False)


def test_info_returns_metadata(wo):
    wo.w("stats", [1, 2, 3], is2d=False)
    payload = wo.info("stats", display=False)
    assert payload["Structure"] == "1D"
    assert payload["Total Entries"] == 3


def test_hide_and_unhide(wo, tmp_path):
    wo.w("hiddenfile", [1], is2d=False)
    wo.hide("hiddenfile", display=False)
    hidden_name = ".hiddenfile"
    root = os.path.join(os.getcwd(), "WithOpen")
    assert os.path.isdir(os.path.join(root, hidden_name))
    wo.unhide("hiddenfile", display=False)
    assert os.path.isdir(os.path.join(root, "hiddenfile"))


def test_backup_creates_snapshot(wo, tmp_path):
    wo.w("bakme", [1, 2], is2d=False)
    wo.backup("bakme", display=False)
    root = os.path.join(os.getcwd(), "WithOpen Backups", "bakme")
    assert os.path.isdir(root)
    assert any(f.endswith(".txt") for f in os.listdir(root))


def test_snapshot_creates_record(wo):
    wo.w("snapme", [1, 2], is2d=False)
    wo.snapshot("snapme", "s", 0.001, display=False)
    root = os.path.join(os.getcwd(), "WithOpen Snapshots", "snapme")
    assert os.path.isdir(root)


def test_backdate_returns_A_on_first_call(wo):
    wo.w("bd", [1], is2d=False)
    assert wo.backdate("bd", "s", gap=0) == "A"


def test_consoles_writes_file(wo):
    wo.w("cl", [1], is2d=False)
    wo.consoles("cl", multiple=False, alert=False)
    folder = os.path.join(os.getcwd(), "WithOpen", "cl")
    assert os.path.exists(os.path.join(folder, "cl_consoles.txt"))


def test_warning_writes_flag(wo):
    wo.warning(False)
    target = os.path.join(os.getcwd(), ".__hide_new_alert_987812919120.txt")
    assert os.path.exists(target)


def test_screen_buffer_put_and_format(wo):
    buf = wo.ScreenBuffer(wait=True)
    buf.put("hello")
    buf.put("world")
    rows = buf.format_text_for_display()
    assert any("hello" in row[0] for row in rows)
    assert any("world" in row[0] for row in rows)


def test_screen_buffer_inspect(wo, capsys):
    buf = wo.ScreenBuffer(wait=True)
    buf.put("a")
    buf.inspect()
    captured = capsys.readouterr()
    assert "[0]:" in captured.out


def test_screen_buffer_remove(wo):
    buf = wo.ScreenBuffer(wait=True)
    buf.put("keep")
    buf.put("drop")
    buf.remove(1)
    rows = buf.format_text_for_display()
    assert any("keep" in row[0] for row in rows)
    assert not any("drop" in row[0] for row in rows)


def test_screen_buffer_clear_buffer(wo):
    buf = wo.ScreenBuffer(wait=True)
    buf.put("something")
    buf.clear_buffer()
    rows = buf.format_text_for_display()
    assert all("something" not in row[0] for row in rows)


def test_corruption_tag_contains_name(wo):
    tag = wo.corruption_tag("TestName")
    assert "TestName" in tag


def test_write_all_files_and_read_back(wo):
    folder = os.path.join(os.getcwd(), "WithOpen", "direct")
    os.makedirs(folder, exist_ok=True)
    wo.write_all_files(["a", "b"], folder, "mydata")
    result = wo.majority_vote_file_reader("mydata", folder)
    assert result == ["a", "b"]


def test_read_txt_helper(wo):
    wo.w("rt", [7, 8], is2d=False)
    assert wo.read_txt("rt") == [7, 8]


def test_hide_folder_and_unhide_folder(wo, tmp_path):
    target = os.path.join(str(tmp_path), "folder_x")
    os.makedirs(target)
    result = wo.hide_folder(target)
    assert "Success" in result
    hidden = os.path.join(str(tmp_path), ".folder_x")
    assert os.path.isdir(hidden)
    result = wo.unhide_folder(hidden)
    assert "Success" in result
    assert os.path.isdir(target)


def test_is_visible(wo, tmp_path):
    target = os.path.join(str(tmp_path), "visible_folder")
    os.makedirs(target)
    assert wo.is_visible(target, announce=False) is True
    hidden = os.path.join(str(tmp_path), ".hidden_folder")
    os.makedirs(hidden)
    assert wo.is_visible(hidden, announce=False) is False


def test_restore_recency_zero(wo):
    result = wo.restore(recency=0, write=False, display=False)
    assert os.path.isdir(result)


def test_delete_requires_index_for_2d(wo):
    wo.w("d2", [[1, 2], [3, 4]], is2d=True)
    with pytest.raises(IndexError):
        wo.d("d2", del_list=["1"])


def test_1d_write_without_is2d_flag_raises(wo):
    with pytest.raises(ValueError):
        wo.w("plain", [1, 2, 3])


def test_2d_write_flag_mismatch_raises(wo):
    with pytest.raises(ValueError):
        wo.w("mismatch", [1, 2, 3], is2d=True)


def test_consoles_invalid_type(wo):
    with pytest.raises(ValueError):
        wo.consoles("x", multiple="yes", alert=False)


def test_warning_invalid_type(wo):
    with pytest.raises(ValueError):
        wo.warning("no")


def test_debug_on_empty_returns_none(wo, capsys):
    wo.w("empty", [], is2d=False)
    out = wo.debug("empty", is2d=False, display=False)
    assert out is None


def test_debug_on_1d_returns_good(wo):
    wo.w("dg", [1, 2, 3], is2d=False)
    out = wo.debug("dg", is2d=False, display=False)
    assert out is not None
    assert out["good"] == [1, 2, 3]
    assert out["bad"] == []
