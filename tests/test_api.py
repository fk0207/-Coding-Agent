"""Task 4：测试 /api/chat 接口与首页（mock run_agent）。"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_chat_endpoint(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def fake_run_agent(client, model, messages, tools, handlers, max_iterations=10):
        return ("完成", [{"tool": "read_file", "args": {"path": "x"}, "result": "y"}])

    with patch("app.main.run_agent", side_effect=fake_run_agent):
        client = TestClient(app)
        resp = client.post("/api/chat", json={"message": "总结 docs/README.md"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "完成"
        assert data["trace"][0]["tool"] == "read_file"


def test_index_served():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
