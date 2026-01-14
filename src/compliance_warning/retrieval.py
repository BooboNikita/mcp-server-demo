from __future__ import annotations

import math
import re
from typing import Any

from .models import SourceSystem


def extract_terms(text: str) -> list[str]:
    normalized = (text or "").lower()
    alnum_terms = re.findall(r"[a-z0-9_]+", normalized)
    han_sequences = re.findall(r"[\u4e00-\u9fff]+", text or "")
    han_bigrams: list[str] = []
    for seq in han_sequences:
        if len(seq) == 1:
            han_bigrams.append(seq)
            continue
        for i in range(len(seq) - 1):
            han_bigrams.append(seq[i : i + 2])
    return alnum_terms + han_bigrams


def tf(terms: list[str]) -> dict[str, float]:
    freq: dict[str, float] = {}
    for t in terms:
        freq[t] = freq.get(t, 0.0) + 1.0
    return freq


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = 0.0
    for k, av in a.items():
        bv = b.get(k)
        if bv is not None:
            dot += av * bv
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)


def topk_by_similarity(query: str, docs: list[tuple[str, str]], k: int = 3) -> list[dict[str, Any]]:
    qv = tf(extract_terms(query))
    scored: list[tuple[float, str, str]] = []
    for doc_id, doc_text in docs:
        dv = tf(extract_terms(doc_text))
        scored.append((cosine(qv, dv), doc_id, doc_text))
    scored.sort(key=lambda x: x[0], reverse=True)
    results: list[dict[str, Any]] = []
    for score, doc_id, doc_text in scored[:k]:
        results.append(
            {"id": doc_id, "score": round(float(score), 4), "excerpt": doc_text[:240]}
        )
    return results


def build_query(source_system: SourceSystem, payload: dict[str, Any]) -> str:
    parts: list[str] = [source_system]
    for key in ["title", "topic", "summary", "description", "project_name", "contract_name"]:
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    for key in [
        "procurement_method",
        "decision_type",
        "project_stage",
        "supplier_name",
        "counterparty_name",
    ]:
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(f"{key}:{v.strip()}")
    for key in ["amount", "contract_value", "budget"]:
        v = payload.get(key)
        if isinstance(v, (int, float)):
            parts.append(f"{key}:{v}")
    return "\n".join(parts)

