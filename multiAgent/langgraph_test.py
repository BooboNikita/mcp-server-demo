from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from youdotcom import You

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver


class SearchState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str      # 经过LLM理解后的用户需求总结
    search_query: str    # 优化后用于Tavily API的搜索查询
    search_results: str  # Tavily搜索返回的结果
    final_answer: str    # 最终生成的答案
    step: str            # 标记当前步骤

load_dotenv()

# 初始化模型
# 我们将使用这个 llm 实例来驱动所有节点的智能
KIMI_API_KEY = os.getenv("KIMI_API_KEY")
KIMI_API_URL = os.getenv("KIMI_API_URL")

llm = ChatOpenAI(
    model_name="kimi-latest",
    openai_api_key=KIMI_API_KEY,
    openai_api_base=KIMI_API_URL,
    temperature=0.7
)
# 初始化You.com客户端
YOU_API_KEY = os.getenv("TAVILY_API_KEY")  # 使用相同的API key变量名
if YOU_API_KEY and YOU_API_KEY.startswith("ydc-sk-"):
    try:
        you_client = You(YOU_API_KEY)
        print(f"✅ You.com客户端初始化成功")
    except Exception as e:
        print(f"⚠️  You.com客户端初始化失败: {e}")
        you_client = None
else:
    you_client = None
    if YOU_API_KEY:
        print(f"⚠️  You.com API key格式不正确，期望以'ydc-sk-'开头，但得到：{YOU_API_KEY[:10]}...")
    else:
        print("⚠️  You.com API key未设置")

def understand_query_node(state: SearchState) -> dict:
    """步骤1：理解用户查询并生成搜索关键词"""
    user_message = state["messages"][-1].content
    
    # 使用LangGraph原生消息历史（窗口设为最近5条消息）
    messages = state["messages"]
    recent_messages = messages[-5:] if len(messages) > 5 else messages
    
    # 构建对话历史上下文
    history_context = ""
    if len(recent_messages) > 1:  # 如果有历史消息
        history_context = "之前的对话历史（最近5条消息）：\n"
        for i, msg in enumerate(recent_messages[:-1], 1):  # 排除当前消息
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            history_context += f"{i}. {role}：{content}\n"
        history_context += "\n"
    
    understand_prompt = f"""{history_context}当前用户查询："{user_message}"

请完成两个任务：
1. 简洁总结用户想要了解什么（结合对话历史理解上下文）
2. 生成最适合搜索引擎的关键词（中英文均可，要精准）

格式：
理解：[用户需求总结]
搜索词：[最佳搜索关键词]"""

    response = llm.invoke([SystemMessage(content=understand_prompt)])
    response_text = response.content
    
    # 解析LLM的输出，提取搜索关键词
    search_query = user_message # 默认使用原始查询
    if "搜索词：" in response_text:
        search_query = response_text.split("搜索词：")[1].strip()
    
    return {
        "user_query": response_text,
        "search_query": search_query,
        "step": "understood",
        "messages": [AIMessage(content=f"我将为您搜索：{search_query}")]
    }

