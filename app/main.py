"""FastAPI 应用：静态页面托管 + POST /api/chat 接口。"""
import json
import queue
import threading
import uuid
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

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

load_dotenv(BASE_DIR.parent / ".env", override=True)
config = load_config()
app = FastAPI(title="Minimal Coding Agent")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")



class ApprovalGate:
    """危险工具审批协调器。

    request() 先通过 emit 回调发出 approval_request 事件，再阻塞等待用户决定；
    decide() 由 /api/approve 调用，把决定放回对应队列。超时默认拒绝。
    """

    def __init__(self, timeout=300):
        self.timeout = timeout
        self._pending = {}

    def request(self, emit, name, args):
        aid = uuid.uuid4().hex
        emit({"type": "approval_request", "id": aid, "tool": name, "args": args})
        decision = queue.Queue(maxsize=1)
        self._pending[aid] = decision
        try:
            return bool(decision.get(timeout=self.timeout))
        except queue.Empty:
            self._pending.pop(aid, None)
            return False

    def decide(self, aid, approved):
        decision = self._pending.pop(aid, None)
        if decision is None:
            return False
        decision.put(approved)
        return True


gate = ApprovalGate()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    trace: list


class ApprovalRequest(BaseModel):
    id: str
    approved: bool


@app.get("/")
def index():
    """返回前端页面 (static/index.html)。"""
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """接收用户需求，运行 agent，返回最终回答与工具调用 trace。

    非流式接口不支持交互审批，危险工具默认拒绝执行。
    """
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    messages = [{"role": "user", "content": req.message}]
    answer, trace = run_agent(client, config.model, messages, TOOLS, HANDLERS)
    return ChatResponse(answer=answer, trace=trace)


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    """流式返回：SSE 逐 token 输出最终回答；危险工具先发 approval_request 等待用户同意。"""
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    messages = [{"role": "user", "content": req.message}]
    out = queue.Queue()

    def approver(name, args):
        return gate.request(out.put, name, args)

    def worker():
        try:
            for ev in run_agent_stream(
                client, config.model, messages, TOOLS, HANDLERS, approver=approver
            ):
                out.put(ev)
        finally:
            out.put(None)  # 结束哨兵

    threading.Thread(target=worker, daemon=True).start()

    def event_stream():
        while True:
            ev = out.get()
            if ev is None:
                break
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/approve")
def approve(req: ApprovalRequest):
    """用户对某个审批请求作出决定（同意/拒绝）。"""
    if gate.decide(req.id, req.approved):
        return {"ok": True}
    return {"ok": False, "reason": "approval not found or expired"}
