from __future__ import annotations

import json
from datetime import date
from typing import Any, Literal

from .models import CaseDoc, PolicyDoc

_POLICIES: dict[str, PolicyDoc] = {}
_CASES: dict[str, CaseDoc] = {}


def is_seeded() -> bool:
    return bool(_POLICIES) or bool(_CASES)


def seed_demo_kb() -> dict[str, Any]:
    today = date.today().isoformat()

    policies = [
        PolicyDoc(
            doc_id="POL-001",
            title="采购方式与金额阈值管理办法",
            content="金额达到一定阈值应采用公开竞争方式。单一来源应具备唯一性依据并履行审批与公示要求。采购过程应留痕可追溯。",
            effective_from=today,
            scope="集团",
        ),
        PolicyDoc(
            doc_id="POL-002",
            title="关联交易与回避管理规定",
            content="涉及关联方的议题应进行关联关系披露，相关人员应按规定回避。披露材料应随议题提交并纳入审批档案。",
            effective_from=today,
            scope="集团",
        ),
        PolicyDoc(
            doc_id="POL-003",
            title="合同关键条款与监督要求",
            content="合同应包含违约责任、审计/监督配合、付款条件、交付验收等关键条款。重大合同应纳入重点监督与审计抽查。",
            effective_from=today,
            scope="集团",
        ),
    ]

    cases = [
        CaseDoc(
            case_id="CASE-101",
            summary="某项目金额较大采用单一来源，未提供唯一性依据。",
            decision="non_compliant",
            reasons="金额达到公开竞争阈值但走单一来源，且缺少唯一性证明与审批要件，审计指出程序不合规。",
            tags=["procurement", "single_source", "threshold"],
        ),
        CaseDoc(
            case_id="CASE-102",
            summary="议题涉及关联方但未披露关联关系，后续被追责。",
            decision="non_compliant",
            reasons="未履行披露与回避流程，审批材料不完整，形成廉洁风险。",
            tags=["decision", "related_party"],
        ),
        CaseDoc(
            case_id="CASE-103",
            summary="合同缺少违约责任条款导致履约争议。",
            decision="non_compliant",
            reasons="关键条款缺失导致权责不清，造成损失与审计问题。",
            tags=["analytics", "contract"],
        ),
        CaseDoc(
            case_id="CASE-104",
            summary="同类采购补齐材料后通过复核。",
            decision="compliant",
            reasons="补充唯一性证明、比价记录与审批链路后，程序要件满足。",
            tags=["procurement", "materials"],
        ),
    ]

    for p in policies:
        _POLICIES[p.doc_id] = p
    for c in cases:
        _CASES[c.case_id] = c

    return {"policies": len(_POLICIES), "cases": len(_CASES)}


def ingest_policy(
    doc_id: str,
    title: str,
    content: str,
    effective_from: str | None = None,
    scope: str | None = None,
) -> dict[str, Any]:
    _POLICIES[doc_id] = PolicyDoc(
        doc_id=doc_id,
        title=title,
        content=content,
        effective_from=effective_from,
        scope=scope,
    )
    return {"ok": True, "policies": len(_POLICIES)}


def ingest_case(
    case_id: str,
    summary: str,
    decision: Literal["compliant", "non_compliant", "unknown"],
    reasons: str,
    tags_json: str = "[]",
) -> dict[str, Any]:
    tags_raw = json.loads(tags_json) if tags_json.strip() else []
    tags = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else [str(tags_raw)]
    _CASES[case_id] = CaseDoc(
        case_id=case_id,
        summary=summary,
        decision=decision,
        reasons=reasons,
        tags=tags,
    )
    return {"ok": True, "cases": len(_CASES)}


def iter_policy_texts() -> list[tuple[str, str]]:
    return [(p.doc_id, f"{p.title}\n{p.content}") for p in _POLICIES.values()]


def iter_case_texts() -> list[tuple[str, str]]:
    return [(c.case_id, f"{c.summary}\n{c.reasons}") for c in _CASES.values()]


def get_policy_json(doc_id: str) -> str:
    p = _POLICIES.get(doc_id)
    if p is None:
        return ""
    return json.dumps(
        {
            "doc_id": p.doc_id,
            "title": p.title,
            "effective_from": p.effective_from,
            "scope": p.scope,
            "content": p.content,
        },
        ensure_ascii=False,
    )


def get_case_json(case_id: str) -> str:
    c = _CASES.get(case_id)
    if c is None:
        return ""
    return json.dumps(
        {
            "case_id": c.case_id,
            "summary": c.summary,
            "decision": c.decision,
            "reasons": c.reasons,
            "tags": c.tags,
        },
        ensure_ascii=False,
    )


def get_case_decision(case_id: str) -> str | None:
    c = _CASES.get(case_id)
    if c is None:
        return None
    return c.decision

