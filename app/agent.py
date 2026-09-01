"""Agent 循环：反复调用 LLM，需要时执行工具，直到产出最终回答。"""
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

from .tools import is_dangerous


def _run_tools_parallel(handlers, specs):
    """并行执行多个工具调用，返回与 specs 同序的结果列表。

    specs: [(name, args), ...]，name 为工具名，args 为解析后的入参字典。
    单条调用直接执行（避免线程开销）；多条调用用线程池并行，提升 I/O 与
    subprocess 类工具的执行效率。
    """
    if len(specs) == 1:
        name, args = specs[0]
        return [handlers[name](**args)]

    with ThreadPoolExecutor(max_workers=len(specs)) as pool:
        return list(pool.map(lambda s: handlers[s[0]](**s[1]), specs))


def _execute_with_approval(handlers, specs, approver):
    """按权限策略执行工具。


    危险工具（见 tools.is_dangerous）需 approver 同意；approver 为 None 或返回
    False 时拒绝执行（不调用 handler）。允许执行的工具用线程池并行运行。

    返回与 specs 同序的结果列表（字符串）。
    """
    results = [None] * len(specs)
    to_run = []  # (index, name, args) 允许执行的部分
    for i, (name, args) in enumerate(specs):
        if is_dangerous(name):
            approved = approver(name, args) if approver else False
            if not approved:
                results[i] = f"已拒绝执行危险工具 {name}（未经用户同意）"
                continue
        to_run.append((i, name, args))

    if to_run:
        executed = _run_tools_parallel(handlers, [(n, a) for _, n, a in to_run])
        for (i, _, _), r in zip(to_run, executed):
            results[i] = r
    return results


def run_agent(
    client: Any,
    model: str,
    messages: list,
    tools: list,
    handlers: dict[str, Callable],
    max_iterations: int = 10,
    approver: Optional[Callable[[str, dict], bool]] = None,
) -> tuple[str, list]:
    """执行 agent 循环。


    参数：
        client:          OpenAI 兼容 client（含 chat.completions.create）
        model:           模型名
        messages:        对话消息列表（起始为用户请求）
        tools:           工具 schema 列表（TOOLS）
        handlers:        工具名 -> 实现函数 映射（HANDLERS）
        max_iterations:  最大 LLM 迭代次数，防止死循环
        approver:        危险工具审批回调 approver(name, args) -> bool；None 则拒绝

    返回：(最终回答文本, 工具调用 trace 列表)
        trace 元素形如 {"tool": 工具名, "args": 入参, "result": 结果文本}
    """
    trace = []
    for _ in range(max_iterations):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return (msg.content or "", trace)

        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
        )

        specs = [
            (tc.function.name, json.loads(tc.function.arguments or "{}"))
            for tc in msg.tool_calls
        ]
        results = _execute_with_approval(handlers, specs, approver)

        for tc, (name, args), result in zip(msg.tool_calls, specs, results):
            trace.append({"tool": name, "args": args, "result": str(result)})
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": str(result)}
            )

    return ("已达到最大迭代次数，任务可能未完成。", trace)


def run_agent_stream(
    client: Any,
    model: str,
    messages: list,
    tools: list,
    handlers: dict[str, Callable],
    max_iterations: int = 10,
    approver: Optional[Callable[[str, dict], bool]] = None,
):
    """流式版 agent 循环：逐 token 产出回答，并实时产出工具调用事件。

    与 run_agent 逻辑一致，但以生成器逐条 yield dict 事件：
        {"type": "delta", "content": "..."}                       # 回答文本增量
        {"type": "tool", "tool": ..., "args": ..., "result": ...} # 工具调用
        {"type": "done", "answer": "...", "trace": [...]}         # 结束

    说明：推理模型（如 deepseek-v4-pro）的思考过程走 delta.reasoning_content，
    这里只累积 delta.content（最终回答），因此前端只看到答案逐字流出。
    危险工具需 approver 同意，approver 为 None 时拒绝执行。
    """
    trace = []
    for _ in range(max_iterations):
        content_parts = []
        tool_calls = []  # 按 index 合并成 {"id", "name", "arguments"}

        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if getattr(delta, "content", None):
                content_parts.append(delta.content)
                yield {"type": "delta", "content": delta.content}

            for tcd in getattr(delta, "tool_calls", None) or []:
                idx = tcd.index
                while len(tool_calls) <= idx:
                    tool_calls.append({"id": "", "name": "", "arguments": ""})
                if getattr(tcd, "id", None):
                    tool_calls[idx]["id"] = tcd.id
                fn = getattr(tcd, "function", None)
                if fn and getattr(fn, "name", None):
                    tool_calls[idx]["name"] = fn.name
                if fn and getattr(fn, "arguments", None):
                    tool_calls[idx]["arguments"] += fn.arguments

        content = "".join(content_parts)

        if not tool_calls:
            yield {"type": "done", "answer": content, "trace": trace}
            return

        messages.append(
            {
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        specs = [
            (tc["name"], json.loads(tc["arguments"] or "{}"))
            for tc in tool_calls
        ]
        results = _execute_with_approval(handlers, specs, approver)

        for tc, (name, args), result in zip(tool_calls, specs, results):
            trace.append({"tool": name, "args": args, "result": str(result)})
            yield {
                "type": "tool",
                "tool": name,
                "args": args,
                "result": str(result),
            }
            messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": str(result)}
            )

    yield {
        "type": "done",
        "answer": "已达到最大迭代次数，任务可能未完成。",
        "trace": trace,
    }
