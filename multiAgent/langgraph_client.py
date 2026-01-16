# 在最开始记录时间 - 在任何导入之前
import time

start_time = time.time()

import asyncio
import json
import os
from datetime import datetime
from typing import Annotated, List, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


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


# 定义状态类型
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


# 创建专家工具
@tool
def math_expert(task: str) -> str:
    """Use this tool for math-related questions (integrals, algebra, calculus)."""
    llm = get_kimi_llm()
    messages = [
        SystemMessage(content="You are a math expert. Provide correct math answers."),
        HumanMessage(content=task),
    ]
    result = llm.invoke(messages)
    content = getattr(result, "content", None) or str(result)
    return f"math_expert: {content}"


@tool
def chemistry_expert(task: str) -> str:
    """Use this tool for chemistry-related questions (molecular weights, elements)."""
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


def create_supervisor_agent():
    """创建主管代理"""
    llm = get_kimi_llm()
    tools = [math_expert, chemistry_expert]
    llm_with_tools = llm.bind_tools(tools)

    def supervisor_agent(state: AgentState) -> dict:
        messages = state["messages"]

        # 使用LLM来判断应该调用哪个工具
        system_message = SystemMessage(
            content="""你是一个智能路由代理。分析用户的问题并决定应该调用哪个专家工具。
            
            可用工具：
            - math_expert: 用于数学相关问题（积分、代数、微积分等）
            - chemistry_expert: 用于化学相关问题（分子量、元素等）
            
            如果问题需要多个工具，请按顺序调用。
            如果问题不需要任何工具，直接回答。"""
        )

        messages_with_system = [system_message] + messages
        response = llm_with_tools.invoke(messages_with_system)

        return {"messages": [response]}

    return supervisor_agent


def create_expert_node(tool_func, tool_name: str):
    """创建专家节点"""

    def expert_agent(state: AgentState) -> dict:
        messages = state["messages"]
        last_message = messages[-1]

        # 提取工具调用的参数
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call = last_message.tool_calls[0]
            args = tool_call.get("args", {})
            task = args.get("task", "")

            # 调用专家工具
            result = tool_func.invoke(task)

            # 创建工具消息响应
            tool_message = HumanMessage(
                content=result, additional_kwargs={"tool_call_id": tool_call.get("id")}
            )

            return {"messages": [tool_message]}

        return {"messages": []}

    return expert_agent


async def main() -> None:
    # 记录库加载完成时间（所有import已完成）
    import_done_time = time.time()
    print(f"=== LangGraph 性能测试开始 ===")
    print(
        f"开始时间: {datetime.fromtimestamp(start_time).strftime('%H:%M:%S.%f')[:-3]}"
    )
    print(
        f"库加载完成时间: {datetime.fromtimestamp(import_done_time).strftime('%H:%M:%S.%f')[:-3]}"
    )
    print(f"库加载耗时: {import_done_time - start_time:.3f}秒")

    # 创建图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("supervisor", create_supervisor_agent())
    workflow.add_node("tools", ToolNode([math_expert, chemistry_expert]))

    # 添加边
    workflow.add_edge(START, "supervisor")

    # 条件边：根据是否有工具调用来决定
    def should_continue(state: AgentState) -> str:
        messages = state["messages"]
        last_message = messages[-1]

        # 如果有工具调用，去tools节点
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        else:
            return END

    workflow.add_conditional_edges("supervisor", should_continue, ["tools", END])
    workflow.add_edge("tools", "supervisor")

    # 编译图
    app = workflow.compile()

    async def run_query(query: str) -> None:
        print(f"\nQ: {query}\n")

        # 创建初始消息
        messages = [HumanMessage(content=query)]

        # 运行图
        final_state = None
        async for step in app.astream({"messages": messages}):
            for node_name, state in step.items():
                if node_name == "supervisor":
                    messages = state.get("messages", [])
                    if messages:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            for tool_call in last_msg.tool_calls:
                                tool_name = tool_call.get("name", "")
                                args = tool_call.get("args", {})
                                print(f"[工具调用] {tool_name}")
                                print(f"{_pretty_json(args)}\n")
                        elif hasattr(last_msg, "content") and last_msg.content:
                            if "工具" not in last_msg.content:
                                print(f"[主管] 分析中...")

                elif node_name == "tools":
                    messages = state.get("messages", [])
                    if messages:
                        for msg in messages:
                            if hasattr(msg, "content") and msg.content:
                                print(f"[工具结果]")
                                print(f"{msg.content}\n")

                final_state = state

        # 显示最终响应
        if final_state and final_state.get("messages"):
            last_message = final_state["messages"][-1]
            if hasattr(last_message, "content") and last_message.content:
                if not any(
                    tool in last_message.content
                    for tool in ["math_expert", "chemistry_expert"]
                ):
                    print(f"答复:\n{last_message.content}\n")

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
