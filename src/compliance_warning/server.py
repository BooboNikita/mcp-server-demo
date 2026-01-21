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
def assess_compliance_risk(
    source_system: SourceSystem, payload: Union[dict[str, Any], str]
) -> dict[str, Any]:
    """【第一步】执行合规风险初步筛查。
    
    这是评估流程的入口。它会：
    1. 解析业务数据
    2. 运行规则引擎检测硬性风险（Signals）
    3. 检索相似的历史案例和制度条款（Hits）
    
    注意：此工具返回的是原始证据（Evidence），不包含最终评分。
    获得输出后，你通常需要继续调用 `calculate_risk_score` 来计算量化风险。

    Args:
        source_system: 业务系统类型，可选值: decision (决策), procurement (采购), analytics (合同)
        payload: 业务数据的 JSON 字符串或对象。例如: {"project_name": "...", "amount": 10000}
    """
    ensure_seeded()
    return service.assess_compliance_context(source_system, payload)


@mcp.tool()
def calculate_risk_score(
    signals: list[dict[str, Any]],
    policy_hits: list[dict[str, Any]],
    case_hits: list[dict[str, Any]],
) -> dict[str, Any]:
    """【第二步】计算量化风险评分。
    
    必须使用 `assess_compliance_risk` 的输出作为此工具的输入。
    它会根据信号严重度和案例相似度，应用数学模型计算客观的风险概率（Probability）和等级（Level）。

    Args:
        signals: 从 assess_compliance_risk 返回的 signals 列表
        policy_hits: 从 assess_compliance_risk 返回的 policy_hits 列表
        case_hits: 从 assess_compliance_risk 返回的 case_hits 列表
    """





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


if __name__ == "__main__":
    mcp.run()
