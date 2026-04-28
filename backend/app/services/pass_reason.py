from __future__ import annotations

from collections import Counter
from typing import Any


LOW_SCORE_THRESHOLD = 50
DEFAULT_REASON_CODE = "insufficient_public_evidence"
REASON_COPY = {
    "weak_builder_evidence": (
        "Weak builder evidence",
        "the review does not show enough hands-on builder or shipping evidence",
    ),
    "insufficient_ai_native_signal": (
        "Insufficient AI-native signal",
        "the review does not show enough direct AI-native product or technical work",
    ),
    DEFAULT_REASON_CODE: (
        "Insufficient public evidence",
        "the review does not provide enough public evidence to justify moving forward",
    ),
}
ACTIONABLE_REFINEMENTS = {
    "too_enterprise_sales_oriented": {
        "suggestion_type": "query_rewrite",
        "suggestion_text": (
            "Tighten sourcing queries toward builders, founders, and AI product shippers "
            "instead of enterprise sales or GTM profiles."
        ),
    },
    "weak_builder_evidence": {
        "suggestion_type": "rubric_adjustment",
        "suggestion_text": (
            "Clarify the builder-evidence rubric so reviewers consistently distinguish "
            "hands-on shipping from advisory or leadership-only experience."
        ),
    },
}


def draft_pass_reason(review: Any) -> dict[str, Any]:
    """Draft a pass reason from review dimensions and stated risks.

    Rules deliberately combine structured dimension scores with review risks:
    dimensions identify the rubric area that underperformed, while risks provide
    candidate-specific evidence and language for the drafted explanation.
    """
    normalized_review = _review_dict(review)
    risks = _evidence_texts(normalized_review, "risks")
    uncertainties = _evidence_texts(normalized_review, "uncertainties")
    evidence = [*risks, *uncertainties]
    reason_code = _structured_reason_code(normalized_review)

    title, summary = REASON_COPY.get(
        reason_code,
        ("Structured pass reason", f"the review supplied pass reason code {reason_code}"),
    )

    return {
        "reason_code": reason_code,
        "reason_text": _reason_text(title, summary, evidence),
        "evidence": evidence,
    }


def suggest_refinements(pass_reasons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reason_counts = Counter(
        reason.get("reason_code") for reason in pass_reasons if reason.get("reason_code")
    )
    suggestions: list[dict[str, Any]] = []

    for reason_code, suggestion in ACTIONABLE_REFINEMENTS.items():
        if reason_counts[reason_code]:
            suggestions.append({**suggestion, "reason_codes": [reason_code]})

    return suggestions


def _review_dict(review: Any) -> dict[str, Any]:
    if isinstance(review, dict):
        return review
    return {}


def _list_value(review: dict[str, Any], key: str) -> list[Any]:
    value = review.get(key, [])
    if isinstance(value, list):
        return value
    return []


def _evidence_texts(review: dict[str, Any], key: str) -> list[str]:
    evidence: list[str] = []
    for value in _list_value(review, key):
        text = _safe_scalar_text(value)
        if text:
            evidence.append(text)
    return evidence


def _safe_scalar_text(value: Any) -> str | None:
    if value is None or isinstance(value, dict | list | tuple | set):
        return None
    if isinstance(value, str | int | float | bool):
        text = str(value).strip()
        if text:
            return text
    return None


def _safe_reason_code(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    reason_code = value.strip()
    if reason_code:
        return reason_code
    return None


def _structured_reason_code(review: dict[str, Any]) -> str:
    for key in ("pass_reason_code", "primary_gap_code", "reason_code", "gap_code"):
        reason_code = _safe_reason_code(review.get(key))
        if reason_code:
            return reason_code

    dimension_codes: list[tuple[float, str]] = []
    for dimension in _list_value(review, "dimension_scores"):
        if not isinstance(dimension, dict):
            continue
        score = dimension.get("score")
        if (
            isinstance(score, int | float)
            and not isinstance(score, bool)
            and score < LOW_SCORE_THRESHOLD
        ):
            for key in ("reason_code", "gap_code", "pass_reason_code", "primary_gap_code"):
                reason_code = _safe_reason_code(dimension.get(key))
                if reason_code:
                    dimension_codes.append((float(score), reason_code))
                    break

    if dimension_codes:
        return min(dimension_codes, key=lambda item: item[0])[1]
    return DEFAULT_REASON_CODE


def _reason_text(title: str, summary: str, evidence: list[str]) -> str:
    if evidence:
        return f"{title}: {summary}. Evidence: {evidence[0]}"
    return f"{title}: {summary}."
