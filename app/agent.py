"""Agent 循环：反复调用 LLM，需要时执行工具，直到产出最终回答。"""
from typing import Any, Callable


def run_agent(
    client: Any,
    model: str,
    messages: list,
    tools: list,
    handlers: dict[str, Callable],
    max_iterations: int = 10,
) -> tuple[str, list]:
    """执行 agent 循环。

    参数：
        client:          OpenAI 兼容 client（含 chat.completions.create）
        model:           模型名
        messages:        对话消息列表（起始为用户请求）
        tools:           工具 schema 列表（TOOLS）
        handlers:        工具名 -> 实现函数 映射（HANDLERS）
        max_iterations:  最大 LLM 迭代次数，防止死循环

    返回：(最终回答文本, 工具调用 trace 列表)
        trace 元素形如 {"tool": 工具名, "args": 入参, "result": 结果文本}
    """
    raise NotImplementedError("TODO(Task 3): 实现 LLM + 工具调用的循环")
