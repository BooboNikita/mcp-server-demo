import os
import sys
# Add project root to sys.path to allow running as script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from python_a2a import agent, skill
import uvicorn
from dotenv import load_dotenv
from src.a2a.protocol import ChatCompletionRequest
from src.a2a.utils import handle_proxy_request, handle_chat_completion

load_dotenv()

llm = ChatOpenAI(
    model_name="kimi-latest",
    openai_api_key=os.getenv("KIMI_API_KEY"),
    openai_api_base=os.getenv("KIMI_API_URL"),
    temperature=0
)

@agent(name="Receptionist", description="分析客户问题类型并路由到合适的专家")
class ReceptionistAgent:
    @skill(
        name="意图分类",
        description="分析用户问题并输出 TECHNICAL 或 SALES 分类",
        tags=["routing", "classification"],
        examples=["你们的报价是多少？", "如何优化数据库索引？"]
    )
    async def classify(self, question: str) -> str:
        classify_prompt = f"分析用户输入并返回分类（TECHNICAL/SALES/GENERAL）。仅返回单词本身，不要包含标点符号。\n用户输入: {question}"
        response = await llm.ainvoke([SystemMessage(content=classify_prompt)])
        result = response.content.strip().upper()
        # 提取第一个匹配的关键词，防止模型输出多余解释
        for key in ["TECHNICAL", "SALES", "GENERAL"]:
            if key in result:
                return key
        return "GENERAL"

receptionist_agent = ReceptionistAgent()

app = FastAPI(title="Receptionist Orchestrator Service")

AGENT_ENDPOINTS = {
    "TECHNICAL": "http://localhost:8001/v1/chat/completions",
    "SALES": "http://localhost:8005/v1/chat/completions"
}

@app.post("/v1/chat/completions")
async def orchestrate(request: ChatCompletionRequest):
    user_msg = request.messages[-1].content
    
    category = await receptionist_agent.classify(user_msg)
    target_url = AGENT_ENDPOINTS.get(category)
    
    if not target_url:
        system_prompt = "你是一个亲切的接待员。请礼貌地回应用户的日常问候或通用问题，并告知他们你可以提供技术咨询（路由给技术专家）或产品销售咨询（路由给销售顾问）。"
        return await handle_chat_completion(request, llm, system_prompt)

    return await handle_proxy_request(target_url, request.model_dump(), request.stream)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
