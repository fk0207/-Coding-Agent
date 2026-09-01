"""FastAPI 应用：静态页面托管 + POST /api/chat 接口。"""
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from .agent import run_agent
from .config import load_config
from .tools import TOOLS, HANDLERS

config = load_config()
app = FastAPI(title="Minimal Coding Agent")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    trace: list


@app.get("/")
def index():
    """返回前端页面 (static/index.html)。"""
    raise NotImplementedError("TODO(Task 4): 返回前端页面")


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """接收用户需求，运行 agent，返回最终回答与工具调用 trace。"""
    raise NotImplementedError("TODO(Task 4): 构造 client 并调用 run_agent")
