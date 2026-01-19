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
from src.a2a.utils import handle_chat_completion

load_dotenv()

llm = ChatOpenAI(
    model_name="kimi-latest",
    openai_api_key=os.getenv("KIMI_API_KEY"),
    openai_api_base=os.getenv("KIMI_API_URL"),
    temperature=0
)

@agent(name="SalesConsultant", description="处理价格咨询、商务合作和产品价值传递")
class SalesConsultantAgent:
    @skill(
        name="销售咨询",
        description="解答报价、合作与产品价值问题",
        tags=["sales", "pricing", "partnership"],
        examples=["你们的产品如何定价？是否支持企业合作？"]
    )
    async def answer(self, question: str) -> str:
        system_prompt = f"你是一个资深的销售顾问。请热情、专业地回答用户的销售相关问题。\n用户问题: \"{question}\""
        response = await llm.ainvoke([SystemMessage(content=system_prompt)])
        return response.content

sales_agent = SalesConsultantAgent()

app = FastAPI(title="Sales Consultant Agent Service")

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    user_msg = request.messages[-1].content
    system_prompt = f"你是一个资深的销售顾问。请热情、专业地回答用户的销售相关问题。\n用户问题: \"{user_msg}\""
    return await handle_chat_completion(request, llm, system_prompt)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
