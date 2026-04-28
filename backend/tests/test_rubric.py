from app.schemas import JobCreate
from app.services.rubric import generate_rubric


def dimension_names(job: JobCreate) -> list[str]:
    rubric = generate_rubric(job)
    return [dimension["name"] for dimension in rubric["dimensions"]]


def test_rubric_includes_product_and_market_discovery_for_all_jobs():
    names = dimension_names(
        JobCreate(
            title="AI Product Engineer",
            description="Build AI prototypes.",
            target_profile_text="Strong builder.",
        )
    )

    assert "Product and Market Discovery Judgment" in names


def test_rubric_does_not_branch_on_pmm_marketing_terms():
    names = dimension_names(
        JobCreate(
            title="PMM Lead",
            description="Own product marketing and GTM for AI launches.",
            target_profile_text="Strong positioning and market judgment.",
        )
    )

    assert "Product Marketing Judgment" not in names
    assert "Product and Market Discovery Judgment" in names
