# Minimal Coding Agent

一个极简 coding agent（一阶段）：具备**读写文件**、**执行 shell 命令**的能力，可完成「总结指定文件」「按需求编写脚本」等基础任务。Web 界面交互，基于 OpenAI 兼容接口。

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
