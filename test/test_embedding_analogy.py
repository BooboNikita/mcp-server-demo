import requests
import numpy as np
from typing import List
import os

# 配置 Embedding 服务地址
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8003/embed")

def get_embeddings(texts: List[str]) -> dict:
    """批量获取文本向量"""
    try:
        response = requests.post(EMBEDDING_SERVICE_URL, json={"input": texts})
        response.raise_for_status()
        embeddings = response.json()["embeddings"]
        return dict(zip(texts, embeddings))
    except Exception as e:
        print(f"Error fetching embeddings: {e}")
        return {}

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """计算余弦相似度"""
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return np.dot(v1, v2) / (norm1 * norm2)

def test_analogy():
    print("==================================================")
    print("   Embedding 语义关系测试 (King - Man + Woman = ?)   ")
    print("==================================================\n")

    # 1. 定义词汇
    words = ["king", "man", "woman", "queen", "princess", "prince", "apple", "doctor"]
    print(f"[1] 获取词向量: {words} ...")
    
    vectors_map = get_embeddings(words)
    if not vectors_map:
        print("❌ 无法获取向量，请确保 embedding_service.py 正在运行 (端口 8003)。")
        return

    # 转换为 numpy 数组以便计算
    vecs = {k: np.array(v) for k, v in vectors_map.items()}

    # 2. 执行向量运算: King - Man + Woman
    # 理论上应该接近 Queen
    print("[2] 执行向量运算: vec(king) - vec(man) + vec(woman) ...")
    target_vec = vecs["king"] - vecs["man"] + vecs["woman"]
    print(f"{vecs["king"]}, {vecs["man"]}, {vecs["woman"]}, {vecs["queen"]} = {target_vec}")

    # 3. 计算与候选词的相似度s
    print("[3] 计算相似度排名:")
    
    similarities = []
    for word, vec in vecs.items():
        print(f"    {word}")
        # 跳过参与运算的词，避免干扰（虽然通常我们看的是 target 与结果的距离）
        # 这里为了直观，我们列出所有候选词
        sim = cosine_similarity(target_vec, vec)
        similarities.append((word, sim))
    
    # 按相似度降序排列
    similarities.sort(key=lambda x: x[1], reverse=True)

    # 4. 打印结果
    for rank, (word, sim) in enumerate(similarities, 1):
        indicator = "   "
        if word == "queen":
            indicator = "👉 " # 预期目标
        print(f"   {rank}. {indicator}{word:<10} : {sim:.4f}")

    # 5. 验证结论
    top_word = similarities[0][0]
    queen_rank = next(i for i, (w, s) in enumerate(similarities) if w == "queen") + 1
    
    print("\n--------------------------------------------------")
    if top_word == "queen":
        print("✅ 测试通过: 'queen' 是最接近计算结果的词向量！")
    elif queen_rank <= 3:
        print(f"⚠️ 测试尚可: 'queen' 排在第 {queen_rank} 位 (Top 1 是 '{top_word}')。")
        print("   说明: 句子级 Embedding 模型在词汇级类比推理上可能不如专用词向量(如 Word2Vec)精准。")
    else:
        print(f"❌ 测试失败: 'queen' 排在第 {queen_rank} 位。")
    print("--------------------------------------------------")

if __name__ == "__main__":
    test_analogy()
