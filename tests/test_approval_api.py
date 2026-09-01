"""Task 8：测试 /api/approve 端点与审批协调器 ApprovalGate。"""
import threading
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import ApprovalGate, app, gate


def test_approve_endpoint_unknown_id():
    client = TestClient(app)
    resp = client.post("/api/approve", json={"id": "nonexistent", "approved": True})
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


def _start_request(g, name, args):
    """在后台线程调用 g.request，返回 (线程, emitted, emit 完成事件, result)。"""
    emitted = {}
    done = threading.Event()

    def emit(ev):
        emitted.update(ev)
        done.set()

    result = []

    def run():
        result.append(g.request(emit, name, args))

    t = threading.Thread(target=run)
    t.start()
    return t, emitted, done, result


def test_approval_gate_request_and_decide():
    g = ApprovalGate(timeout=5)
    t, emitted, done, result = _start_request(g, "run_command", {"command": "ls"})

    assert done.wait(timeout=5)
    assert emitted["type"] == "approval_request"
    assert emitted["tool"] == "run_command"

    assert g.decide(emitted["id"], True) is True
    t.join(timeout=5)
    assert not t.is_alive()
    assert result == [True]


def test_approval_gate_deny():
    g = ApprovalGate(timeout=5)
    t, emitted, done, result = _start_request(g, "write_file", {"path": "x", "content": "y"})

    assert done.wait(timeout=5)
    assert g.decide(emitted["id"], False) is True
    t.join(timeout=5)
    assert not t.is_alive()
    assert result == [False]


def test_approval_gate_timeout_defaults_deny():
    g = ApprovalGate(timeout=0.2)
    assert g.request(lambda ev: None, "run_command", {"command": "ls"}) is False


def test_chat_stream_emits_approval_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    # 用不阻塞的假 request 替换真 request，便于同步测试端点接线
    def fake_request(emit, name, args):
        emit({"type": "approval_request", "id": "aid1", "tool": name, "args": args})
        return True

    monkeypatch.setattr(gate, "request", fake_request)

    def fake_stream(client, model, messages, tools, handlers, approver=None, max_iterations=10):
        approved = approver("run_command", {"command": "ls"})
        yield {"type": "tool", "tool": "run_command", "args": {"command": "ls"}, "result": "ok" if approved else "denied"}
        yield {"type": "done", "answer": "完成", "trace": []}

    with patch("app.main.run_agent_stream", side_effect=fake_stream):
        client = TestClient(app)
        resp = client.post("/api/chat/stream", json={"message": "hi"})
        body = resp.text
        assert '"type": "approval_request"' in body
        assert '"tool": "run_command"' in body
        assert '"result": "ok"' in body
