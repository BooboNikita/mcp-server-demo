import json
import httpx
from fastapi.responses import StreamingResponse
from langchain_core.messages import SystemMessage
from src.a2a.protocol import ChatCompletionRequest

async def generate_stream(llm, system_prompt: str):
    """生成 SSE 格式的流式响应"""
    try:
        async for chunk in llm.astream([SystemMessage(content=system_prompt)]):
            if chunk.content:
                data = json.dumps({'choices': [{'delta': {'content': chunk.content}}]})
                yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        error_data = json.dumps({'error': str(e)})
        yield f"data: {error_data}\n\n"
        yield "data: [DONE]\n\n"

async def handle_chat_completion(request: ChatCompletionRequest, llm, system_prompt: str):
    """通用的 Chat Completion 处理逻辑"""
    if request.stream:
        return StreamingResponse(
            generate_stream(llm, system_prompt),
            media_type="text/event-stream"
        )
    else:
        response = await llm.ainvoke([SystemMessage(content=system_prompt)])
        return {
            "choices": [{"message": {"role": "assistant", "content": response.content}}]
        }

async def handle_proxy_request(target_url: str, request_data: dict, stream: bool):
    """处理代理转发请求"""
    if stream:
        async def stream_proxy():
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", target_url, json=request_data) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            yield f"{line}\n\n"
        return StreamingResponse(stream_proxy(), media_type="text/event-stream")
    else:
        async with httpx.AsyncClient() as client:
            resp = await client.post(target_url, json=request_data)
            return resp.json()
