"""Task 1：测试 load_config 读取环境变量与默认值。"""
from app.config import load_config


def test_load_config_reads_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "deepseek-chat")
    monkeypatch.setenv("AGENT_WORK_DIR", "/tmp/ws")

    cfg = load_config()
    assert cfg.api_key == "sk-test"
    assert cfg.base_url == "https://api.deepseek.com/v1"
    assert cfg.model == "deepseek-chat"
    assert cfg.work_dir == "/tmp/ws"


def test_load_config_defaults(monkeypatch):
    for k in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "AGENT_WORK_DIR"):
        monkeypatch.delenv(k, raising=False)

    cfg = load_config()
    assert cfg.base_url == "https://api.openai.com/v1"
    assert cfg.model == "gpt-4o-mini"
    assert cfg.work_dir == "./workspace"