def you_search_node(state: SearchState) -> dict:
    """步骤2：使用You.com API进行真实搜索"""
    search_query = state["search_query"]
    try:
        print(f"🔍 正在搜索: {search_query}")
        
        # 检查You.com客户端是否已初始化
        if not you_client:
            print("⚠️  You.com客户端未初始化，将使用LLM知识库回答")
            return {
                "search_results": "You.com API配置问题，将使用LLM知识库回答",
                "step": "search_failed",
                "messages": [AIMessage(content="⚠️  You.com API配置问题，将使用我的知识库回答...")]
            }
        
        # 使用You.com统一搜索API
        response = you_client.search.unified(query=search_query, count=5)
        
        # 处理和格式化搜索结果
        search_results = ""
        
        # 处理网页搜索结果
        if hasattr(response, 'results') and hasattr(response.results, 'web'):
            for i, result in enumerate(response.results.web, 1):
                title = getattr(result, 'title', '')
                description = getattr(result, 'description', '')
                url = getattr(result, 'url', '')
                search_results += f"{i}. {title}\n{description}\n来源: {url}\n\n"
        
        # 处理新闻搜索结果
        if hasattr(response, 'results') and hasattr(response.results, 'news'):
            if response.results.news:
                search_results += "\n📰 相关新闻:\n"
                for i, result in enumerate(response.results.news, 1):
                    title = getattr(result, 'title', '')
                    description = getattr(result, 'description', '')
                    url = getattr(result, 'url', '')
                    search_results += f"{i}. {title}\n{description}\n来源: {url}\n\n"
        
        if not search_results:
            search_results = "未找到相关搜索结果"

        print('search_result', search_results)
        
        return {
            "search_results": search_results,
            "step": "searched",
            "messages": [AIMessage(content="✅ 搜索完成！正在整理答案...")]
        }
    except Exception as e:
        import traceback
        error_msg = f"搜索失败：{e}"
        print(f"❌ {error_msg}")
        print("💡 将使用LLM知识库作为备选方案")
        traceback.print_exc()
        return {
            "search_results": error_msg,
            "step": "search_failed",
            "messages": [AIMessage(content="❌ 搜索遇到问题...")]
        }

def generate_answer_node(state: SearchState) -> dict:
    """步骤3：基于搜索结果生成最终答案"""
    if state["step"] == "search_failed":
        # 如果搜索失败，执行回退策略，基于LLM自身知识回答
        fallback_prompt = f"搜索API暂时不可用，请基于您的知识回答用户的问题：\n用户问题：{state['user_query']}"
        response = llm.invoke([SystemMessage(content=fallback_prompt)])
    else:
        # 搜索成功，基于搜索结果生成答案
        answer_prompt = f"""基于以下搜索结果为用户提供完整、准确的答案：
用户问题：{state['user_query']}
搜索结果：\n{state['search_results']}
请综合搜索结果，提供准确、有用的回答..."""
        print(f"🔧 正在生成答案...提示词：\n{answer_prompt}")
        response = llm.invoke([SystemMessage(content=answer_prompt)])
    
    return {
        "final_answer": response.content,
        "step": "completed",
        "messages": [AIMessage(content=response.content)]
    }

def create_search_assistant():
    workflow = StateGraph(SearchState)
    
    # 添加节点
    workflow.add_node("understand", understand_query_node)
    workflow.add_node("search", you_search_node)
    workflow.add_node("answer", generate_answer_node)
    
    # 设置线性流程
    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "search")
    workflow.add_edge("search", "answer")
    workflow.add_edge("answer", END)
    
    # 编译图
    memory = InMemorySaver()
    app = workflow.compile(checkpointer=memory)
    return app


async def main():
    """主函数：运行搜索助手"""
    print("🚀 初始化搜索助手...")
    app = create_search_assistant()
    
    # 检查You.com API key状态
    if not YOU_API_KEY:
        print("⚠️  You.com API key未设置，搜索功能将使用LLM知识库")
    else:
        print("✅ You.com API key已设置，将使用实时搜索功能")
    
    print("✅ 搜索助手已就绪！输入您的问题（输入 'exit' 或 'quit' 退出）")
    print("💡 提示：我会通过 LangGraph 原生 Memory 记住最近 5 条消息的上下文")
    
    while True:
        try:
            user_input = input("\n🔍 请输入您的问题 > ").strip()
            
            if user_input.lower() in ["exit", "quit"]:
                print("👋 再见！")
                break
                
            if not user_input:
                continue
            
            # 创建初始状态
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "user_query": "",
                "search_query": "",
                "search_results": "",
                "final_answer": "",
                "step": "start"
            }
            
            # 运行工作流
            print("\n🤔 正在处理您的问题...")
            final_state = await app.ainvoke(initial_state, config={"configurable": {"thread_id": "1"}})
            
            # 显示最终结果
            print(f"\n💡 答案：{final_state['final_answer']}")
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 发生错误：{e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

