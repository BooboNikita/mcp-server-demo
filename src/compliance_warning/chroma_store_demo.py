import chromadb
from chromadb.config import Settings
import requests
import uuid
import os
import json
from typing import List, Dict, Any

# 配置 Embedding 服务地址 (复用现有的服务)
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8003/embed")

class SimpleEmbeddingFunction:
    """
    自定义 Embedding 函数，适配 ChromaDB 的接口。
    调用我们本地启动的 embedding_service.py
    """
    def __call__(self, input: List[str]) -> List[List[float]]:
        try:
            # 注意：Chroma 传入的 input 是列表
            response = requests.post(EMBEDDING_SERVICE_URL, json={"input": input})
            response.raise_for_status()
            return response.json()["embeddings"]
        except Exception as e:
            print(f"Embedding 服务调用失败: {e}")
            # 返回全0向量作为 fallback，防止程序崩溃（仅演示用）
            return [[0.0] * 1024 for _ in input]

def run_chroma_demo():
    print("=== ChromaDB 多租户/多维度知识库演示 ===\n")

    # 1. 初始化 Chroma 客户端 (使用内存模式演示，重启后数据丢失)
    # 如果需要持久化，可以使用 chromadb.PersistentClient(path="./chroma_db")
    client = chromadb.Client()

    # 2. 创建集合 (Collection)
    # 使用自定义的 Embedding 函数
    collection = client.create_collection(
        name="compliance_docs",
        embedding_function=SimpleEmbeddingFunction()
    )

    print(">> 正在准备模拟数据...")
    
    # 3. 准备模拟数据：不同公司、不同文档、不同适用人群
    documents_data = [
        # --- A 公司的数据 ---
        {
            "text": "A公司差旅规定：市内交通费实报实销，但在没有发票的情况下，每人每天补贴上限为50元。",
            "metadata": {
                "company_id": "COMP_A",
                "company_name": "阿尔法科技",
                "doc_type": "policy",
                "department": "Finance",
                "access_level": "all",  # 全员可见
                "chunk_index": 0
            }
        },
        {
            "text": "A公司研发部加班制度：工作日加班超过21:00可报销打车费，需提供打车软件行程单。",
            "metadata": {
                "company_id": "COMP_A",
                "company_name": "阿尔法科技",
                "doc_type": "policy",
                "department": "R&D",
                "access_level": "internal", # 内部可见
                "chunk_index": 1
            }
        },
        
        # --- B 公司的数据 (内容相似但规定不同) ---
        {
            "text": "B公司差旅管理办法：市内交通一律不予报销，员工享有每月300元的固定交通补贴。",
            "metadata": {
                "company_id": "COMP_B",
                "company_name": "贝塔贸易",
                "doc_type": "policy",
                "department": "Finance",
                "access_level": "all",
                "chunk_index": 0
            }
        },
        {
            "text": "B公司高级管理人员特殊津贴：VP级以上高管出差可乘坐商务舱。",
            "metadata": {
                "company_id": "COMP_B",
                "company_name": "贝塔贸易",
                "doc_type": "policy",
                "department": "HR",
                "access_level": "executive", # 仅高管可见
                "chunk_index": 1
            }
        }
    ]

    # 4. 批量写入数据
    # 将数据拆分为列表以便 API 调用
    docs = [d["text"] for d in documents_data]
    metadatas = [d["metadata"] for d in documents_data]
    ids = [f"doc_{uuid.uuid4().hex[:8]}" for _ in documents_data]

    print(f">> 正在存入 {len(docs)} 条文档片段 (自动计算 Embedding 并绑定 Metadata)...")
    collection.add(
        documents=docs,
        metadatas=metadatas,
        ids=ids
    )
    print(">> 写入完成！\n")

    # 5. 演示检索场景
    
    # 场景一：查询“交通报销”，如果不加限制（会混淆不同公司的规定）
    query_text = "交通费怎么报销？"
    print(f"🔍 [场景1] 无过滤检索: '{query_text}'")
    results = collection.query(
        query_texts=[query_text],
        n_results=2
    )
    
    print("   结果可能包含多个公司的规定：")
    for i, doc in enumerate(results['documents'][0]):
        meta = results['metadatas'][0][i]
        print(f"   - [{meta['company_name']}] {doc}")


    # 场景二：我是 A 公司的员工，只想看 A 公司的规定
    print(f"\n🔍 [场景2] 过滤检索 (只看 A 公司): '{query_text}'")
    results_a = collection.query(
        query_texts=[query_text],
        n_results=2,
        # 关键点：使用 where 子句进行元数据过滤
        where={"company_id": "COMP_A"}
    )
    
    for i, doc in enumerate(results_a['documents'][0]):
        meta = results_a['metadatas'][0][i]
        print(f"   - [{meta['company_name']}] {doc}")


    # 场景三：我是 B 公司的高管，我想看所有关于“待遇”的规定（包括普通员工和高管）
    # Chroma 的 where 支持操作符，如 $or, $in 等 (视版本而定，这里演示复合查询逻辑)
    # 假设我们想查 COMP_B 且 (access_level=all OR access_level=executive)
    # Chroma 标准语法通常是 {"key": "value"} 或 {"key": {"$in": [...]}}
    
    query_vip = "高管有什么福利？"
    print(f"\n🔍 [场景3] 复合过滤 (B公司 + 权限控制): '{query_vip}'")
    
    results_vip = collection.query(
        query_texts=[query_vip],
        n_results=2,
        where={
            "$and": [
                {"company_id": {"$eq": "COMP_B"}},
                # 注意：简单的 where 字典通常是 AND 关系。
                # 复杂的 OR 逻辑在 Chroma 中可能需要用 $or 列表
                {"$or": [
                    {"access_level": {"$eq": "all"}},
                    {"access_level": {"$eq": "executive"}}
                ]}
            ]
        }
    )
    
    for i, doc in enumerate(results_vip['documents'][0]):
        meta = results_vip['metadatas'][0][i]
        print(f"   - [{meta['company_name']} | {meta['access_level']}] {doc}")

if __name__ == "__main__":
    try:
        run_chroma_demo()
    except ImportError:
        print("❌ 错误: 未找到 chromadb 库。")
        print("请运行: pip install chromadb")
    except Exception as e:
        print(f"❌ 运行出错: {e}")
