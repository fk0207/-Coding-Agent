"""Task 7：测试 /api/chat/stream 流式接口（mock run_agent_stream）。"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_chat_stream_endpoint(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def fake_run_agent_stream(client, model, messages, tools, handlers, max_iterations=10, approver=None, asker=None):
        yield {"type": "delta", "content": "完成"}
        yield {"type": "tool", "tool": "read_file", "args": {"path": "x"}, "result": "y"}
        yield {"type": "done", "answer": "完成", "trace": []}

    with patch("app.main.run_agent_stream", side_effect=fake_run_agent_stream):
        client = TestClient(app)
        resp = client.post("/api/chat/stream", json={"message": "hi"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert '"type": "delta"' in body
        assert '"type": "tool"' in body
        assert "完成" in body


def test_chat_stream_emits_error_on_exception(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def fake_run_agent_stream(client, model, messages, tools, handlers, max_iterations=10, approver=None, asker=None):
        yield {"type": "delta", "content": "部分"}
        raise RuntimeError("网络错误")

    with patch("app.main.run_agent_stream", side_effect=fake_run_agent_stream):
        client = TestClient(app)
        resp = client.post("/api/chat/stream", json={"message": "hi"})
        body = resp.text
        assert '"type": "error"' in body
        assert "网络错误" in body
