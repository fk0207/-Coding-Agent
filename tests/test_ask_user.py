"""Task 9：测试 ask_user 交互式提问工具。"""
import json
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.agent import run_agent, run_agent_stream
from app.main import InteractionGate
from app.tools import HANDLERS, TOOLS


def test_ask_user_in_schema():
    ask = [t for t in TOOLS if t["function"]["name"] == "ask_user"]
    assert len(ask) == 1
    params = ask[0]["function"]["parameters"]
    assert "question" in params["properties"]
    assert "question" in params["required"]


def test_run_agent_ask_user_continues():
    msg1 = MagicMock()
    tc = MagicMock()
    tc.id = "call_1"
    tc.function.name = "ask_user"
    tc.function.arguments = json.dumps({"question": "要写入哪个文件？"})
    msg1.tool_calls = [tc]
    msg1.content = None
    msg2 = MagicMock()
    msg2.tool_calls = None
    msg2.content = "好的，写入 a.txt"

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=msg1)]),
        MagicMock(choices=[MagicMock(message=msg2)]),
    ]

    def asker(args):
        assert args["question"] == "要写入哪个文件？"
        return "a.txt"

    answer, trace = run_agent(
        client, "gpt-4o-mini", [{"role": "user", "content": "写文件"}], TOOLS, HANDLERS,
        asker=asker,
    )
    assert answer == "好的，写入 a.txt"
    assert trace[0]["tool"] == "ask_user"
    assert trace[0]["result"] == "a.txt"


def test_run_agent_ask_user_without_asker_falls_back():
    msg1 = MagicMock()
    tc = MagicMock()
    tc.id = "call_1"
    tc.function.name = "ask_user"
    tc.function.arguments = json.dumps({"question": "?"})
    msg1.tool_calls = [tc]
    msg1.content = None
    msg2 = MagicMock()
    msg2.tool_calls = None
    msg2.content = "done"

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=msg1)]),
        MagicMock(choices=[MagicMock(message=msg2)]),
    ]

    answer, trace = run_agent(
        client, "gpt-4o-mini", [{"role": "user", "content": "hi"}], TOOLS, HANDLERS
    )
    assert "用户未回答" in trace[0]["result"]


def test_stream_ask_user():
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
                    _tcd(0, "call_1", "ask_user", json.dumps({"question": "选哪个？"}))
                ])
            ])
        return iter([_delta_chunk("选了 A")])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))

    events = list(
        run_agent_stream(
            client, "gpt-4o-mini", [{"role": "user", "content": "hi"}], TOOLS, HANDLERS,
            asker=lambda args: "A",
        )
    )
    tool_events = [e for e in events if e["type"] == "tool"]
    assert tool_events[0]["tool"] == "ask_user"
    assert tool_events[0]["result"] == "A"


def test_interaction_gate_ask():
    g = InteractionGate(timeout=5)
    emitted = {}
    done = threading.Event()

    def emit(ev):
        emitted.update(ev)
        done.set()

    result = []

    def run():
        result.append(g.ask(emit, "你的需求是什么？"))

    t = threading.Thread(target=run)
    t.start()
    assert done.wait(timeout=5)
    assert emitted["type"] == "ask_user_request"
    assert emitted["question"] == "你的需求是什么？"

    assert g.decide(emitted["id"], "写一个脚本") is True
    t.join(timeout=5)
    assert result == ["写一个脚本"]
