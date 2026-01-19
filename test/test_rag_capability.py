import requests
import numpy as np
import os
from typing import List

EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8003/embed")

def get_embeddings(texts: List[str]) -> List[List[float]]:
    try:
        response = requests.post(EMBEDDING_SERVICE_URL, json={"input": texts})
        response.raise_for_status()
        return response.json()["embeddings"]
    except Exception as e:
        print(f"Error: {e}")
        return []

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def test_semantic_search():
    print("=== Testing Semantic Search Capabilities (RAG Scenario) ===\n")
    
    # 1. 模拟知识库中的文档片段（Answer）
    documents = [
        "财务报销需要提供增值税专用发票，并在每月25日前提交。",  # Doc 1: 财务/发票
        "员工请假超过3天需要部门负责人审批，超过7天需分管副总审批。", # Doc 2: 人事/请假
        "公司服务器严禁私自安装未授权软件，违者将面临纪律处分。",   # Doc 3: IT/安全
        "采购金额在50万以上的项目必须进行公开招标。",             # Doc 4: 采购/招标
    ]
    
    # 2. 模拟用户的模糊查询（Query）
    queries = [
        "买东西怎么报账？",       # 语义匹配 Doc 1
        "我想请一周的假找谁批？",  # 语义匹配 Doc 2
        "电脑能不能装个游戏？",    # 语义匹配 Doc 3
        "大额采购有什么规定？",    # 语义匹配 Doc 4
    ]

    print("Encoding documents...")
    doc_vecs = get_embeddings(documents)
    
    print("Encoding queries...")
    query_vecs = get_embeddings(queries)
    
    if not doc_vecs or not query_vecs:
        return

    # 3. 计算匹配度
    for q_idx, query in enumerate(queries):
        print(f"\nQuery: '{query}'")
        scores = []
        for d_idx, doc in enumerate(documents):
            sim = cosine_similarity(query_vecs[q_idx], doc_vecs[d_idx])
            scores.append((doc, sim))
        
        # 排序并打印 Top 1
        scores.sort(key=lambda x: x[1], reverse=True)
        best_doc, best_score = scores[0]
        
        print(f"  👉 Best Match ({best_score:.4f}): \"{best_doc}\"")
        
        # 简单验证：只要分数最高的是预期的那个，就算成功
        # 这里人工看一眼就知道对不对
        
if __name__ == "__main__":
    test_semantic_search()
