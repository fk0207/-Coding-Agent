"""Task 8：测试危险工具的权限控制（approver 审批）。"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.agent import run_agent, run_agent_stream
from app.tools import HANDLERS, TOOLS, is_dangerous


def test_is_dangerous():
    assert is_dangerous("run_command") is True
    assert is_dangerous("write_file") is True
    assert is_dangerous("read_file") is False


def _tc(tool_id, name, args):
    tc = MagicMock()
    tc.id = tool_id
    tc.function.name = name
    tc.function.arguments = json.dumps(args)
    return tc


def _resp(msg):
    return MagicMock(choices=[MagicMock(message=msg)])


def test_run_agent_denies_dangerous_without_approver():
    msg1 = MagicMock()
    msg1.tool_calls = [_tc("call_1", "run_command", {"command": "echo hi"})]
    msg1.content = None
    msg2 = MagicMock()
    msg2.tool_calls = None
    msg2.content = "已处理"
    client = MagicMock()
    client.chat.completions.create.side_effect = [_resp(msg1), _resp(msg2)]

    answer, trace = run_agent(client, "gpt-4o-mini", [{"role": "user", "content": "hi"}], TOOLS, HANDLERS)
    assert answer == "已处理"
    assert len(trace) == 1
    assert "拒绝" in trace[0]["result"]


def test_run_agent_approves_dangerous_tool(tmp_path):
    f = tmp_path / "out.txt"
    msg1 = MagicMock()
    msg1.tool_calls = [_tc("call_1", "write_file", {"path": str(f), "content": "hello"})]
    msg1.content = None
    msg2 = MagicMock()
    msg2.tool_calls = None
    msg2.content = "done"
    client = MagicMock()
    client.chat.completions.create.side_effect = [_resp(msg1), _resp(msg2)]

    answer, trace = run_agent(
        client, "gpt-4o-mini", [{"role": "user", "content": "写文件"}], TOOLS, HANDLERS,
        approver=lambda name, args: True,
    )
    assert answer == "done"
    assert f.read_text(encoding="utf-8") == "hello"
    assert "已写入" in trace[0]["result"]


def test_run_agent_approver_can_deny():
    msg1 = MagicMock()
    msg1.tool_calls = [_tc("call_1", "run_command", {"command": "echo hi"})]
    msg1.content = None
    msg2 = MagicMock()
    msg2.tool_calls = None
    msg2.content = "ok"
    client = MagicMock()
    client.chat.completions.create.side_effect = [_resp(msg1), _resp(msg2)]

    answer, trace = run_agent(
        client, "gpt-4o-mini", [{"role": "user", "content": "hi"}], TOOLS, HANDLERS,
        approver=lambda name, args: False,
    )
    assert "拒绝" in trace[0]["result"]


def test_stream_denies_dangerous_without_approver():
    def _delta_chunk(content=None, tool_calls=None):
        delta = SimpleNamespace(content=content, tool_calls=tool_calls)
        return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])

    def _tcd(idx, tool_id, name, arguments):
        fn = SimpleNamespace(name=name, arguments=arguments)
        return SimpleNamespace(index=idx, id=tool_id, function=fn)

    state = {"n": 0}

    def fake_create(**kw):
        n = state["n"]
        state["n"] += 1
        if n == 0:
            return iter([
                _delta_chunk(tool_calls=[
                    _tcd(0, "call_1", "run_command", json.dumps({"command": "echo hi"}))
                ])
            ])
        return iter([_delta_chunk("完成")])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    events = list(
        run_agent_stream(client, "gpt-4o-mini", [{"role": "user", "content": "hi"}], TOOLS, HANDLERS)
    )
    tool_events = [e for e in events if e["type"] == "tool"]
    assert len(tool_events) == 1
    assert "拒绝" in tool_events[0]["result"]
