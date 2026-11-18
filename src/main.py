import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rich.console import Console
from rich.panel import Panel

load_dotenv()
console = Console()

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = ROOT_DIR / "Workspace"
SERVER_SCRIPT = Path(__file__).resolve().parent / "mcp_server.py"

client = AsyncOpenAI(
    base_url=os.getenv("ollama_base", "http://localhost:11434/v1"),
    api_key=os.getenv("ollama_api"),
)
MODEL = os.getenv("ollama_model_deepseek")

SYSTEM_PROMPT = """You are Weaver, a grounded AI software engineer.
Rules:
1. Never guess file contents or directory state—always call `list_files` or `read_file` first.
2. Write clean, modular Python code using `write_file`.
3. Always verify your work by running the code or tests via `run_command` and fixing any errors before finishing."""


def mcp_to_openai_tools(mcp_tools) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", {}),
            },
        }
        for tool in mcp_tools
    ]

async def run_session(project_name: str):
    project_dir = (WORKSPACE_ROOT / project_name).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    # Pass target project path to the MCP subprocess
    server_env = os.environ.copy()
    server_env["WEAVER_PROJECT_DIR"] = str(project_dir)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
        env=server_env,
    )

    # Step 1: Session-wide in-memory message history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_resp = await session.list_tools()
            openai_tools = mcp_to_openai_tools(tools_resp.tools)

            console.print(
                Panel.fit(
                    f"[bold cyan]Weaver Step 1 Prototype[/bold cyan]\n"
                    f"Project: [green]{project_name}[/green] ({project_dir})\n"
                    f"Model:   [yellow]{MODEL}[/yellow]\n"
                    f"Tools:   {', '.join(t.name for t in tools_resp.tools)}",
                    border_style="cyan",
                )
            )

            while True:
                try:
                    user_input = console.input("\n[bold green]You >[/bold green] ").strip()
                except (EOFError, KeyboardInterrupt):
                    break

                if not user_input:
                    continue
                if user_input.lower() in {"exit", "quit"}:
                    break

                messages.append({"role": "user", "content": user_input})

                # Agentic tool-execution loop for this turn
                while True:
                    response = await client.chat.completions.create(
                        model=MODEL,
                        messages=messages,
                        tools=openai_tools,
                        temperature=0.0,  # Low temp to minimize hallucinated args/code
                    )
                    msg = response.choices[0].message
                    messages.append(msg.model_dump(exclude_none=True))

                    if not msg.tool_calls:
                        console.print(f"\n[bold cyan]Weaver >[/bold cyan]\n{msg.content}")
                        break

                    for tc in msg.tool_calls:
                        fn_name = tc.function.name
                        try:
                            fn_args = json.loads(tc.function.arguments or "{}")
                        except json.JSONDecodeError as e:
                            tool_output = f"ERROR: Invalid JSON arguments passed to tool: {e}"
                        else:
                            console.print(f"  [dim]⚙ Calling {fn_name}({list(fn_args.keys())})...[/dim]")
                            result = await session.call_tool(fn_name, fn_args)
                            tool_output = "\n".join(
                                c.text for c in result.content if hasattr(c, "text")
                            )

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": tool_output,
                            }
                        )


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else input("Enter project name: ").strip() or "demo_app"
    asyncio.run(run_session(proj))