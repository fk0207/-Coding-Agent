"""工具模块：定义 agent 可用的工具（读文件 / 写文件 / 执行命令 / 向用户提问）及其 schema。"""
import subprocess


def read_file(path: str) -> str:
    """读取指定路径文件的文本内容。"""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_file(path: str, content: str) -> str:
    """将内容写入指定路径文件（覆盖写），返回确认信息。"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"已写入文件: {path}"


def run_command(command: str, timeout: int = 30) -> str:
    """执行 shell 命令并返回 stdout/stderr（超时返回提示）。"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (result.stdout + result.stderr).strip() or "(无输出)"
    except subprocess.TimeoutExpired:
        return f"命令超时（>{timeout}s）: {command}"








# OpenAI function calling 格式的工具 schema
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定路径文件的文本内容",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "文件路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "将内容写入指定路径文件（覆盖写）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "要写入的内容"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "执行 shell 命令并返回 stdout/stderr",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "要执行的 shell 命令"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "向用户提问，获取用户的回答。当需要用户澄清需求、做出选择或补充信息时使用。",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string", "description": "要问用户的问题"}},
                "required": ["question"],
            },
        },
    },
]


# 工具名 -> 实现函数 的映射
HANDLERS = {
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
}


# 危险工具集合：调用前需用户同意
DANGEROUS_TOOLS = {"run_command", "write_file"}


def is_dangerous(name: str) -> bool:
    """判断工具是否危险（危险工具调用前需用户同意）。"""
    return name in DANGEROUS_TOOLS
