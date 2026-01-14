from __future__ import annotations

import json
from typing import Any

from . import kb
from .models import SourceSystem
from .retrieval import build_query, topk_by_similarity
from .rules import evaluate_rules
from .scoring import score_probability


def demo_payload(source_system: SourceSystem) -> dict[str, Any]:
    if source_system == "decision":
        return {
            "topic": "关于某供应商合作与采购策略的议题",
            "decision_type": "上会审批",
            "related_party": True,
            "disclosure_provided": False,
            "attachments": [],
            "stakeholders": ["部门A", "部门B"],
        }
    if source_system == "procurement":
        return {
            "title": "某信息化系统采购申请",
            "procurement_method": "single_source",
            "amount": 2200000,
            "supplier_name": "某科技有限公司",
            "supplier_blacklisted": False,
            "single_source_reason": "",
            "attachments": ["采购申请.pdf"],
        }
    return {
        "project_name": "某建设项目",
        "contract_name": "软件服务合同",
        "contract_value": 3500000,
        "payment_terms_days": 240,
        "contract_text": "本合同约定服务内容与付款安排……",
        "has_penalty_clause": False,
        "has_audit_clause": False,
        "attachments": [],
    }


def schema_hint(source_system: SourceSystem) -> dict[str, Any]:
    if source_system == "decision":
        return {
            "topic/title": "议题标题",
            "decision_type": "上会/会签/领导审批",
            "related_party": "是否涉及关联方(true/false)",
            "disclosure_provided": "是否已提供披露材料(true/false)",
            "attachments": "附件列表(可为空)",
        }
    if source_system == "procurement":
        return {
            "title": "采购事项名称",
            "procurement_method": "公开招标/竞争性谈判/询价/single_source/direct_purchase",
            "amount": "金额(数字)",
            "supplier_name": "供应商名称",
            "supplier_blacklisted": "是否黑名单(true/false)",
            "single_source_reason": "单一来源原因(字符串，可为空)",
            "attachments": "附件列表",
        }
    return {
        "project_name": "项目名称",
        "contract_name": "合同名称",
        "contract_value": "合同金额(数字)",
        "payment_terms_days": "付款周期(天，数字)",
        "contract_text": "合同正文(字符串，可为空)",
        "has_penalty_clause": "是否包含违约责任条款(true/false)",
        "has_audit_clause": "是否包含审计/监督条款(true/false)",
        "attachments": "附件列表",
    }


def parse_payload_json(payload_input: Any) -> dict[str, Any]:
    """解析输入数据，支持字符串 JSON 或直接传入的字典。"""
    if isinstance(payload_input, dict):
        return payload_input
    
    if isinstance(payload_input, str):
        content = payload_input.strip()
        if not content:
            return {}
        
        # 尝试自动修复常见的 LLM 转义错误（例如 \" -> "）
        # 这种错误通常发生在模型尝试在 JSON 字符串内部手动转义键名时
        if '\\"' in content and '"' in content:
            # 只有当检测到非法转义序列时才尝试修复
            fixed_content = content.replace('\\"', '"')
            try:
                obj = json.loads(fixed_content)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass

        try:
            obj = json.loads(content)
            if isinstance(obj, dict):
                return obj
            return {"value": obj}
        except json.JSONDecodeError:
            # 如果不是合法的 JSON 字符串，则作为文本字段返回
            return {"text": content}
            
    return {}


def assess_compliance_risk(source_system: SourceSystem, payload: Any) -> dict[str, Any]:
    payload_data = parse_payload_json(payload)
    query = build_query(source_system, payload_data)

    policy_docs = kb.iter_policy_texts()
    case_docs = kb.iter_case_texts()

    policy_hits = topk_by_similarity(query, policy_docs, k=3) if policy_docs else []
    case_hits = topk_by_similarity(query, case_docs, k=3) if case_docs else []

    signals = evaluate_rules(source_system, payload_data)
    score = score_probability(
        signals=signals,
        policy_hits=policy_hits,
        case_hits=case_hits,
        case_decision_getter=kb.get_case_decision,
    )

    follow_ups: list[str] = []
    for s in signals:
        code = s.get("code")
        if code in {"missing_single_source_reason"}:
            follow_ups.append("请补充单一来源的唯一性依据或紧急性说明，并提供审批要件。")
        if code in {
            "missing_attachments",
            "decision_missing_procurement_materials",
            "missing_contract_materials",
        }:
            follow_ups.append("请补充关键附件（预算依据、需求说明、比选材料/合同正文等）。")
        if code in {"related_party_disclosure"}:
            follow_ups.append("请补充关联关系披露材料，并说明回避流程是否已执行。")
        if code in {"contract_missing_penalty", "contract_missing_audit_clause"}:
            follow_ups.append("请确认合同关键条款是否齐全（违约责任、审计/监督配合等），必要时补充条款。")

    citations: list[dict[str, Any]] = []
    for hit in policy_hits:
        citations.append({"type": "policy", **hit})
    for hit in case_hits:
        citations.append(
            {"type": "case", **hit, "case_decision": kb.get_case_decision(hit["id"])}
        )

    return {
        "source_system": source_system,
        "risk": score,
        "signals": signals,
        "citations": citations,
        "follow_up_questions": follow_ups[:5],
        "normalized_payload": payload_data,
    }


def assess_demo(source_system: SourceSystem) -> dict[str, Any]:
    payload = demo_payload(source_system)
    return assess_compliance_risk(source_system, json.dumps(payload, ensure_ascii=False))

