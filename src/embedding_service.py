from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Union
from langchain_huggingface import HuggingFaceEmbeddings
import uvicorn

app = FastAPI(title="Embedding Service")

# 初始化模型（全局加载一次）
# 使用 Qwen3 系列的 Embedding 模型 (0.6B 级别)
# Qwen/Qwen3-Embedding-0.6B 是最新的 Qwen3 系列 Embedding 模型，兼顾性能与效率
MODEL_NAME = "BAAI/bge-small-zh-v1.5"

print(f"Loading Embedding Model ({MODEL_NAME})...")
model = HuggingFaceEmbeddings(
    model_name=MODEL_NAME,
    model_kwargs={"trust_remote_code": True},
    encode_kwargs={"normalize_embeddings": True},
)
print("Model loaded successfully.")


class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]


@app.post("/embed", response_model=EmbeddingResponse)
async def embed_text(request: EmbeddingRequest):
    try:
        if isinstance(request.input, str):
            # 针对单条文本
            embedding = model.embed_query(request.input)
            return {"embeddings": [embedding]}
        else:
            # 针对多条文本
            embeddings = model.embed_documents(request.input)
            return {"embeddings": embeddings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok", "model": MODEL_NAME}


if __name__ == "__main__":
    # 默认运行在 8002 端口，避免与 MCP Server (8001) 冲突
    uvicorn.run(app, host="0.0.0.0", port=8003)
