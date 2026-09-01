"""Task 9：测试多轮会话历史。"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main as main_mod
from app.main import app


def test_chat_stream_session_history(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    main_mod.SESSIONS.clear()

    def fake_stream(client, model, messages, tools, handlers, approver=None, asker=None, max_iterations=10):
        yield {"type": "done", "answer": "回答", "trace": []}

    with patch("app.main.run_agent_stream", side_effect=fake_stream):
        client = TestClient(app)
        r1 = client.post("/api/chat/stream", json={"message": "第一句"})
        r1.text  # 消费流式响应，确保 worker 线程完成
        sid = list(main_mod.SESSIONS.keys())[0]
        r2 = client.post("/api/chat/stream", json={"message": "第二句", "session_id": sid})
        r2.text

    conv = main_mod.SESSIONS[sid]
    assert [m["role"] for m in conv] == ["user", "assistant", "user", "assistant"]
    assert conv[0]["content"] == "第一句"
    assert conv[1]["content"] == "回答"
    assert conv[2]["content"] == "第二句"


def test_chat_session_history(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    main_mod.SESSIONS.clear()

    def fake_run_agent(client, model, messages, tools, handlers, max_iterations=10):
        return ("完成", [])

    with patch("app.main.run_agent", side_effect=fake_run_agent):
        client = TestClient(app)
        r1 = client.post("/api/chat", json={"message": "hi"})
        sid = r1.json()["session_id"]
        r2 = client.post("/api/chat", json={"message": "继续", "session_id": sid})

    conv = main_mod.SESSIONS[sid]
    assert [m["role"] for m in conv] == ["user", "assistant", "user", "assistant"]
    assert conv[0]["content"] == "hi"
    assert conv[2]["content"] == "继续"


def test_session_history_is_trimmed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(main_mod, "MAX_SESSION_TURNS", 2)
    main_mod.SESSIONS.clear()

    def fake_run_agent(client, model, messages, tools, handlers, max_iterations=10):
        return ("ok", [])

    with patch("app.main.run_agent", side_effect=fake_run_agent):
        client = TestClient(app)
        sid = None
        for i in range(5):
            payload = {"message": f"m{i}"}
            if sid:
                payload["session_id"] = sid
            r = client.post("/api/chat", json=payload)
            sid = r.json()["session_id"]

    conv = main_mod.SESSIONS[sid]
    assert len(conv) == 4
    assert conv[0]["content"] == "m3"
    assert conv[-1]["content"] == "ok"


def test_sessions_evicted_when_too_many(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(main_mod, "MAX_SESSIONS", 2)
    main_mod.SESSIONS.clear()

    def fake_run_agent(client, model, messages, tools, handlers, max_iterations=10):
        return ("ok", [])

    with patch("app.main.run_agent", side_effect=fake_run_agent):
        client = TestClient(app)
        sids = []
        for i in range(3):
            r = client.post("/api/chat", json={"message": f"m{i}"})  # 每次新会话
            sids.append(r.json()["session_id"])

    assert len(main_mod.SESSIONS) == 2
    assert sids[0] not in main_mod.SESSIONS
    assert sids[1] in main_mod.SESSIONS
    assert sids[2] in main_mod.SESSIONS
