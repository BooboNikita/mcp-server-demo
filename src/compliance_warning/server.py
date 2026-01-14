from __future__ import annotations

from typing import Any, Literal, Union

import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from . import kb, service
from .models import SourceSystem

# 加载环境变量
load_dotenv()

mcp = FastMCP("ComplianceWarningDemo", json_response=True, port=8001)


def ensure_seeded() -> dict[str, Any] | None:
    if kb.is_seeded():
        return None
    return kb.seed_demo_kb()


@mcp.tool()
def seed_demo_kb() -> dict[str, Any]:
    """初始化知识库，填充演示用的制度条款和历史案例数据。"""
    return kb.seed_demo_kb()


@mcp.tool()
def demo_payload(source_system: SourceSystem) -> dict[str, Any]:
    """获取指定业务系统的示例输入数据（Payload）。支持：decision(议事), procurement(招标), analytics(分析)。"""
    return service.demo_payload(source_system)


@mcp.tool()
def schema_hint(source_system: SourceSystem) -> dict[str, Any]:
    """获取指定业务系统的输入字段说明，帮助了解需要提供哪些合规审查要素。"""
    return service.schema_hint(source_system)


@mcp.tool()
def ingest_policy(
    doc_id: str,
    title: str,
    content: str,
    effective_from: str | None = None,
    scope: str | None = None,
) -> dict[str, Any]:
    """向知识库动态录入一条新的制度条款。"""
    return kb.ingest_policy(
        doc_id=doc_id,
        title=title,
        content=content,
        effective_from=effective_from,
        scope=scope,
    )


@mcp.tool()
def ingest_case(
    case_id: str,
    summary: str,
    decision: Literal["compliant", "non_compliant", "unknown"],
    reasons: str,
    tags_json: Union[str, list[str]] = "[]",
) -> dict[str, Any]:
    """向知识库动态录入一个历史合规案例（审计结果或否决记录）。"""
    return kb.ingest_case(
        case_id=case_id,
        summary=summary,
        decision=decision,
        reasons=reasons,
        tags_json=tags_json,
    )


@mcp.tool()
def assess_compliance_risk(source_system: SourceSystem, payload: Union[dict[str, Any], str]) -> dict[str, Any]:
    """核心评估工具：根据提供的业务数据，结合制度库和案例库，计算不合规概率并给出预警理由与证据引用。
    
    Args:
        source_system: 业务系统类型 (decision, procurement, analytics)
        payload: 业务数据对象（推荐）或 JSON 字符串。
    """
    ensure_seeded()
    return service.assess_compliance_risk(source_system, payload)


@mcp.tool()
def assess_demo(source_system: SourceSystem) -> dict[str, Any]:
    """一键评估工具：使用内置的示例数据运行一次完整的风险评估流程。"""
    ensure_seeded()
    return service.assess_demo(source_system)


@mcp.resource("policy://{doc_id}")
def get_policy(doc_id: str) -> str:
    """资源获取：根据 ID 获取特定制度条款的详细 JSON 内容。"""
    ensure_seeded()
    return kb.get_policy_json(doc_id)


@mcp.resource("case://{case_id}")
def get_case(case_id: str) -> str:
    """资源获取：根据 ID 获取特定历史案例的详细 JSON 内容。"""
    ensure_seeded()
    return kb.get_case_json(case_id)

