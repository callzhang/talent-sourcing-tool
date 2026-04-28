from app.services.pass_reason import draft_pass_reason, suggest_refinements


def test_draft_pass_reason_prioritizes_weak_builder_evidence():
    review = {
        "risks": ["No public evidence of shipping AI products"],
        "dimension_scores": [{"name": "Builder Evidence", "score": 35}],
    }
    draft = draft_pass_reason(review)

    assert draft["reason_code"] == "weak_builder_evidence"
    assert "builder" in draft["reason_text"].lower()
    assert draft["evidence"] == ["No public evidence of shipping AI products"]


def test_draft_pass_reason_identifies_enterprise_sales_orientation():
    review = {
        "risks": ["Background is mostly enterprise sales leadership, not hands-on product work"],
        "dimension_scores": [{"name": "Founder / Builder Evidence", "score": 62}],
    }

    draft = draft_pass_reason(review)

    assert draft["reason_code"] == "too_enterprise_sales_oriented"
    assert "sales" in draft["reason_text"].lower()


def test_draft_pass_reason_identifies_insufficient_ai_native_signal():
    review = {
        "risks": ["Candidate has general SaaS experience without meaningful AI-native work"],
        "dimension_scores": [{"name": "AI Native Signal", "score": 40}],
    }

    draft = draft_pass_reason(review)

    assert draft["reason_code"] == "insufficient_ai_native_signal"
    assert "ai" in draft["reason_text"].lower()


def test_draft_pass_reason_falls_back_to_public_evidence_gap():
    draft = draft_pass_reason({"risks": [], "dimension_scores": []})

    assert draft["reason_code"] == "insufficient_public_evidence"
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


def test_suggest_refinements_falls_back_to_jd_rewrite():
    suggestions = suggest_refinements(
        pass_reasons=[
            {
                "reason_code": "insufficient_ai_native_signal",
                "reason_text": "Weak AI signal",
            }
        ]
    )

    assert any(item["suggestion_type"] == "jd_rewrite" for item in suggestions)
