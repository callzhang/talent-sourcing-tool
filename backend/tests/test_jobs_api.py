from fastapi.testclient import TestClient

from app.main import app


def test_create_job_generates_rubric():
    client = TestClient(app)

    response = client.post(
        "/api/jobs",
        json={
            "title": "AI Product Engineer",
            "description": "Build AI prototypes with strong vibe coding.",
            "target_profile_text": "Strong builder, AI-native, product sense.",
            "red_flags_text": "Only traditional backend, no product sense.",
            "search_notes": "Search early AI app builders.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job"]["title"] == "AI Product Engineer"
    assert data["rubric"]["version"] == 1
    assert len(data["rubric"]["rubric"]["dimensions"]) >= 3
