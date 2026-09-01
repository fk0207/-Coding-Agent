"""Task 7：测试 run_agent_stream 流式循环（注入 fake streaming client）。"""
import json
from types import SimpleNamespace

from app.agent import run_agent_stream
from app.tools import HANDLERS, TOOLS


def _delta_chunk(content=None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _tool_call_delta(idx, tool_id, name, arguments):
    fn = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(index=idx, id=tool_id, function=fn)


def _client(create):
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_stream_answers_without_tool():
    client = _client(lambda **kw: iter([_delta_chunk("总结"), _delta_chunk("完成")]))

    events = list(
        run_agent_stream(client, "gpt-4o-mini", [{"role": "user", "content": "hi"}], TOOLS, HANDLERS)
    )
    deltas = [e["content"] for e in events if e["type"] == "delta"]
    done = [e for e in events if e["type"] == "done"]
    assert "".join(deltas) == "总结完成"
    assert done and done[0]["answer"] == "总结完成"
    assert done[0]["trace"] == []


def test_stream_calls_tool_then_answers(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world", encoding="utf-8")

    state = {"n": 0}

    def fake_create(**kw):
        n = state["n"]
        state["n"] += 1
        if n == 0:
            return iter(
                [
                    _delta_chunk(
                        tool_calls=[
                            _tool_call_delta(0, "call_1", "read_file", json.dumps({"path": str(f)}))
                        ]
                    )
                ]
            )
        return iter([_delta_chunk("文件内容: hello world")])

    events = list(
        run_agent_stream(_client(fake_create), "gpt-4o-mini", [{"role": "user", "content": "读 a.txt"}], TOOLS, HANDLERS)
    )
    tool_events = [e for e in events if e["type"] == "tool"]
    deltas = [e["content"] for e in events if e["type"] == "delta"]
    done = [e for e in events if e["type"] == "done"]

    assert len(tool_events) == 1
    assert tool_events[0]["tool"] == "read_file"
    assert "hello world" in tool_events[0]["result"]
    assert "".join(deltas) == "文件内容: hello world"
    assert done and done[0]["answer"] == "文件内容: hello world"


def test_stream_stops_at_max_iterations():
    def fake_create(**kw):
        return iter(
            [
                _delta_chunk(
                    tool_calls=[
                        _tool_call_delta(0, "call_x", "run_command", json.dumps({"command": "echo x"}))
                    ]
                )
            ]
        )

    events = list(
        run_agent_stream(
            _client(fake_create),
            "gpt-4o-mini",
            [{"role": "user", "content": "loop"}],
            TOOLS,
            HANDLERS,
            max_iterations=3,
        )
    )
    done = [e for e in events if e["type"] == "done"]
    assert done and "最大迭代" in done[-1]["answer"]
