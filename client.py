import asyncio
import sys
import os
from typing import List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.agents import create_agent
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

KIMI_API_KEY = os.getenv("KIMI_API_KEY")
KIMI_API_URL = os.getenv("KIMI_API_URL")


class MCPClientApp:
    def __init__(self, server_config: dict):
        self.mcp_client = MultiServerMCPClient(server_config)
        self.history = InMemoryChatMessageHistory()
        self.llm = ChatOpenAI(
            model_name="kimi-latest",
            openai_api_key=KIMI_API_KEY,
            openai_api_base=KIMI_API_URL,
            temperature=0,
        )

    async def initialize(self):
        """初始化连接。"""
        # MultiServerMCPClient 在 get_tools 时会自动初始化连接
        pass

    async def process_query(self, query: str, stream: bool = True):
        """使用 LangChain Agent 处理查询。"""
        # 1. 获取所有服务器的工具
        tools = await self.mcp_client.get_tools()

        if not tools:
            print("Warning: No tools found from MCP servers.")

        # 2. 定义消息列表 (包括 System Message)
        system_message = SystemMessage(
            content="You are a helpful assistant. Use the provided tools to answer the user's questions."
        )

        # 3. 创建 Agent
        agent = create_agent(self.llm, tools=tools)

        messages = (
            [system_message] + self.history.messages + [HumanMessage(content=query)]
        )

        try:
            if stream:
                output_parts: List[str] = []
                async for event in agent.astream_events(
                    {"messages": messages}, version="v2"
                ):
                    event_type = event.get("event")
                    if event_type in ("on_chat_model_stream", "on_llm_stream"):
                        chunk = (event.get("data") or {}).get("chunk")
                        text = getattr(chunk, "content", None)
                        if text:
                            print(text, end="", flush=True)
                            output_parts.append(str(text))

                output = "".join(output_parts)
                print("")
            else:
                result = await agent.ainvoke({"messages": messages})
                last_message = result["messages"][-1]
                output = (
                    last_message.content
                    if hasattr(last_message, "content")
                    else str(last_message)
                )
                print(f"\nResult: {output}")

            self.history.add_message(HumanMessage(content=query))
            self.history.add_message(AIMessage(content=output))
            return output
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Error during agent execution: {e}")
            return str(e)

    async def cleanup(self):
        """清理资源。"""
        # MultiServerMCPClient 内部会处理 aclose
        # await self.mcp_client.aclose()
        pass


async def main():
    # 使用用户提供的配置
    server_config = {
        "database": {
            "transport": "streamable_http",
            "url": "http://localhost:8000/mcp",
        },
        "compliance-warning": {
            "transport": "streamable_http",
            "url": "http://localhost:8001/mcp",
        },
    }

    app = MCPClientApp(server_config)

    try:
        print(
            "\nMCP Client (using MultiServerMCPClient) started. You can now ask questions. Type 'exit' or 'quit' to stop."
        )

        while True:
            try:
                query = input("\nQuery > ").strip()

                if query.lower() in ["exit", "quit"]:
                    break

                if not query:
                    continue

                await app.process_query(query, stream=True)

            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")

    finally:
        await app.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
