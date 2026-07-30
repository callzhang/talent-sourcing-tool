from collections.abc import Generator

from fastapi.testclient import TestClient
import httpx

from app.main import app


def client() -> Generator[TestClient, None, None]:
    app.state.create_tables_on_startup = False
    with TestClient(app) as test_client:
        yield test_client
    app.state.create_tables_on_startup = True


def test_system_status_reports_local_environment_without_warnings(monkeypatch):
    from app.api import system

    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr(system.settings, "database_url", "sqlite:////tmp/local.sqlite3")
    monkeypatch.setattr(system.settings, "openai_api_key", "")
    monkeypatch.setattr(system.settings, "review_provider", "codex")
    monkeypatch.setattr(system.settings, "exa_api_key", "")
    monkeypatch.setattr(system.settings, "brightdata_api_key", "")
    monkeypatch.setattr(system.settings, "brightdata_zone", "")

    app.state.create_tables_on_startup = False
    with TestClient(app) as test_client:
        response = test_client.get("/api/system/status")
    app.state.create_tables_on_startup = True

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    payload = response.json()
    assert payload["environment"] == "local"
    assert payload["deployment_ready"] is True
    assert payload["hard_blockers"] == []
    assert payload["optional_degradations"] == []
    assert payload["capabilities"]["linkedin_configured"] is False
    assert payload["capabilities"]["channel_availability"]["github"] is True
    assert payload["capabilities"]["required_channels"] == [
        "linkedin",
        "github",
        "openreview",
        "arxiv",
        "exa",
    ]
    assert payload["capabilities"]["optional_channels"] == ["brightdata_discover"]
    assert payload["capabilities"]["required_provider_checks"] == ["exa"]
    assert payload["capabilities"]["optional_provider_checks"] == ["brightdata"]
    assert payload["capabilities"]["missing_env_vars"] == {
        "storage": [],
        "review": [],
        "channels": {
            "linkedin": [
                "TALENT_EXA_API_KEY",
                "TALENT_BRIGHTDATA_API_KEY",
                "TALENT_BRIGHTDATA_ZONE",
            ],
            "github": [],
            "openreview": [],
            "arxiv": [],
            "exa": ["TALENT_EXA_API_KEY"],
            "brightdata_discover": [
                "TALENT_BRIGHTDATA_API_KEY",
                "TALENT_BRIGHTDATA_ZONE",
            ],
        },
    }
    assert payload["warnings"] == [
        "LinkedIn, Exa, and Bright Data channels are not configured. Only public channels are currently available."
    ]
    assert payload["delivery_resources"] == {
        "production_url": "https://talent-sourcing-tool-zeta.vercel.app",
        "local_url": "http://127.0.0.1:5173",
        "owner_checklist_path": "docs/production-owner-checklist.md",
        "runbook_path": "docs/vercel-production-runbook-2026-07-29.md",
        "verification_commands": [
            "python3 scripts/prepare_vercel_env.py --strict",
            "vercel --prod --yes",
            "./scripts/verify_production.sh",
        ],
        "owner_prompts": [],
    }


def test_system_status_reports_vercel_blockers(monkeypatch):
    from app.api import system

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(system.settings, "database_url", "sqlite:////tmp/talent_sourcing.sqlite3")
    monkeypatch.setattr(system.settings, "openai_api_key", "")
    monkeypatch.setattr(system.settings, "review_provider", "openai")
    monkeypatch.setattr(system.settings, "exa_api_key", "")
    monkeypatch.setattr(system.settings, "brightdata_api_key", "")
    monkeypatch.setattr(system.settings, "brightdata_zone", "")

    app.state.create_tables_on_startup = False
    with TestClient(app) as test_client:
        response = test_client.get("/api/system/status")
    app.state.create_tables_on_startup = True

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    payload = response.json()
    assert payload["environment"] == "vercel"
    assert payload["deployment_ready"] is False
    assert payload["hard_blockers"] == [
        {
            "code": "durable_storage_missing",
            "message": "Production is using temporary SQLite storage on /tmp. Configure DATABASE_URL, TALENT_DATABASE_URL, or TURSO_DATABASE_URL with TURSO_AUTH_TOKEN for durable state.",
            "env_vars": ["DATABASE_URL", "TALENT_DATABASE_URL", "TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN"],
        },
        {
            "code": "review_provider_missing_key",
            "message": "AI review is not configured for deployment. Set TALENT_OPENAI_API_KEY.",
            "env_vars": ["TALENT_OPENAI_API_KEY"],
        },
        {
            "code": "required_channels_incomplete",
            "message": "Search channels are incomplete for production. Configure: LinkedIn, Exa.",
            "channels": ["linkedin", "exa"],
        },
    ]
    assert payload["optional_degradations"] == [
        {
            "code": "optional_channel_unavailable",
            "message": "Optional production channel unavailable: Bright Data Discover.",
            "channels": ["brightdata_discover"],
            "env_vars": ["TALENT_BRIGHTDATA_API_KEY", "TALENT_BRIGHTDATA_ZONE"],
        }
    ]
    assert "Configure DATABASE_URL, TALENT_DATABASE_URL, or TURSO_DATABASE_URL" in payload["warnings"][0]
    assert "AI review is not configured for deployment." in payload["warnings"][1]
    assert payload["warnings"][2] == (
        "Search channels are incomplete for production. Configure: LinkedIn, Exa."
    )
    assert payload["warnings"][3] == "Optional production channel unavailable: Bright Data Discover."
    assert payload["capabilities"]["linkedin_configured"] is False
    assert payload["capabilities"]["channel_availability"]["brightdata_discover"] is False
    assert payload["capabilities"]["missing_env_vars"]["storage"] == [
        "DATABASE_URL",
        "TALENT_DATABASE_URL",
        "TURSO_DATABASE_URL",
        "TURSO_AUTH_TOKEN",
    ]
    assert payload["capabilities"]["missing_env_vars"]["review"] == [
        "TALENT_OPENAI_API_KEY"
    ]


