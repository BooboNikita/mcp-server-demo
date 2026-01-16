# 在最开始记录时间 - 在任何导入之前
import time

start_time = time.time()

import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.tools import AgentTool
from autogen_agentchat.messages import (
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient


def get_model_client() -> OpenAIChatCompletionClient:
    load_dotenv()

    kimi_api_key = os.getenv("KIMI_API_KEY")
    kimi_api_url = os.getenv("KIMI_API_URL")
    if not kimi_api_key:
        raise ValueError("Missing env var: KIMI_API_KEY")
    if not kimi_api_url:
        raise ValueError("Missing env var: KIMI_API_URL")

    model_client = OpenAIChatCompletionClient(
        model="kimi-latest",
        api_key=kimi_api_key,
        base_url=kimi_api_url,
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "structured_output": False,
            "family": "unknown",
        },
        temperature=0,
    )

    return model_client


def _maybe_pretty_json(value: str) -> str:
    try:
        obj = json.loads(value)
    except Exception:
        return value
    return json.dumps(obj, ensure_ascii=False, indent=2)


async def print_stream(stream) -> None:
    async for message in stream:
        if isinstance(message, TextMessage):
            if message.source == "user":
                print(f"\nQ: {message.content}\n")
            else:
                print(f"{message.content}\n")
            continue

        if isinstance(message, ToolCallRequestEvent):
            for call in message.content:
                args = _maybe_pretty_json(call.arguments)
                print(f"[工具调用] {call.name}\n{args}\n")
            continue

        if isinstance(message, ToolCallExecutionEvent):
            for r in message.content:
                status = "ERROR" if r.is_error else "OK"
                print(f"[工具结果] {r.name} ({status})\n{r.content}\n")
            continue

        if isinstance(message, ToolCallSummaryMessage):
            print(f"答复:\n{message.content}\n")
            continue


async def main() -> None:
    # 记录库加载完成时间（所有import已完成）
    import_done_time = time.time()
    print(f"=== AutoGen 性能测试开始 ===")
    print(
        f"开始时间: {datetime.fromtimestamp(start_time).strftime('%H:%M:%S.%f')[:-3]}"
    )
    print(
        f"库加载完成时间: {datetime.fromtimestamp(import_done_time).strftime('%H:%M:%S.%f')[:-3]}"
    )
    print(f"库加载耗时: {import_done_time - start_time:.3f}秒")

    model_client = get_model_client()

    math_agent = AssistantAgent(
        "math_expert",
        model_client=model_client,
        system_message="You are a math expert.",
        description="A math expert assistant.",
        model_client_stream=True,
    )
    math_agent_tool = AgentTool(math_agent)

    chemistry_agent = AssistantAgent(
        "chemistry_expert",
        model_client=model_client,
        system_message="You are a chemistry expert.",
        description="A chemistry expert assistant.",
        model_client_stream=True,
    )
    chemistry_agent_tool = AgentTool(chemistry_agent)

    agent = AssistantAgent(
        "assistant",
        system_message="You are a general assistant. Use expert tools when needed.",
        model_client=model_client,
        model_client_stream=True,
        tools=[math_agent_tool, chemistry_agent_tool],
    )
    # 记录实际执行开始时间
    execution_start_time = time.time()
    print(f"\n=== 正文代码执行开始 ===")
    print(
        f"执行开始时间: {datetime.fromtimestamp(execution_start_time).strftime('%H:%M:%S.%f')[:-3]}"
    )

    await print_stream(agent.run_stream(task="What is the integral of x^2?"))
    await print_stream(agent.run_stream(task="What is the molecular weight of water?"))

    # 记录结束时间
    end_time = time.time()
    print(f"\n=== 性能测试结束 ===")
    print(f"结束时间: {datetime.fromtimestamp(end_time).strftime('%H:%M:%S.%f')[:-3]}")
    print(f"正文代码执行耗时: {end_time - execution_start_time:.3f}秒")
    print(f"总耗时: {end_time - start_time:.3f}秒")
    print(
        f"库加载占比: {((import_done_time - start_time) / (end_time - start_time) * 100):.1f}%"
    )
    print(
        f"正文代码占比: {((end_time - execution_start_time) / (end_time - start_time) * 100):.1f}%"
    )


asyncio.run(main())
