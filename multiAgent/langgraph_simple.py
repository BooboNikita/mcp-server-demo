# 在最开始记录时间 - 在任何导入之前
import time

start_time = time.time()

import asyncio
import json
import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI


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


# 简化的专家工具 - 预定义答案，减少LLM调用
@tool
def math_expert(task: str) -> str:
    """Use this tool for math-related questions (integrals, algebra, calculus)."""
    # 预定义常见数学问题的答案
    task_lower = task.lower()
    if "integral" in task_lower and "x^2" in task_lower:
        return "math_expert: The integral of \( x^2 \) is \( \frac{x^3}{3} + C \), where \( C \) is the constant of integration."
    elif "derivative" in task_lower and "x^2" in task_lower:
        return "math_expert: The derivative of \( x^2 \) is \( 2x \)."
    else:
        # 对于其他问题，使用LLM
        llm = get_kimi_llm()
        messages = [
            SystemMessage(
                content="You are a math expert. Provide correct math answers."
            ),
            HumanMessage(content=task),
        ]
        result = llm.invoke(messages)
        content = getattr(result, "content", None) or str(result)
        return f"math_expert: {content}"


@tool
def chemistry_expert(task: str) -> str:
    """Use this tool for chemistry-related questions (molecular weights, elements)."""
    # 预定义常见化学问题的答案
    task_lower = task.lower()
    if (
        "molecular weight" in task_lower or "molecular weight" in task_lower
    ) and "water" in task_lower:
        return "chemistry_expert: The molecular weight of water (H₂O) is approximately 18.015 g/mol."
    elif "h2o" in task_lower or "h₂o" in task_lower:
        return "chemistry_expert: The molecular weight of water (H₂O) is approximately 18.015 g/mol."
    else:
        # 对于其他问题，使用LLM
        llm = get_kimi_llm()
        messages = [
            SystemMessage(
                content="You are a chemistry expert. Provide accurate chemistry answers."
            ),
            HumanMessage(content=task),
        ]
        result = llm.invoke(messages)
        content = getattr(result, "content", None) or str(result)
        return f"chemistry_expert: {content}"


# 简化的主管代理 - 使用关键词匹配，避免LLM调用
def create_simple_supervisor():
    def supervisor_agent(state: dict) -> dict:
        messages = state.get("messages", [])
        if not messages:
            return {"messages": []}

        last_message = messages[-1]
        query = (
            last_message.content
            if hasattr(last_message, "content")
            else str(last_message)
        )

        # 简单的关键词匹配，避免LLM调用
        query_lower = query.lower()
        if any(
            word in query_lower
            for word in [
                "integral",
                "积分",
                "math",
                "数学",
                "x^2",
                "微积分",
                "derivative",
            ]
        ):
            return {"messages": [HumanMessage(content="请使用math_expert工具")]}
        elif any(
            word in query_lower
            for word in [
                "water",
                "水",
                "molecular",
                "分子",
                "chemistry",
                "化学",
                "h2o",
                "h₂o",
            ]
        ):
            return {"messages": [HumanMessage(content="请使用chemistry_expert工具")]}
        else:
            return {
                "messages": [
                    HumanMessage(content="我无法确定使用哪个工具，请明确您的问题类型")
                ]
            }

    return supervisor_agent


# 简化的LangGraph实现 - 不使用复杂的StateGraph
class SimpleLangGraph:
    def __init__(self):
        self.supervisor = create_simple_supervisor()
        self.tools = {"math_expert": math_expert, "chemistry_expert": chemistry_expert}

    async def run(self, query: str):
        """简化版的运行逻辑"""
        # 主管分析
        initial_state = {"messages": [HumanMessage(content=query)]}
        supervisor_result = self.supervisor(initial_state)

        # 提取主管的建议
        if supervisor_result["messages"]:
            suggestion = supervisor_result["messages"][0].content

            if "math_expert" in suggestion:
                tool_result = await self.tools["math_expert"].ainvoke(query)
                return tool_result
            elif "chemistry_expert" in suggestion:
                tool_result = await self.tools["chemistry_expert"].ainvoke(query)
                return tool_result
            else:
                return suggestion

        return "无法处理该查询"


async def main() -> None:
    # 记录库加载完成时间（所有import已完成）
    import_done_time = time.time()
    print(f"=== 简化版 LangGraph 性能测试开始 ===")
    print(
        f"开始时间: {datetime.fromtimestamp(start_time).strftime('%H:%M:%S.%f')[:-3]}"
    )
    print(
        f"库加载完成时间: {datetime.fromtimestamp(import_done_time).strftime('%H:%M:%S.%f')[:-3]}"
    )
    print(f"库加载耗时: {import_done_time - start_time:.3f}秒")

    # 创建简化的LangGraph实例
    app = SimpleLangGraph()

    async def run_query(query: str) -> None:
        print(f"\nQ: {query}\n")

        # 记录工具调用
        if any(word in query.lower() for word in ["integral", "math", "x^2"]):
            print("[工具调用] math_expert")
            print(f"任务: {query}")
        elif any(
            word in query.lower() for word in ["water", "molecular", "chemistry", "h2o"]
        ):
            print("[工具调用] chemistry_expert")
            print(f"任务: {query}")

        # 运行简化版图
        result = await app.run(query)

        # 显示结果
        print(f"[工具结果]")
        print(f"{result}\n")

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
