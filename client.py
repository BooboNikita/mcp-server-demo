import asyncio
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

import os
from dotenv import load_dotenv

load_dotenv()

KIMI_API_KEY = os.getenv("KIMI_API_KEY")
KIMI_API_URL = os.getenv("KIMI_API_URL")


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")

        if not (is_python or is_js):
            raise ValueError("Server script must be a Python or JavaScript file.")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # response = await self.session.list_tools()
        # tools = response.tools
        # print("\n connect to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str):
        """Process a query using the available tools and LLM."""
        if self.session is None:
            raise RuntimeError(
                "Client session is not initialized. Call connect_to_server first."
            )

        # 1. 获取并转换 MCP 工具为 OpenAI 格式
        response = await self.session.list_tools()
        openai_tools = []
        for tool in response.tools:
            input_schema = getattr(tool, "input_schema", None)
            if input_schema is None:
                input_schema = getattr(tool, "inputSchema", None)

            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": input_schema,
                    },
                }
            )

        # 2. 初始化 LLM 并绑定工具
        llm = ChatOpenAI(
            model_name="kimi-latest",
            openai_api_key=KIMI_API_KEY,
            openai_api_base=KIMI_API_URL,
            temperature=0,  # 设为 0 以获得更稳定的工具调用
        ).bind_tools(openai_tools)

        # 3. 会话消息列表
        messages = [HumanMessage(content=query)]

        # 4. 循环处理工具调用 (支持多轮 tool call)
        while True:
            response = await llm.ainvoke(messages)
            messages.append(response)

            # 如果没有工具调用，说明 LLM 已经给出了最终回答
            if not response.tool_calls:
                break

            # 处理每个工具调用
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                args = tool_call["args"]
                tool_call_id = tool_call["id"]

                print(f"Calling tool: {tool_name} with args: {args}")

                # 调用 MCP 服务器工具
                tool_result = await self.session.call_tool(tool_name, arguments=args)

                # 将结果添加回消息列表
                messages.append(
                    ToolMessage(
                        content=str(tool_result.content), tool_call_id=tool_call_id
                    )
                )

        print(f"\nResult: {messages[-1].content}")
        return messages[-1].content

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        # Connect to the MCP server
        await client.connect_to_server(sys.argv[1])

        print(
            "\nMCP Client connected. You can now ask questions. Type 'exit' or 'quit' to stop."
        )

        while True:
            try:
                # Use query as a prompt for the user
                query = input("\nQuery > ").strip()

                if query.lower() in ["exit", "quit"]:
                    break

                if not query:
                    continue

                await client.process_query(query)

            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")

    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())
