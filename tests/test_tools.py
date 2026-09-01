"""Task 2：测试 read_file / write_file / run_command 与 TOOLS/HANDLERS 对齐。"""
from app.tools import TOOLS, HANDLERS, read_file, run_command, write_file


def test_read_file(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world", encoding="utf-8")
    assert read_file(str(f)) == "hello world"


def test_write_file(tmp_path):
    f = tmp_path / "b.txt"
    result = write_file(str(f), "新内容")
    assert f.read_text(encoding="utf-8") == "新内容"
    assert "b.txt" in result


def test_run_command():
    result = run_command("echo hi", timeout=5)
    assert "hi" in result


def test_run_command_timeout():
    result = run_command("sleep 3", timeout=1)
    assert "超时" in result or "timeout" in result.lower()


def test_tools_schema_and_handlers_aligned():
    names = {t["function"]["name"] for t in TOOLS}
    assert names == set(HANDLERS.keys())
    assert {"read_file", "write_file", "run_command"} <= names
