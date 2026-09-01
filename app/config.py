"""配置加载模块：从环境变量读取 LLM 接入与工作目录配置。"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Agent 运行配置。"""
    api_key: str     # OpenAI 兼容接口的 API 密钥
    base_url: str    # 接口地址
    model: str       # 模型名
    work_dir: str    # agent 读写文件 / 执行命令的工作目录


def load_config() -> Config:
    """从环境变量加载配置，返回 Config 实例。

    读取 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL / AGENT_WORK_DIR，
    未设置时使用默认值（base_url=https://api.openai.com/v1, model=gpt-4o-mini,
    work_dir=./workspace）。
    """
    return Config(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        work_dir=os.environ.get("AGENT_WORK_DIR", "./workspace"),
    )
