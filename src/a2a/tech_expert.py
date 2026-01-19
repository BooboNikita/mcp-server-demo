import os
import sys
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

@agent(name="TechExpert", description="回答深度的技术问题、架构建议和 API 使用")
class TechExpertAgent:
    @skill(
        name="技术解答",
        description="回答技术问题与架构咨询",
        tags=["technical", "architecture"],
        examples=["如何设计高可用的微服务架构？"]
    )
    async def answer(self, question: str) -> str:
        system_prompt = f"你是一个资深的架构师和技术专家。请专业地回答用户的技术问题。\n用户问题: \"{question}\""
        response = await llm.ainvoke([SystemMessage(content=system_prompt)])
        return response.content

tech_agent = TechExpertAgent()

app = FastAPI(title="Tech Expert Agent Service")

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    user_msg = request.messages[-1].content
    system_prompt = f"你是一个资深的架构师和技术专家。请专业地回答用户的技术问题。\n用户问题: \"{user_msg}\""
    return await handle_chat_completion(request, llm, system_prompt)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
