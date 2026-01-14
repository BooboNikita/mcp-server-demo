from __future__ import annotations

from typing import Any, Literal

from .models import SourceSystem

Severity = Literal["low", "medium", "high", "block"]


def add_signal(
    signals: list[dict[str, Any]],
    *,
    code: str,
    severity: Severity,
    message: str,
    evidence: list[dict[str, Any]] | None = None,
) -> None:
    signals.append(
        {"code": code, "severity": severity, "message": message, "evidence": evidence or []}
    )


def evaluate_rules(source_system: SourceSystem, payload: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []

    attachments = payload.get("attachments")
    if attachments is None:
        attachments_list: list[Any] = []
    elif isinstance(attachments, list):
        attachments_list = attachments
    else:
        attachments_list = [attachments]

    if source_system == "procurement":
        amount = payload.get("amount")
        method = (payload.get("procurement_method") or "").strip()
        supplier_blacklisted = bool(payload.get("supplier_blacklisted", False))
        single_source_reason = (payload.get("single_source_reason") or "").strip()

        if supplier_blacklisted:
            add_signal(
                signals,
                code="supplier_blacklist",
                severity="block",
                message="供应商命中风险/黑名单，需要强制复核或拦截。",
            )

        if (
            isinstance(amount, (int, float))
            and amount >= 1_000_000
            and method in {"single_source", "direct_purchase", "询价"}
        ):
            add_signal(
                signals,
                code="method_threshold_mismatch",
                severity="high",
                message="金额较大但采购方式可能不匹配，建议核对公开招标/竞争性方式要求。",
            )

        if method in {"single_source", "direct_purchase"} and not single_source_reason:
            add_signal(
                signals,
                code="missing_single_source_reason",
                severity="high",
                message="单一来源/直采缺少原因说明，建议补充唯一性依据或紧急性证明。",
            )

        if not attachments_list:
            add_signal(
                signals,
                code="missing_attachments",
                severity="medium",
                message="缺少关键附件，建议补充采购申请、预算依据、技术需求或比价材料。",
            )

    elif source_system == "decision":
        topic = (payload.get("topic") or payload.get("title") or "").strip()
        related_party = bool(payload.get("related_party", False))
        disclosure_provided = payload.get("disclosure_provided")
        if related_party and disclosure_provided is not True:
            add_signal(
                signals,
                code="related_party_disclosure",
                severity="high",
                message="涉及关联方但未明确披露或未提供披露材料，建议补充关联关系说明与回避流程。",
            )

        if topic and any(k in topic for k in ["招标", "采购", "供应商"]) and not attachments_list:
            add_signal(
                signals,
                code="decision_missing_procurement_materials",
                severity="medium",
                message="议题涉及采购但缺少关键材料，建议补充预算、需求、供应商信息与比选依据。",
            )

    else:
        contract_text = (payload.get("contract_text") or "").strip()
        has_penalty_clause = payload.get("has_penalty_clause")
        has_audit_clause = payload.get("has_audit_clause")
        payment_terms_days = payload.get("payment_terms_days")

        if contract_text and has_penalty_clause is False:
            add_signal(
                signals,
                code="contract_missing_penalty",
                severity="high",
                message="合同文本存在但缺少违约责任/处罚条款标记，建议复核合同关键条款完整性。",
            )

        if contract_text and has_audit_clause is False:
            add_signal(
                signals,
                code="contract_missing_audit_clause",
                severity="medium",
                message="合同缺少审计/监督配合条款标记，建议补充审计与留痕要求。",
            )

        if isinstance(payment_terms_days, (int, float)) and payment_terms_days > 180:
            add_signal(
                signals,
                code="long_payment_terms",
                severity="medium",
                message="付款周期较长，建议核对财务制度与履约保障安排。",
            )

        if not payload.get("contract_text") and not attachments_list:
            add_signal(
                signals,
                code="missing_contract_materials",
                severity="medium",
                message="缺少合同文本或附件，无法进行合同合规分析，建议补充材料。",
            )

    return signals

