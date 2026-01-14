from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SourceSystem = Literal["decision", "procurement", "analytics"]


@dataclass(frozen=True)
class PolicyDoc:
    doc_id: str
    title: str
    content: str
    effective_from: str | None = None
    scope: str | None = None


@dataclass(frozen=True)
class CaseDoc:
    case_id: str
    summary: str
    decision: Literal["compliant", "non_compliant", "unknown"]
    reasons: str
    tags: list[str]

