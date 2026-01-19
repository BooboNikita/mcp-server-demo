import json
import os

from src.compliance_warning import kb, service
from src.compliance_warning.models import SourceSystem
from unittest.mock import MagicMock, patch
import random

def mock_embed_query(text):
    # Return a random vector of dimension 1024 (typical for large models)
    return [random.random() for _ in range(1024)]

def mock_embed_documents(texts):
    return [[random.random() for _ in range(1024)] for _ in texts]

def run_evaluation():
    print("==================================================")
    print("   监管预警 MCP 服务能力评估 (Compliance Warning)   ")
    print("==================================================\n")
    
    # Check if embedding service is running, if not, mock it
    import requests
    try:
        requests.get("http://localhost:8003/health", timeout=1)
        print("[INFO] Embedding service detected. Using real embeddings.\n")
    except (requests.ConnectionError, requests.Timeout):
        print("[WARN] Embedding service NOT found. Switching to MOCK embeddings for functional testing.\n")
        # Patch the RemoteEmbeddings class in retrieval module
        patcher = patch('src.compliance_warning.retrieval.RemoteEmbeddings')
        MockEmbeddings = patcher.start()
        # Setup the mock instance
        mock_instance = MockEmbeddings.return_value
        mock_instance.embed_query.side_effect = mock_embed_query
        mock_instance.embed_documents.side_effect = mock_embed_documents
        
        # We also need to mock the get_embeddings_model function to return our mock
        # or ensure the patch applies where it's instantiated.
        # Actually, looking at retrieval.py, get_embeddings_model creates a new instance every time.
        # So patching the class should work.
    
    # 1. 初始化系统
    print("[1] 初始化知识库 (System Initialization)...")
    kb.seed_demo_kb()
    print(f"    √ 知识库已加载: 制度({len(kb._POLICIES)}条), 案例({len(kb._CASES)}个)\n")

    # 2. 规则引擎测试：高风险场景（单一来源未说明原因）
    print("[2] 规则引擎测试: 高风险场景 (High Risk Scenario)...")
    payload_high_risk = {
        "title": "大型核心系统采购项目",
        "procurement_method": "single_source",
        "amount": 5000000,  # 高金额
        "supplier_name": "某科技公司",
        "supplier_blacklisted": False,
        "single_source_reason": "",  # 故意留空，应触发风险
        "attachments": []
    }
    result_high = service.assess_compliance_risk("procurement", payload_high_risk)
    
    risk_score = result_high["risk"]
    signals = [s["code"] for s in result_high["signals"]]
    
    print(f"    风险评分: {risk_score}")
    print(f"    触发信号: {signals}")
    
    # Check probability field if risk is a dict
    prob = risk_score["probability"] if isinstance(risk_score, dict) else risk_score
    
    if prob > 0.5 and "missing_single_source_reason" in signals:
        print("    ✅ PASS: 成功识别高风险及缺失单一来源依据。")
    else:
        print(f"    ❌ FAIL: 未能识别高风险或信号缺失 (Score: {prob}).")
    print("")

    # 3. 规则引擎测试：低风险场景（合规采购）
    print("[3] 规则引擎测试: 低风险场景 (Low Risk Scenario)...")
    payload_low_risk = {
        "title": "标准硬件采购",
        "procurement_method": "single_source",
        "amount": 5000000,
        "supplier_name": "独家专利持有公司",
        "supplier_blacklisted": False,
        "single_source_reason": "拥有核心专利X，市场上无替代品", # 已提供充分理由
        "attachments": ["采购申请书.pdf", "专利证明.pdf"]
    }
    result_low = service.assess_compliance_risk("procurement", payload_low_risk)
    
    risk_score_low = result_low["risk"]
    signals_low = [s["code"] for s in result_low["signals"]]
    
    print(f"    风险评分: {risk_score_low}")
    
    prob_low = risk_score_low["probability"] if isinstance(risk_score_low, dict) else risk_score_low
    
    if prob_low < prob and "missing_single_source_reason" not in signals_low:
        print("    ✅ PASS: 风险评分显著降低且无阻断性信号。")
    else:
        print(f"    ❌ FAIL: 风险评分未降低或误报信号 (High: {prob}, Low: {prob_low}).")
    print("")

    # 4. 检索能力测试：语义匹配
    print("[4] 检索能力测试: 语义匹配 (Retrieval Relevance)...")
    # 构造一个涉及“亲属”、“关联”的场景，看能否检索到《关联交易管理规定》
    payload_retrieval = {
        "topic": "关于与董事亲属控制企业合作的议案",
        "decision_type": "approval",
        "related_party": True,
        "disclosure_provided": False,
        "attachments": []
    }
    result_retrieval = service.assess_compliance_risk("decision", payload_retrieval)
    
    citations = result_retrieval["citations"]
    found_policy = False
    for cit in citations:
        print(f"    引用: {cit}")
        # Note: citations contain 'excerpt' which combines title and content
        if cit["type"] == "policy" and ("关联" in cit.get("excerpt", "") or "回避" in cit.get("excerpt", "")):
            found_policy = True
            print(f"    √ 成功检索到相关制度: {cit['id']}")
            break
            
    if found_policy:
        print("    ✅ PASS: 上下文检索准确。")
    else:
        print("    ❌ FAIL: 未能检索到关联交易相关制度。")
    print("")

    # 5. 动态学习测试：注入新知识
    print("[5] 动态能力测试: 知识注入 (Dynamic Knowledge Injection)...")
    new_policy_id = "POL-999"
    new_policy_title = "AI大模型采购安全规范"
    new_policy_content = "所有AI相关采购必须经过数据安全委员会的前置评估，否则不予立项。"
    
    print(f"    操作: 注入新制度《{new_policy_title}》...")
    kb.ingest_policy(new_policy_id, new_policy_title, new_policy_content)
    
    payload_ai = {
        "title": "采购ChatGPT企业版服务", # 包含 AI 关键词
        "procurement_method": "open_tender",
        "amount": 100000,
        "attachments": []
    }
    
    result_ai = service.assess_compliance_risk("procurement", payload_ai)
    citations_ai = result_ai["citations"]
    
    found_new_policy = False
    for cit in citations_ai:
        if cit.get("id") == new_policy_id: # Use 'id' instead of 'doc_id' as per retrieval.py
            found_new_policy = True
            print(f"    √ 评估结果引用了新制度: {cit['id']}")
            break
            
    if found_new_policy:
        print("    ✅ PASS: 动态注入的知识已生效。")
    else:
        print("    ❌ FAIL: 评估未引用新注入的知识。")
    print("")

    # 6. 鲁棒性测试
    print("[6] 鲁棒性测试: 异常输入 (Robustness)...")
    try:
        # 传入非 JSON 的纯文本
        service.assess_compliance_risk("procurement", "这是一段纯文本描述，不是JSON")
        print("    ✅ PASS: 系统能够处理非结构化文本输入而不崩溃。")
    except Exception as e:
        print(f"    ❌ FAIL: 系统发生异常: {e}")

    print("\n==================================================")
    print("   评估结束 (Evaluation Complete)   ")
    print("==================================================")

if __name__ == "__main__":
    run_evaluation()
