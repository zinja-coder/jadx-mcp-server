#!/usr/bin/env python3
"""
Example: drive jadx-mcp-server from any OpenAI-compatible chat endpoint.

MCP-aware desktop apps (Claude Desktop, Cherry Studio, LM Studio) speak MCP
directly. Everything else - OpenRouter, LiteLLM, vLLM, Ollama's OpenAI layer,
OmniRoute and friends - speaks `POST /v1/chat/completions` and only needs a
small adapter, which is all this file is:

  1. connect to a running `jadx_mcp_server.py --http` through fastmcp
  2. convert the MCP tool list into OpenAI's function-calling `tools` schema
  3. run the usual loop: ask the model -> execute the tool calls it returns
     against the MCP server -> feed the results back -> repeat until it answers

Start the server first:

    uv run jadx_mcp_server.py --http --host 127.0.0.1 --port 9000 --jadx-port 8650

Then point this client at any OpenAI-compatible endpoint:

    # OpenAI itself
    OPENAI_API_KEY=sk-... python examples/openai_compatible_client.py \
        --prompt "What does com.example.app.MainActivity do?"

    # a local gateway (any placeholder works as the key)
    OPENAI_BASE_URL=http://127.0.0.1:11434/v1 OPENAI_API_KEY=ollama \
    OPENAI_MODEL=llama3.1 python examples/openai_compatible_client.py

    # see exactly what the model is offered, without calling a model at all
    python examples/openai_compatible_client.py --list-tools

Run without --prompt for an interactive session. Needs the `openai` SDK:

    pip install -r examples/requirements.txt

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Callable, Iterable, List

from fastmcp import Client

try:
    from openai import AsyncOpenAI
except ImportError:  # the server never needs this; only this example does
    AsyncOpenAI = None

DEFAULT_MCP_URL = "http://127.0.0.1:9000/mcp"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are a reverse-engineering assistant working with JADX MCP tools that "
    "read a live jadx-gui project. Answer from tool output instead of guessing: "
    "list packages or search for classes first, then read the source of the "
    "classes that matter. Kotlin metadata annotations are already stripped from "
    "the source you receive. Keep answers short and name the classes and methods "
    "you relied on."
)


def tool_schema(tool: Any) -> dict:
    """Read a tool's JSON schema across fastmcp versions."""
    return (
        getattr(tool, "input_schema", None)
        or getattr(tool, "inputSchema", None)
        or {"type": "object", "properties": {}}
    )


def as_openai_tools(tools: Iterable[Any]) -> List[dict]:
    """MCP tools -> the `tools` list the OpenAI chat API expects."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": (tool.description or "").strip() or f"JADX MCP tool {tool.name}",
                "parameters": tool_schema(tool),
            },
        }
        for tool in tools
    ]


def result_to_text(result: Any) -> str:
    """Flatten an MCP tool result into text the model can read."""
    blocks = getattr(result, "content", None) or []
    text = "\n".join(getattr(block, "text", "") for block in blocks if getattr(block, "text", ""))
    return text or str(result)


async def run_turn(
    client: Client,
    model_client: Any,
    model: str,
    messages: List[Any],
    tools: List[Any],
    max_steps: int,
    max_tool_chars: int,
    log: Callable[[str], None],
) -> str:
    """Let the model call tools until it produces a final answer."""
    for _ in range(max_steps):
        completion = await model_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        message = completion.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            return message.content or "(the model returned no content)"

        for call in message.tool_calls:
            function = getattr(call, "function", None)
            if function is None:  # a custom tool call: not something we offer
                continue
            try:
                arguments = json.loads(function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
            log(f"tool -> {function.name}({json.dumps(arguments, ensure_ascii=False)[:160]})")

            try:
                output = result_to_text(await client.call_tool(function.name, arguments))
            except Exception as error:  # a bad tool call should not end the session
                output = f"ERROR while calling {function.name}: {error}"
            if len(output) > max_tool_chars:
                output = output[:max_tool_chars] + f"\n... [truncated, {len(output)} chars in total]"
            log(f"tool <- {len(output)} chars")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output})

    return f"(stopped: the model kept calling tools past --max-steps {max_steps})"


async def run(args: argparse.Namespace) -> int:
    log = (lambda text: None) if args.quiet else (lambda text: print(text, file=sys.stderr))

    async with Client(args.mcp_url) as client:
        tools = as_openai_tools(await client.list_tools())
        log(f"connected to {args.mcp_url}: {len(tools)} MCP tools exposed to the model")

        if args.list_tools:
            print(json.dumps(tools, indent=2))
            return 0

        if AsyncOpenAI is None:
            # --list-tools works without the SDK; an actual model call cannot.
            print(
                "This example needs the OpenAI SDK (the MCP server itself does not).\n"
                "Install it with: pip install -r examples/requirements.txt",
                file=sys.stderr,
            )
            return 2

        model_client = AsyncOpenAI(base_url=args.base_url, api_key=args.api_key)
        messages: List[Any] = [{"role": "system", "content": args.system_prompt}]
        pending = [args.prompt] if args.prompt else None

        while True:
            if pending is not None:
                if not pending:
                    break
                question = pending.pop(0)
            else:
                try:
                    question = input("you> ")
                except EOFError:
                    break
                if not question.strip():
                    continue

            messages.append({"role": "user", "content": question})
            answer = await run_turn(
                client, model_client, args.model, messages, tools,
                args.max_steps, args.max_tool_chars, log,
            )
            print(f"\n{answer}\n")

    return 0


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Drive jadx-mcp-server from any OpenAI-compatible chat endpoint.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--mcp-url", default=os.environ.get("JADX_MCP_URL", DEFAULT_MCP_URL),
                        help="streamable-http endpoint of jadx_mcp_server.py --http")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL),
                        help="OpenAI-compatible /v1 endpoint (OpenRouter, LiteLLM, vLLM, Ollama, ...)")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"),
                        help="API key; for local gateways any placeholder will do")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--prompt", help="ask one question and exit; omit for an interactive session")
    parser.add_argument("--system-prompt", default=SYSTEM_PROMPT)
    parser.add_argument("--max-steps", type=int, default=12,
                        help="most tool-calling rounds allowed per question")
    parser.add_argument("--max-tool-chars", type=int, default=20000,
                        help="truncate a single tool result to this many characters")
    parser.add_argument("--list-tools", action="store_true",
                        help="print the OpenAI tool schema the model is offered, then exit")
    parser.add_argument("--quiet", action="store_true", help="do not trace tool calls on stderr")
    args = parser.parse_args(argv)

    if not args.api_key and not args.list_tools:
        parser.error("no API key: pass --api-key or set OPENAI_API_KEY "
                     "(a placeholder is fine for local gateways)")
    return args


def main() -> int:
    try:
        return asyncio.run(run(parse_args()))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
