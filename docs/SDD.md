# 软件设计说明书（SDD）—— 初步骨架

| 项目 | 内容 |
|---|---|
| 项目名称 | Minimal Coding Agent（一阶段） |
| 文档类型 | 软件设计说明书（SDD） |
| 版本 | v0.1（初步骨架） |
| 日期 | 2026-09-01 |
| 仓库 | https://github.com/fk0207/-Coding-Agent |
| 关联文档 | 《开发计划书》`docs/开发计划书.md` |

---

## 1. 引言

### 1.1 目的
本文档描述极简 Coding Agent（一阶段）的**初步骨架设计**，定义系统的模块划分、模块职责、模块间接口与目录结构，作为后续实现（Task 1–6）的设计依据。

### 1.2 范围
本阶段范围：具备「读写文件 + 执行 shell 命令」能力、可完成「总结文件 / 按需求写脚本」等基础任务，提供 Web 界面，基于 OpenAI 兼容接口。

### 1.3 术语
- **Agent 循环**：LLM 反复决策——调用工具 → 取回结果 → 再决策，直到产出最终回答。
- **工具（Tool）**：以 OpenAI function calling 格式暴露给 LLM 的能力单元（read_file / write_file / run_command）。
- **兼容接口**：遵循 OpenAI API 协议的服务（OpenAI / DeepSeek / Qwen / GLM / Ollama 等）。

---

## 2. 总体设计

### 2.1 架构
三层极简架构：

```
浏览器（HTML/CSS/JS）
        │  HTTP
        ▼
FastAPI 后端（静态托管 + POST /api/chat）
        │  函数调用
        ▼
Agent 循环（LLM 决策 + 工具执行）
        │  function calling
        ▼
LLM（OpenAI 兼容接口）
```

- **表现层**：零构建单页聊天界面，由 FastAPI 静态托管。
- **服务层**：FastAPI，唯一业务接口 `POST /api/chat`。
- **核心层**：手写 agent 循环 + 三个工具，与 LLM 解耦（client 可注入，便于单测）。

### 2.2 技术选型
| 项 | 选型 | 理由 |
|---|---|---|
| 语言 | Python 3.10+ | Agent/LLM 生态成熟 |
| Web 框架 | FastAPI + uvicorn | 轻量、自带静态托管与 Pydantic 校验 |
| LLM SDK | openai（>=1.0） | 兼容接口通用，base_url 可配 |
| 前端 | 原生 HTML/CSS/JS | 极简，无构建链 |
| 测试 | pytest + httpx | 单测 + API 测试 |

---

## 3. 模块设计

### 3.1 `app/config.py` —— 配置模块
- **职责**：从环境变量加载 LLM 接入与工作目录配置。
- **产出**：`Config` dataclass（`api_key` / `base_url` / `model` / `work_dir`）、`load_config()`。

### 3.2 `app/tools.py` —— 工具模块
- **职责**：定义并实现三个工具，提供 LLM 可用的 schema 与处理器映射。
- **产出**：`TOOLS`（list[dict] schema）、`HANDLERS`（dict 名称→函数）、三个工具函数。

### 3.3 `app/agent.py` —— Agent 循环模块
- **职责**：驱动 LLM 与工具交互，直到产出最终回答或达到迭代上限。
- **产出**：`run_agent(client, model, messages, tools, handlers, max_iterations=10) -> (answer, trace)`。

### 3.4 `app/main.py` —— 服务模块
- **职责**：暴露 HTTP 接口、托管前端静态资源、组装 agent 与配置。
- **产出**：FastAPI `app`、`GET /`、`POST /api/chat`。

### 3.5 `app/static/` —— 前端
- **职责**：聊天交互界面，发送需求、渲染回答与工具调用 trace。

---

## 4. 接口设计

| 符号 | 签名 | 返回 | 说明 |
|---|---|---|---|
| `load_config` | `() -> Config` | 配置对象 | 读环境变量，含默认值 |
| `read_file` | `(path: str) -> str` | 文件文本 | 读文本文件 |
| `write_file` | `(path: str, content: str) -> str` | 确认信息 | 覆盖写 |
| `run_command` | `(command: str, timeout: int = 30) -> str` | stdout/stderr | 执行 shell |
| `run_agent` | `(client, model, messages, tools, handlers, max_iterations=10) -> tuple[str, list]` | (回答, trace) | agent 循环 |

**HTTP 接口：**

| 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|
| GET | `/` | — | 前端页面 HTML |
| POST | `/api/chat` | `{"message": str}` | `{"answer": str, "trace": list}` |

---

## 5. 数据流

`POST /api/chat` 时序：

```
用户输入 message
   → main.chat 构造 OpenAI client + 初始 messages=[{role:user}]
   → run_agent 循环：
        LLM 返回 tool_calls？──否──→ 返回最终 answer
        └─ 是 → 逐个执行 handlers[name](**args)
              → 将 tool 结果回填 messages
              → 记录 trace → 继续循环（直至 max_iterations）
   → 返回 {answer, trace} 给前端渲染
```

---

## 6. 目录结构

```
minimal-coding-agent/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── tools.py
│   ├── agent.py
│   ├── main.py
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── tests/
│   ├── test_config.py
│   ├── test_tools.py
│   ├── test_agent.py
│   └── test_api.py
├── docs/
│   ├── 开发计划书.md
│   └── SDD.md
├── requirements.txt
├── .env.example
├── .gitignore
├── pytest.ini
└── README.md
```

---

## 7. 关键设计决策与约束

1. **client 可注入**：`run_agent` 接收 client 而非自建，使核心循环可脱离真实 API 单测（注入 fake client）。
2. **最大迭代上限**：`max_iterations` 防 LLM 发散死循环。
3. **命令超时**：`run_command` 默认 30s 超时。
4. **密钥不落库**：`api_key` 仅经环境变量/.env 注入，仓库只提交 `.env.example`。
5. **前端零构建**：原生三件套，FastAPI 静态托管。
6. **安全边界（本阶段接受，后续硬化）**：`run_command` 使用 `shell=True` 执行任意命令，存在命令注入风险，仅限本地/受信任环境，沙箱化列入后续阶段。

---

## 8. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-09-01 | 初步骨架定义 |
