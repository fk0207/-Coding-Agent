"""FastAPI 应用：静态页面托管 + POST /api/chat 接口。"""
import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

from .agent import run_agent, run_agent_stream
from .config import load_config
from .tools import TOOLS, HANDLERS

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
config = load_config()
app = FastAPI(title="Minimal Coding Agent")

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    trace: list


@app.get("/")
def index():
    """返回前端页面 (static/index.html)。"""
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """接收用户需求，运行 agent，返回最终回答与工具调用 trace。"""
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    messages = [{"role": "user", "content": req.message}]
    answer, trace = run_agent(client, config.model, messages, TOOLS, HANDLERS)
    return ChatResponse(answer=answer, trace=trace)


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    """流式返回：SSE 逐 token 输出最终回答，并实时输出工具调用事件。"""
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    messages = [{"role": "user", "content": req.message}]

    def event_stream():
        for ev in run_agent_stream(client, config.model, messages, TOOLS, HANDLERS):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
