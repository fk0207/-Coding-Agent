# Minimal Coding Agent

一个极简 coding agent（一阶段）：具备**读写文件**、**执行 shell 命令**、**向用户提问（ask_user）**的能力，可完成「总结指定文件」「按需求编写脚本」等基础任务。Web 界面交互，基于 OpenAI 兼容接口；支持**危险工具审批**与**多轮会话记忆**。

- 仓库地址：https://github.com/fk0207/-Coding-Agent
- 文档：[开发计划书](docs/开发计划书.md) · [软件设计说明书 SDD](docs/SDD.md)

## 技术栈

Python 3.10+ · FastAPI · uvicorn · openai（兼容接口）· 原生 HTML/CSS/JS

## 快速开始

> 要求 Python ≥ 3.10

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置密钥
cp .env.example .env        # Windows 用 copy .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY（及兼容服务的 OPENAI_BASE_URL）

# 3. 启动
uvicorn app.main:app --reload

# 4. 浏览器打开 http://127.0.0.1:8000
```

## 配置项

| 变量 | 说明 | 默认 |
|---|---|---|
| `OPENAI_API_KEY` | API 密钥 | 空 |
| `OPENAI_BASE_URL` | 兼容接口地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 模型名 | `gpt-4o-mini` |
| `AGENT_WORK_DIR` | 工作目录 | `./workspace` |

兼容服务示例（改 `OPENAI_BASE_URL` + `OPENAI_MODEL`）：

| 服务 | base_url | 模型示例 |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| Ollama（本地） | `http://localhost:11434/v1` | `llama3` |

## 使用示例

- 「总结 docs/README.md 的内容」
- 「写一个打印 hello 的 Python 脚本并运行它」

## 工具列表

Agent 通过 OpenAI 函数调用使用以下工具：

| 工具 | 说明 | 需要审批 |
|---|---|---|
| `read_file` | 读取文件内容 | 否 |
| `write_file` | 写入文件 | ✅ |
| `run_command` | 执行 shell 命令 | ✅ |
| `ask_user` | 向用户提问 | 否（交互式） |

`write_file` / `run_command` 属于危险工具，执行前会弹出审批框，用户同意后才执行；拒绝则跳过该步骤。

## 交互式提问（ask_user）

当需求信息不足（例如「先问清楚用 JSON 还是 YAML」）时，Agent 会调用 `ask_user` 提问。页面弹出 ❓ 提问气泡，用户输入回答后，Agent 拿到回答并**继续执行**后续步骤。

示例提示词：

> 帮我写一个配置文件来保存应用配置。是存成 JSON 还是 YAML、里面放哪些字段，你先问清楚再动手。

## 多轮会话记忆

后端按 `session_id` 保存每轮 user/assistant 对话，后续请求自动携带历史上下文，Agent 能记住之前的对话。

- 新会话首次请求返回 `session_id`，前端保存后自动回传。
- 点击页面「新对话」按钮清空上下文，开启新会话。
- 单个会话最多保留最近 20 轮；会话总数超过 100 个时淘汰最旧会话。

## ⚠️ 安全声明

本工具会执行 LLM 生成的 shell 命令（`shell=True`），存在任意命令执行风险。**仅限本地 / 受信任环境使用，请勿直接暴露到公网。** 命令沙箱化与权限收敛属后续阶段任务。

## 测试

```bash
pytest -v
```

## 目录结构

```
app/            # 应用代码（config / tools / agent / main + static 前端）
tests/          # 单元测试
docs/           # 开发计划书 + SDD
```
