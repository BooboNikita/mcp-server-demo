# 在最开始记录时间 - 在任何导入之前
import time

start_time = time.time()

import asyncio
import json
import os
from datetime import datetime

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


def get_kimi_llm() -> ChatOpenAI:
    load_dotenv()

    kimi_api_key = os.getenv("KIMI_API_KEY")
    kimi_api_url = os.getenv("KIMI_API_URL")
    kimi_model = os.getenv("KIMI_MODEL") or "kimi-latest"

    if not kimi_api_key:
        raise ValueError("Missing env var: KIMI_API_KEY")
    if not kimi_api_url:
        raise ValueError("Missing env var: KIMI_API_URL")

    return ChatOpenAI(
        model_name=kimi_model,
        openai_api_key=kimi_api_key,
        openai_api_base=kimi_api_url,
        temperature=0,
    )


def _pretty_json(value: object) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return value
    return json.dumps(value, ensure_ascii=False, indent=2)


async def main() -> None:
    # 记录库加载完成时间（所有import已完成）
    import_done_time = time.time()
    print(f"=== LangChain 性能测试开始 ===")
    print(
        f"开始时间: {datetime.fromtimestamp(start_time).strftime('%H:%M:%S.%f')[:-3]}"
    )
    print(
        f"库加载完成时间: {datetime.fromtimestamp(import_done_time).strftime('%H:%M:%S.%f')[:-3]}"
    )
    print(f"库加载耗时: {import_done_time - start_time:.3f}秒")

    expert_llm = get_kimi_llm()

    math_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a math expert. Provide correct math answers."),
            ("human", "{task}"),
        ]
    )
    chemistry_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a chemistry expert. Provide accurate chemistry answers.",
            ),
            ("human", "{task}"),
        ]
    )

    math_chain = math_prompt | expert_llm
    chemistry_chain = chemistry_prompt | expert_llm

    @tool
    async def math_expert(task: str) -> str:
        """Use this tool for math-related questions (integrals, algebra, calculus)."""
        result = await math_chain.ainvoke({"task": task})
        content = getattr(result, "content", None) or str(result)
        return f"math_expert: {content}"

    @tool
    async def chemistry_expert(task: str) -> str:
        """Use this tool for chemistry-related questions (molecular weights, elements)."""
        result = await chemistry_chain.ainvoke({"task": task})
        content = getattr(result, "content", None) or str(result)
        return f"chemistry_expert: {content}"

    controller_llm = get_kimi_llm()
    agent = create_agent(controller_llm, tools=[math_expert, chemistry_expert])

    async def run_query(query: str) -> None:
        print(f"\nQ: {query}\n")

        system_message = SystemMessage(
            content="You are a general assistant. Use expert tools when needed."
        )
        messages = [system_message, HumanMessage(content=query)]

        output_parts: list[str] = []
        async for event in agent.astream_events({"messages": messages}, version="v2"):
            event_type = event.get("event")

            if event_type == "on_tool_start":
                name = event.get("name") or "tool"
                tool_input = (event.get("data") or {}).get("input")
                if tool_input is not None:
                    print(f"[工具调用] {name}\n{_pretty_json(tool_input)}\n")
                else:
                    print(f"[工具调用] {name}\n")
                continue

            if event_type == "on_tool_end":
                name = event.get("name") or "tool"
                tool_output = (event.get("data") or {}).get("output")
                if tool_output is not None:
                    print(f"[工具结果] {name}\n{tool_output}\n")
                else:
                    print(f"[工具结果] {name}\n")
                continue

            if event_type in ("on_chat_model_stream", "on_llm_stream"):
                chunk = (event.get("data") or {}).get("chunk")
                text = getattr(chunk, "content", None)
                if text:
                    output_parts.append(str(text))
                continue

        output = "".join(output_parts).strip()
        if output:
            print(f"答复:\n{output}\n")

    # 记录实际执行开始时间
    execution_start_time = time.time()
    print(f"\n=== 正文代码执行开始 ===")
    print(
        f"执行开始时间: {datetime.fromtimestamp(execution_start_time).strftime('%H:%M:%S.%f')[:-3]}"
    )

    await run_query("What is the integral of x^2?")
    await run_query("What is the molecular weight of water?")

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


if __name__ == "__main__":
    asyncio.run(main())
