import httpx
import asyncio
import json

async def test_agent_chat(prompt: str):
    url = "http://localhost:8000/v1/chat/completions"
    payload = {
        "model": "kimi-latest",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }
    
    print(f"\n🟢 发送问题: {prompt}")
    print("waiting for response...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    print(f"❌ Error: {response.status_code}")
                    print(await response.aread())
                    return

                print("🔵 收到响应:")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk["choices"][0]["delta"].get("content", "")
                            print(content, end="", flush=True)
                        except json.JSONDecodeError:
                            pass
                print("\n" + "-"*50)
    except Exception as e:
        print(f"❌ Connection Error: {e}")

async def main():
    # 1. 测试技术问题 -> 应该路由给 TechExpert
    await test_agent_chat("如何设计高并发的 Python 微服务架构？")
    
    # 2. 测试销售问题 -> 应该路由给 SalesConsultant
    await test_agent_chat("你们的企业版授权多少钱一年？")
    
    # 3. 测试通用/其他问题
    await test_agent_chat("你好，你是谁？")

if __name__ == "__main__":
    asyncio.run(main())