def test_system_status_reports_linkedin_available_when_exa_is_configured(monkeypatch):
    from app.api import system

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(system.settings, "database_url", "postgresql://example")
    monkeypatch.setattr(system.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(system.settings, "review_provider", "openai")
    monkeypatch.setattr(system.settings, "exa_api_key", "exa-key")
    monkeypatch.setattr(system.settings, "brightdata_api_key", "")
    monkeypatch.setattr(system.settings, "brightdata_zone", "")

    app.state.create_tables_on_startup = False
    with TestClient(app) as test_client:
        response = test_client.get("/api/system/status")
    app.state.create_tables_on_startup = True

    assert response.status_code == 200
    payload = response.json()
    assert payload["capabilities"]["linkedin_configured"] is True
    assert payload["hard_blockers"] == []
    assert payload["optional_degradations"] == [
        {
            "code": "optional_channel_unavailable",
            "message": "Optional production channel unavailable: Bright Data Discover.",
            "channels": ["brightdata_discover"],
            "env_vars": ["TALENT_BRIGHTDATA_API_KEY", "TALENT_BRIGHTDATA_ZONE"],
        }
    ]
    assert payload["capabilities"]["channel_availability"]["linkedin"] is True
    assert payload["capabilities"]["channel_availability"]["exa"] is True
    assert payload["capabilities"]["channel_availability"]["brightdata_discover"] is False
    assert payload["capabilities"]["missing_env_vars"]["channels"]["linkedin"] == []
    assert payload["capabilities"]["missing_env_vars"]["channels"]["exa"] == []
    assert payload["capabilities"]["missing_env_vars"]["channels"][
        "brightdata_discover"
    ] == ["TALENT_BRIGHTDATA_API_KEY", "TALENT_BRIGHTDATA_ZONE"]
    assert payload["deployment_ready"] is True
    assert payload["warnings"] == [
        "Optional production channel unavailable: Bright Data Discover."
    ]


def test_system_status_prefers_explicit_delivery_urls(monkeypatch):
    from app.api import system

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("TALENT_PUBLIC_APP_URL", "https://hiring.example.com")
    monkeypatch.setenv("TALENT_LOCAL_APP_URL", "http://127.0.0.1:4173")
    monkeypatch.setattr(system.settings, "database_url", "postgresql://example")
    monkeypatch.setattr(system.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(system.settings, "review_provider", "openai")
    monkeypatch.setattr(system.settings, "exa_api_key", "exa-key")
    monkeypatch.setattr(system.settings, "brightdata_api_key", "")
    monkeypatch.setattr(system.settings, "brightdata_zone", "")

    payload = system.system_status_payload()
    assert payload["delivery_resources"]["production_url"] == "https://hiring.example.com"
    assert payload["delivery_resources"]["local_url"] == "http://127.0.0.1:4173"


def test_provider_checks_report_expired_brightdata_key_and_missing_exa(monkeypatch):
    from app.api import system

    class FakeClient:
        def get(self, url, headers=None):  # noqa: ANN001
            request = httpx.Request("GET", url, headers=headers)
            response = httpx.Response(401, request=request, text="Token expired")
            raise httpx.HTTPStatusError("expired", request=request, response=response)

    monkeypatch.setattr(system.settings, "exa_api_key", "")
    monkeypatch.setattr(system.settings, "brightdata_api_key", "bright-key")
    monkeypatch.setattr(system.settings, "brightdata_zone", "")

    payload = system.provider_checks_payload(client=FakeClient())
    assert payload == {
        "providers": {
            "exa": {
                "status": "missing_key",
                "detail": "TALENT_EXA_API_KEY is not configured.",
            },
            "brightdata": {
                "status": "expired_key",
                "detail": "Bright Data API key exists but is expired.",
            },
        }
    }


def test_provider_checks_report_active_zones_when_zone_is_missing(monkeypatch):
    from app.api import system

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class FakeClient:
        def post(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return FakeResponse({})

        def get(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return FakeResponse([{"name": "discover_zone"}, {"name": "serp_zone"}])

    monkeypatch.setattr(system.settings, "exa_api_key", "exa-key")
    monkeypatch.setattr(system.settings, "brightdata_api_key", "bright-key")
    monkeypatch.setattr(system.settings, "brightdata_zone", "")

    payload = system.provider_checks_payload(client=FakeClient())
    assert payload["providers"]["exa"] == {
        "status": "ok",
        "detail": "Exa API key accepted a search request.",
    }
    assert payload["providers"]["brightdata"] == {
        "status": "missing_zone",
        "detail": "Bright Data key is valid, but TALENT_BRIGHTDATA_ZONE is missing.",
        "active_zones": ["discover_zone", "serp_zone"],
    }


def test_provider_checks_endpoint_disables_caching(monkeypatch):
    from app.api import system

    monkeypatch.setattr(system.settings, "exa_api_key", "")
    monkeypatch.setattr(system.settings, "brightdata_api_key", "")
    monkeypatch.setattr(system.settings, "brightdata_zone", "")

    app.state.create_tables_on_startup = False
    with TestClient(app) as test_client:
        response = test_client.get("/api/system/provider-checks")
    app.state.create_tables_on_startup = True

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
