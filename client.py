import asyncio
import sys
import re
from typing import Optional, List, Dict
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
        self.sessions: List[ClientSession] = []
        self.exit_stack = AsyncExitStack()
        self.chat_history: List = []  # 添加记忆功能：存储历史消息

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")

        if not (is_python or is_js):
            raise ValueError("Server script must be a Python or JavaScript file.")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=None
        )

        print(f"Connecting to server: {server_script_path}")

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )

        await session.initialize()
        self.sessions.append(session)
        print(f"Connected to {server_script_path}")

    async def process_query(self, query: str):
        """Process a query using the available tools and LLM."""
        if not self.sessions:
            raise RuntimeError(
                "No client sessions initialized. Call connect_to_server first."
            )

        # 0. 解析并获取资源 (Resources) - 遍历所有会话
        resource_messages = []
        # 匹配 URI 格式，如 greeting://Alice, config://settings
        uris = re.findall(r"[a-zA-Z0-9]+://[^\s，。！？]+", query)
        for uri in uris:
            for session in self.sessions:
                try:
                    print(f"Fetching resource {uri} from session...")
                    resource_content = await session.read_resource(uri)
                    for content in resource_content.contents:
                        if hasattr(content, "text"):
                            resource_messages.append(
                                SystemMessage(
                                    content=f"Context from resource {uri}:\n{content.text}"
                                )
                            )
                    break  # 如果在一个会话中找到了，就跳出循环
                except Exception:
                    continue

        # 1. 获取并转换 MCP 工具为 OpenAI 格式 - 聚合所有会话的工具
        openai_tools = []
        tool_to_session: Dict[str, ClientSession] = {}
        
        for session in self.sessions:
            response = await session.list_tools()
            for tool in response.tools:
                input_schema = getattr(tool, "input_schema", None)
                if input_schema is None:
                    input_schema = getattr(tool, "inputSchema", None)

                # 记录工具名到会话的映射，以便后续调用
                tool_to_session[tool.name] = session
                
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

        # 3. 更新记忆：添加资源上下文和当前查询
        # 将资源信息作为系统消息加入历史（如果本次查询解析到了资源）
        for res_msg in resource_messages:
            self.chat_history.append(res_msg)
        
        # 添加用户当前查询
        self.chat_history.append(HumanMessage(content=query))

        # 4. 循环处理工具调用 (支持多轮 tool call)
        while True:
            # 使用完整的历史记录进行思考
            response = await llm.ainvoke(self.chat_history)
            self.chat_history.append(response)

            # 如果没有工具调用，说明 LLM 已经给出了最终回答
            if not response.tool_calls:
                break

            # 处理每个工具调用
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                args = tool_call["args"]
                tool_call_id = tool_call["id"]

                print(f"Calling tool: {tool_name} with args: {args}")

                # 从映射中找到对应的会话进行调用
                session = tool_to_session.get(tool_name)
                if session:
                    tool_result = await session.call_tool(tool_name, arguments=args)
                    result_content = str(tool_result.content)
                    self.chat_history.append(
                        ToolMessage(
                            content=result_content, tool_call_id=tool_call_id
                        )
                    )
                else:
                    self.chat_history.append(
                        ToolMessage(
                            content=f"Error: Tool {tool_name} not found.", tool_call_id=tool_call_id
                        )
                    )

        print(f"\nResult: {self.chat_history[-1].content}")
        return self.chat_history[-1].content

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script1> [path_to_server_script2 ...]")
        sys.exit(1)

    client = MCPClient()
    try:
        # 连接所有提供的 MCP 服务器
        for script_path in sys.argv[1:]:
            await client.connect_to_server(script_path)

        print(
            f"\nMCP Client connected to {len(client.sessions)} server(s). You can now ask questions. Type 'exit' or 'quit' to stop."
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
