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


class InteractionGate:
    """用户交互协调器：审批（bool）与提问（str）都通过队列阻塞等待前端回应。"""

    def __init__(self, timeout=300):
        self.timeout = timeout
        self._pending = {}

    def _wait(self, aid, emit_event, default):
        decision = queue.Queue(maxsize=1)
        self._pending[aid] = decision
        emit_event()
        try:
            return decision.get(timeout=self.timeout)
        except queue.Empty:
            self._pending.pop(aid, None)
            return default

    def request(self, emit, name, args):
        """审批：发出 approval_request 事件，返回用户是否同意（bool）。"""
        aid = uuid.uuid4().hex

        def emit_event():
            emit({"type": "approval_request", "id": aid, "tool": name, "args": args})

        return bool(self._wait(aid, emit_event, default=False))

    def ask(self, emit, question):
        """提问：发出 ask_user_request 事件，返回用户回答（str）。"""
        aid = uuid.uuid4().hex

        def emit_event():
            emit({"type": "ask_user_request", "id": aid, "question": question})

        return str(self._wait(aid, emit_event, default=""))

    def decide(self, aid, value):
        """把用户决定（bool 或 str）放回对应等待队列。"""
        decision = self._pending.pop(aid, None)
        if decision is None:
            return False
        decision.put(value)
        return True


gate = InteractionGate()

# 会话历史：session_id -> [{"role": "user"/"assistant", "content": ...}]
SESSIONS = {}
MAX_SESSION_TURNS = 20
MAX_SESSIONS = 100


def _trim(conversation):
    """去掉最前面多余的整轮（user+assistant），保证历史不超过 MAX_SESSION_TURNS 轮。"""
    while len(conversation) // 2 > MAX_SESSION_TURNS:
        conversation.pop(0)
        conversation.pop(0)


def _get_conversation(session_id):
    """取出已有会话或新建；超过 MAX_SESSIONS 时淘汰最旧的会话。"""
    if session_id in SESSIONS:
        return SESSIONS[session_id]
    while len(SESSIONS) >= MAX_SESSIONS:
        SESSIONS.pop(next(iter(SESSIONS)), None)
    conversation = []
    SESSIONS[session_id] = conversation
    return conversation


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    trace: list
    session_id: str


class ApprovalRequest(BaseModel):
    id: str
    approved: bool


class AnswerRequest(BaseModel):
    id: str
    answer: str


@app.get("/")
def index():
    """返回前端页面 (static/index.html)。"""
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """接收用户需求，运行 agent，返回最终回答与工具调用 trace。

    非流式接口不支持交互审批/提问：危险工具默认拒绝、ask_user 返回占位。
    """
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    session_id = req.session_id or uuid.uuid4().hex
    conversation = _get_conversation(session_id)
    conversation.append({"role": "user", "content": req.message})
    _trim(conversation)
    messages = list(conversation)

    answer, trace = run_agent(client, config.model, messages, TOOLS, HANDLERS)
    conversation.append({"role": "assistant", "content": answer})
    _trim(conversation)
    return ChatResponse(answer=answer, trace=trace, session_id=session_id)


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    """流式返回：SSE 逐 token 输出最终回答；危险工具发 approval_request、ask_user 发提问等待用户。"""
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    session_id = req.session_id or uuid.uuid4().hex
    conversation = _get_conversation(session_id)
    conversation.append({"role": "user", "content": req.message})
    _trim(conversation)
    messages = list(conversation)
    out = queue.Queue()

    def approver(name, args):
        return gate.request(out.put, name, args)

    def asker(args):
        return gate.ask(out.put, args.get("question", ""))

    def worker():
        final_answer = None
        try:
            for ev in run_agent_stream(
                client, config.model, messages, TOOLS, HANDLERS,
                approver=approver, asker=asker,
            ):
                if ev.get("type") == "done":
                    ev["session_id"] = session_id
                    final_answer = ev.get("answer")
                out.put(ev)
            conversation.append({"role": "assistant", "content": final_answer or ""})
            _trim(conversation)
        except Exception as exc:  # 把运行错误透传给前端，避免流静默卡死
            out.put({"type": "error", "message": f"运行失败: {exc}"})
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


@app.post("/api/answer")
def answer(req: AnswerRequest):
    """用户回答 ask_user 提问。"""
    if gate.decide(req.id, req.answer):
        return {"ok": True}
    return {"ok": False, "reason": "question not found or expired"}
