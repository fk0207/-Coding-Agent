"""Task 3：测试 run_agent 循环（注入 fake client，不依赖真实 API）。"""
import json
from unittest.mock import MagicMock

from app.agent import run_agent
from app.tools import HANDLERS, TOOLS


def _resp(msg):
    return MagicMock(choices=[MagicMock(message=msg)])


def _tool_call(tool_id, name, args):
    tc = MagicMock()
    tc.id = tool_id
    tc.function.name = name
    tc.function.arguments = json.dumps(args)
    return tc


def test_agent_answers_without_tool():
    msg = MagicMock()
    msg.tool_calls = None
    msg.content = "总结完成"
    client = MagicMock()
    client.chat.completions.create.return_value = _resp(msg)

    answer, trace = run_agent(
        client, "gpt-4o-mini", [{"role": "user", "content": "hi"}], TOOLS, HANDLERS
    )
    assert answer == "总结完成"
    assert trace == []


def test_agent_calls_read_file_then_answers(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world", encoding="utf-8")

    msg1 = MagicMock()
    msg1.tool_calls = [_tool_call("call_1", "read_file", {"path": str(f)})]
    msg1.content = None
    msg2 = MagicMock()
    msg2.tool_calls = None
    msg2.content = "文件内容是 hello world"

    client = MagicMock()
    client.chat.completions.create.side_effect = [_resp(msg1), _resp(msg2)]

    answer, trace = run_agent(
        client, "gpt-4o-mini", [{"role": "user", "content": "读 a.txt"}], TOOLS, HANDLERS
    )
    assert answer == "文件内容是 hello world"
    assert len(trace) == 1
    assert trace[0]["tool"] == "read_file"
    assert "hello world" in trace[0]["result"]


def test_agent_stops_at_max_iterations():
    msg = MagicMock()
    msg.tool_calls = [_tool_call("call_x", "run_command", {"command": "echo x"})]
    msg.content = None
    client = MagicMock()
    client.chat.completions.create.return_value = _resp(msg)

    answer, _ = run_agent(
        client,
        "gpt-4o-mini",
        [{"role": "user", "content": "loop"}],
        TOOLS,
        HANDLERS,
        max_iterations=3,
    )
    assert "最大迭代" in answer
