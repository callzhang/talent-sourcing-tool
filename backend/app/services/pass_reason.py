from __future__ import annotations

from collections import Counter
from typing import Any


LOW_SCORE_THRESHOLD = 50


def draft_pass_reason(review: dict[str, Any]) -> dict[str, Any]:
    """Draft a pass reason from review dimensions and stated risks.

    Rules deliberately combine structured dimension scores with review risks:
    dimensions identify the rubric area that underperformed, while risks provide
    candidate-specific evidence and language for the drafted explanation.
    """
    risks = _risk_texts(review)
    low_dimensions = _low_dimension_names(review)
    evidence = risks

    if _has_dimension_signal(low_dimensions, ("builder", "founder", "shipping")):
        return {
            "reason_code": "weak_builder_evidence",
            "reason_text": _reason_text(
                "Weak builder evidence",
                "the review does not show enough hands-on builder or shipping evidence",
                evidence,
            ),
            "evidence": evidence,
        }

    if _has_dimension_signal(low_dimensions, ("ai", "native", "technical")):
        return {
            "reason_code": "insufficient_ai_native_signal",
            "reason_text": _reason_text(
                "Insufficient AI-native signal",
                "the review does not show enough direct AI-native product or technical work",
                evidence,
            ),
            "evidence": evidence,
        }

    risk_blob = " ".join(risks).lower()
    if "sales" in risk_blob and any(
        marker in risk_blob for marker in ("enterprise", "gtm", "go-to-market", "account")
    ):
        return {
            "reason_code": "too_enterprise_sales_oriented",
            "reason_text": _reason_text(
                "Too enterprise sales oriented",
                "the strongest signals are enterprise sales or GTM-oriented rather than product-building",
                evidence,
            ),
            "evidence": evidence,
        }

    return {
        "reason_code": "insufficient_public_evidence",
        "reason_text": _reason_text(
            "Insufficient public evidence",
            "the review does not provide enough public evidence to justify moving forward",
            evidence,
        ),
        "evidence": evidence,
    }


def suggest_refinements(pass_reasons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reason_counts = Counter(
        reason.get("reason_code") for reason in pass_reasons if reason.get("reason_code")
    )
    suggestions: list[dict[str, Any]] = []

    if reason_counts["too_enterprise_sales_oriented"]:
        suggestions.append(
            {
                "suggestion_type": "query_rewrite",
                "suggestion_text": (
                    "Tighten sourcing queries toward builders, founders, and AI product shippers "
                    "instead of enterprise sales or GTM profiles."
                ),
                "reason_codes": ["too_enterprise_sales_oriented"],
            }
        )

    if reason_counts["weak_builder_evidence"]:
        suggestions.append(
            {
                "suggestion_type": "rubric_adjustment",
                "suggestion_text": (
                    "Clarify the builder-evidence rubric so reviewers consistently distinguish "
                    "hands-on shipping from advisory or leadership-only experience."
                ),
                "reason_codes": ["weak_builder_evidence"],
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "suggestion_type": "jd_rewrite",
                "suggestion_text": (
                    "Revisit the job description to make must-have evidence explicit before the "
                    "next sourcing pass."
                ),
                "reason_codes": sorted(reason_counts),
            }
        )

    return suggestions


def _risk_texts(review: dict[str, Any]) -> list[str]:
    return [str(risk) for risk in review.get("risks", []) if str(risk).strip()]


def _low_dimension_names(review: dict[str, Any]) -> list[str]:
    low_dimensions: list[str] = []
    for dimension in review.get("dimension_scores", []):
        if not isinstance(dimension, dict):
            continue
        score = dimension.get("score")
        name = str(dimension.get("name", "")).lower()
        if isinstance(score, int | float) and score < LOW_SCORE_THRESHOLD and name:
            low_dimensions.append(name)
    return low_dimensions


def _has_dimension_signal(dimensions: list[str], terms: tuple[str, ...]) -> bool:
    return any(term in dimension for dimension in dimensions for term in terms)


def _reason_text(title: str, summary: str, evidence: list[str]) -> str:
    if evidence:
        return f"{title}: {summary}. Evidence: {evidence[0]}"
    return f"{title}: {summary}."
