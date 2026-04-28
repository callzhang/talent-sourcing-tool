import pytest

from app.services.pass_reason import draft_pass_reason, suggest_refinements


def test_draft_pass_reason_uses_review_level_structured_reason_code():
    review = {
        "risks": ["No public evidence of shipping AI products"],
        "pass_reason_code": "weak_builder_evidence",
        "dimension_scores": [{"name": "AI Native Signal", "score": 35}],
    }
    draft = draft_pass_reason(review)

    assert draft["reason_code"] == "weak_builder_evidence"
    assert "builder" in draft["reason_text"].lower()
    assert draft["evidence"] == ["No public evidence of shipping AI products"]


def test_draft_pass_reason_uses_dimension_structured_gap_code():
    review = {
        "risks": ["Candidate has general SaaS experience without meaningful AI-native work"],
        "dimension_scores": [
            {
                "name": "General evaluation",
                "score": 40,
                "gap_code": "insufficient_ai_native_signal",
            }
        ],
    }

    draft = draft_pass_reason(review)

    assert draft["reason_code"] == "insufficient_ai_native_signal"
    assert "ai" in draft["reason_text"].lower()


def test_draft_pass_reason_does_not_route_from_dimension_names_or_risk_keywords():
    review = {
        "risks": [
            "Background is mostly enterprise sales leadership, not hands-on builder work"
        ],
        "dimension_scores": [{"name": "AI Native Signal", "score": 40}],
    }

    draft = draft_pass_reason(review)

    assert draft["reason_code"] == "insufficient_public_evidence"


@pytest.mark.parametrize(
    "reason_code",
    [True, False, 0, 1, 12.5, "", "   "],
)
def test_draft_pass_reason_ignores_malformed_review_level_reason_codes(reason_code):
    draft = draft_pass_reason({"reason_code": reason_code})

    assert draft["reason_code"] == "insufficient_public_evidence"


@pytest.mark.parametrize(
    "reason_code",
    [True, False, 0, 1, 12.5, "", "   "],
)
def test_draft_pass_reason_ignores_malformed_dimension_reason_codes(reason_code):
    draft = draft_pass_reason(
        {"dimension_scores": [{"score": 35, "reason_code": reason_code}]}
    )

    assert draft["reason_code"] == "insufficient_public_evidence"


def test_draft_pass_reason_falls_back_to_public_evidence_gap():
    draft = draft_pass_reason({"risks": [], "dimension_scores": []})

    assert draft["reason_code"] == "insufficient_public_evidence"
    assert draft["evidence"] == []


@pytest.mark.parametrize(
    "review",
    [
        None,
        [],
        "x",
        {"risks": None},
        {"dimension_scores": None},
    ],
)
def test_draft_pass_reason_handles_malformed_review_shapes(review):
    draft = draft_pass_reason(review)

    assert draft["reason_code"] == "insufficient_public_evidence"
    assert draft["evidence"] == []


def test_draft_pass_reason_filters_evidence_to_user_facing_scalars():
    review = {
        "risks": [
            None,
            {"detail": "hidden object"},
            "Visible risk",
            123,
            True,
        ],
        "uncertainties": [
            "Unclear AI depth",
            {"detail": "hidden uncertainty"},
            False,
        ],
        "dimension_scores": None,
    }

    draft = draft_pass_reason(review)

    assert draft["reason_code"] == "insufficient_public_evidence"
    assert draft["evidence"] == ["Visible risk", "123", "True", "Unclear AI depth", "False"]


def test_draft_pass_reason_ignores_non_scalar_evidence_and_non_dict_dimensions():
    draft = draft_pass_reason(
        {
            "risks": [object()],
            "dimension_scores": [
                "not-a-dimension",
                {
                    "name": "Weak dimension",
                    "score": 40,
                    "reason_code": "weak_builder_evidence",
                },
            ],
        }
    )

    assert draft["reason_code"] == "weak_builder_evidence"
    assert draft["evidence"] == []


def test_suggest_refinements_mentions_search_query():
    suggestions = suggest_refinements(
        pass_reasons=[
            {"reason_code": "too_enterprise_sales_oriented", "reason_text": "Too sales-heavy"}
        ]
    )

    assert any(item["suggestion_type"] == "query_rewrite" for item in suggestions)


def test_suggest_refinements_maps_weak_builder_to_rubric_adjustment():
    suggestions = suggest_refinements(
        pass_reasons=[
            {
                "reason_code": "weak_builder_evidence",
                "reason_text": "No builder evidence",
            }
        ]
    )

    assert any(item["suggestion_type"] == "rubric_adjustment" for item in suggestions)


def test_suggest_refinements_returns_no_fallback_for_non_actionable_reasons():
    suggestions = suggest_refinements(
        pass_reasons=[
            {
                "reason_code": "insufficient_ai_native_signal",
                "reason_text": "Weak AI signal",
            }
        ]
    )

    assert suggestions == []
