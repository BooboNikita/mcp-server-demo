from __future__ import annotations

import math
import re
import os
import requests
from typing import Any, List

from .models import SourceSystem

EMBEDDING_SERVICE_URL = os.getenv(
    "EMBEDDING_SERVICE_URL", "http://localhost:8003/embed"
)


class RemoteEmbeddings:
    """通过 HTTP 调用独立 Embedding 服务的客户端"""

    def __init__(self, url: str):
        self.url = url

    def embed_query(self, text: str) -> List[float]:
        response = requests.post(self.url, json={"input": text})
        # 在实际生产中应添加重试机制和错误处理
        response.raise_for_status()
        return response.json()["embeddings"][0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        response = requests.post(self.url, json={"input": texts})
        response.raise_for_status()
        return response.json()["embeddings"]


def get_embeddings_model():
    """初始化远程 Embedding 服务客户端"""
    return RemoteEmbeddings(url=EMBEDDING_SERVICE_URL)


def vector_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 <= 0.0 or norm2 <= 0.0:
        return 0.0
    return dot_product / (norm1 * norm2)


def topk_by_similarity(
    query: str, docs: list[tuple[str, str]], k: int = 3
) -> list[dict[str, Any]]:
    if not docs:
        return []

    embeddings_model = get_embeddings_model()

    # 获取查询和文档的向量
    # 注意：在实际生产中，文档向量应该被缓存或预先计算
    query_vec = embeddings_model.embed_query(query)
    print(f"Query vector: {query_vec}...")

    doc_texts = [doc[1] for doc in docs]
    doc_vecs = embeddings_model.embed_documents(doc_texts)

    scored: list[tuple[float, str, str]] = []
    for i, (doc_id, doc_text) in enumerate(docs):
        sim = vector_cosine_similarity(query_vec, doc_vecs[i])
        scored.append((sim, doc_id, doc_text))

    scored.sort(key=lambda x: x[0], reverse=True)
    results: list[dict[str, Any]] = []
    for score, doc_id, doc_text in scored[:k]:
        results.append(
            {"id": doc_id, "score": round(float(score), 4), "excerpt": doc_text[:240]}
        )
    return results


def build_query(source_system: SourceSystem, payload: dict[str, Any]) -> str:
    parts: list[str] = [source_system]
    for key in [
        "title",
        "topic",
        "summary",
        "description",
        "project_name",
        "contract_name",
    ]:
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    for key in [
        "procurement_method",
        "decision_type",
        "project_stage",
        "supplier_name",
        "counterparty_name",
    ]:
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(f"{key}:{v.strip()}")
    for key in ["amount", "contract_value", "budget"]:
        v = payload.get(key)
        if isinstance(v, (int, float)):
            parts.append(f"{key}:{v}")
    return "\n".join(parts)
