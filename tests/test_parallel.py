"""Task 7：测试工具并行执行（ThreadPoolExecutor）。"""
import json
import threading
from unittest.mock import MagicMock

from app.agent import _run_tools_parallel, run_agent
from app.tools import HANDLERS, TOOLS


def test_run_tools_parallel_keeps_order():
    handlers = {"a": lambda **kw: "r1", "b": lambda **kw: "r2"}
    specs = [("a", {}), ("b", {}), ("a", {})]
    assert _run_tools_parallel(handlers, specs) == ["r1", "r2", "r1"]


def test_run_tools_parallel_is_concurrent():
    # 3 个调用必须同时进行：若串行执行，barrier 凑不齐 3 个线程会超时抛 BrokenBarrierError
    barrier = threading.Barrier(3)

    def handler(**kw):
        barrier.wait(timeout=5)
        return "ok"

    specs = [("f", {}), ("f", {}), ("f", {})]
    assert _run_tools_parallel({"f": handler}, specs) == ["ok", "ok", "ok"]


def test_run_agent_multiple_tools_in_order(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("AAA", encoding="utf-8")
    f2.write_text("BBB", encoding="utf-8")

    def _tc(tool_id, name, args):
        tc = MagicMock()
        tc.id = tool_id
        tc.function.name = name
        tc.function.arguments = json.dumps(args)
        return tc

    def _resp(msg):
        return MagicMock(choices=[MagicMock(message=msg)])

    msg1 = MagicMock()
    msg1.tool_calls = [
        _tc("call_1", "read_file", {"path": str(f1)}),
        _tc("call_2", "read_file", {"path": str(f2)}),
    ]
    msg1.content = None
    msg2 = MagicMock()
    msg2.tool_calls = None
    msg2.content = "done"

    client = MagicMock()
    client.chat.completions.create.side_effect = [_resp(msg1), _resp(msg2)]

    answer, trace = run_agent(
        client, "gpt-4o-mini", [{"role": "user", "content": "读两个文件"}], TOOLS, HANDLERS
    )
    assert answer == "done"
    assert len(trace) == 2
    assert trace[0]["tool"] == "read_file"
    assert "AAA" in trace[0]["result"]
    assert "BBB" in trace[1]["result"]
