from __future__ import annotations

from typing import Any, Literal

from .rules import Severity


def clamp01(x: float) -> float:
    return max(0.0, min(0.99, x))


def risk_level(p: float, has_blocking: bool) -> Literal["low", "medium", "high", "block"]:
    if has_blocking:
        return "block"
    if p >= 0.75:
        return "high"
    if p >= 0.45:
        return "medium"
    return "low"


def score_probability(
    *,
    signals: list[dict[str, Any]],
    policy_hits: list[dict[str, Any]],
    case_hits: list[dict[str, Any]],
    case_decision_getter,
) -> dict[str, Any]:
    weight_by_sev: dict[Severity, float] = {
        "low": 0.08,
        "medium": 0.18,
        "high": 0.35,
        "block": 0.6,
    }

    p_from_signals = 0.0
    for s in signals:
        sev = str(s.get("severity", "low"))
        w = weight_by_sev.get(sev, 0.1)
        p_from_signals = 1.0 - (1.0 - p_from_signals) * (1.0 - w)
    print(signals)

    p_from_cases = 0.0
    for hit in case_hits[:3]:
        case_id = hit.get("id")
        sim = float(hit.get("score", 0.0))
        decision = case_decision_getter(case_id) if case_id else None
        base = 0.25 if decision == "non_compliant" else 0.08
        p_from_cases = max(p_from_cases, base * sim)
    print(case_hits)

    p_from_policies = 0.0
    for hit in policy_hits[:3]:
        sim = float(hit.get("score", 0.0))
        p_from_policies = max(p_from_policies, 0.12 * sim)
    print(policy_hits)

    raw = 0.15 + 0.55 * p_from_signals + 0.25 * p_from_cases + 0.15 * p_from_policies
    p = clamp01(raw)
    has_blocking = any(s.get("severity") == "block" for s in signals)
    return {
        "probability": round(float(p), 4),
        "level": risk_level(p, has_blocking),
        "components": {
            "signals": round(float(p_from_signals), 4),
            "cases": round(float(p_from_cases), 4),
            "policies": round(float(p_from_policies), 4),
        },
    }

