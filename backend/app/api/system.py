from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Response
import httpx

from app.core.config import settings
from app.services.review_worker import resolve_review_provider

router = APIRouter(prefix="/system", tags=["system"])

CHANNEL_LABELS = {
    "linkedin": "LinkedIn",
    "github": "GitHub",
    "openreview": "OpenReview",
    "arxiv": "arXiv",
    "exa": "Exa",
    "brightdata_discover": "Bright Data Discover",
}
PUBLIC_CHANNELS = ["github", "openreview", "arxiv"]
REQUIRED_PRODUCTION_CHANNELS = [
    "linkedin",
    "github",
    "openreview",
    "arxiv",
    "exa",
]
OPTIONAL_PRODUCTION_CHANNELS = [
    "brightdata_discover",
]
REQUIRED_PROVIDER_CHECKS = ["exa"]
OPTIONAL_PROVIDER_CHECKS = ["brightdata"]
STORAGE_ENV_VARS = [
    "DATABASE_URL",
    "TALENT_DATABASE_URL",
    "TURSO_DATABASE_URL",
    "TURSO_AUTH_TOKEN",
]


def resolve_production_app_url() -> str:
    explicit_url = os.environ.get("TALENT_PUBLIC_APP_URL", "").strip()
    if explicit_url:
        return explicit_url
    project_production_url = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL", "").strip()
    if project_production_url:
        return f"https://{project_production_url.removeprefix('https://')}"
    vercel_url = os.environ.get("VERCEL_URL", "").strip()
    if vercel_url:
        return f"https://{vercel_url.removeprefix('https://')}"
    return "https://talent-sourcing-tool-zeta.vercel.app"


def resolve_local_app_url() -> str:
    explicit_url = os.environ.get("TALENT_LOCAL_APP_URL", "").strip()
    if explicit_url:
        return explicit_url
    return "http://127.0.0.1:5173"


def system_status_payload() -> dict[str, Any]:
    is_vercel = os.environ.get("VERCEL") == "1"
    database_url = settings.database_url.strip()
    review_provider = resolve_review_provider(settings)
    brightdata_configured = bool(
        settings.brightdata_api_key.strip() and settings.brightdata_zone.strip()
    )
    exa_configured = bool(settings.exa_api_key.strip())
    linkedin_configured = exa_configured or brightdata_configured
    persistent_storage_configured = not (
        is_vercel and database_url == "sqlite:////tmp/talent_sourcing.sqlite3"
    )
    review_configured = review_provider != "openai" or bool(settings.openai_api_key.strip())
    missing_database_env_vars = (
        []
        if persistent_storage_configured
        else STORAGE_ENV_VARS
    )
    missing_review_env_vars = (
        []
        if review_configured
        else ["TALENT_OPENAI_API_KEY"]
    )
    missing_sourcing_env_vars: dict[str, list[str]] = {
        "linkedin": [],
        "github": [],
        "openreview": [],
        "arxiv": [],
        "exa": [],
        "brightdata_discover": [],
    }
    if not exa_configured:
        missing_sourcing_env_vars["exa"] = ["TALENT_EXA_API_KEY"]
    if not brightdata_configured:
        missing_sourcing_env_vars["brightdata_discover"] = [
            "TALENT_BRIGHTDATA_API_KEY",
            "TALENT_BRIGHTDATA_ZONE",
        ]
    if not linkedin_configured:
        missing_sourcing_env_vars["linkedin"] = [
            "TALENT_EXA_API_KEY",
            "TALENT_BRIGHTDATA_API_KEY",
            "TALENT_BRIGHTDATA_ZONE",
        ]
    channel_availability = {
        "linkedin": linkedin_configured,
        "github": True,
        "openreview": True,
        "arxiv": True,
        "exa": exa_configured,
        "brightdata_discover": brightdata_configured,
    }
    missing_required_production_channels = [
        channel
        for channel in REQUIRED_PRODUCTION_CHANNELS
        if not channel_availability[channel]
    ]
    sourcing_channels_ready = not is_vercel or not missing_required_production_channels

    blockers: list[dict[str, str | list[str]]] = []
    optional_degradations: list[dict[str, str | list[str]]] = []
    warnings: list[str] = []
    if not persistent_storage_configured:
        message = (
            "Production is using temporary SQLite storage on /tmp. Configure DATABASE_URL, "
            "TALENT_DATABASE_URL, or TURSO_DATABASE_URL with TURSO_AUTH_TOKEN for durable state."
        )
        warnings.append(message)
        blockers.append(
            {
                "code": "durable_storage_missing",
                "message": message,
                "env_vars": STORAGE_ENV_VARS,
            }
        )
    if not review_configured:
        message = (
            "AI review is not configured for deployment. Set TALENT_OPENAI_API_KEY."
        )
        warnings.append(message)
        blockers.append(
            {
                "code": "review_provider_missing_key",
                "message": message,
                "env_vars": ["TALENT_OPENAI_API_KEY"],
            }
        )
    if is_vercel and missing_required_production_channels:
        message = (
            "Search channels are incomplete for production. Configure: "
            + ", ".join(CHANNEL_LABELS[channel] for channel in missing_required_production_channels)
            + "."
        )
        warnings.append(message)
        blockers.append(
            {
                "code": "required_channels_incomplete",
                "message": message,
                "channels": missing_required_production_channels,
            }
        )
    if is_vercel and not brightdata_configured:
        message = "Optional production channel unavailable: Bright Data Discover."
        warnings.append(message)
        optional_degradations.append(
            {
                "code": "optional_channel_unavailable",
                "message": message,
                "channels": OPTIONAL_PRODUCTION_CHANNELS,
                "env_vars": ["TALENT_BRIGHTDATA_API_KEY", "TALENT_BRIGHTDATA_ZONE"],
            }
        )
    elif not exa_configured and not brightdata_configured:
        warnings.append(
            "LinkedIn, Exa, and Bright Data channels are not configured. Only public channels are currently available."
        )

    return {
        "environment": "vercel" if is_vercel else "local",
        "deployment_ready": (
            persistent_storage_configured and review_configured and sourcing_channels_ready
        ),
        "warnings": warnings,
        "hard_blockers": blockers,
        "optional_degradations": optional_degradations,
        "delivery_resources": {
            "production_url": resolve_production_app_url(),
            "local_url": resolve_local_app_url(),
            "owner_checklist_path": "docs/production-owner-checklist.md",
            "runbook_path": "docs/vercel-production-runbook-2026-07-29.md",
            "verification_commands": [
                "python3 scripts/prepare_vercel_env.py --strict",
                "vercel --prod --yes",
                "./scripts/verify_production.sh",
            ],
            "owner_prompts": [
                *(
                    [
                        "TALENT_DATABASE_URL 或 TURSO_DATABASE_URL + TURSO_AUTH_TOKEN 由谁提供"
                    ]
                    if not persistent_storage_configured
                    else []
                ),
                *( ["TALENT_OPENAI_API_KEY 由谁提供"] if not review_configured else [] ),
            ],
        },
        "capabilities": {
            "persistent_storage_configured": persistent_storage_configured,
            "review_provider": review_provider,
            "review_configured": review_configured,
            "linkedin_configured": linkedin_configured,
            "exa_configured": exa_configured,
            "brightdata_configured": brightdata_configured,
            "public_channels": PUBLIC_CHANNELS,
            "required_channels": REQUIRED_PRODUCTION_CHANNELS,
            "optional_channels": OPTIONAL_PRODUCTION_CHANNELS,
            "required_provider_checks": REQUIRED_PROVIDER_CHECKS,
            "optional_provider_checks": OPTIONAL_PROVIDER_CHECKS,
            "channel_availability": channel_availability,
            "missing_env_vars": {
                "storage": missing_database_env_vars,
                "review": missing_review_env_vars,
                "channels": missing_sourcing_env_vars,
            },
        },
    }


def provider_checks_payload(
    *,
    app_settings=settings,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    http_client = client or httpx.Client(
        timeout=20.0,
        follow_redirects=True,
        trust_env=False,
        headers={"User-Agent": "talent-sourcing-tool/0.1"},
    )
    exa_api_key = app_settings.exa_api_key.strip()
    brightdata_api_key = app_settings.brightdata_api_key.strip()
    brightdata_zone = app_settings.brightdata_zone.strip()

    exa_check = {"status": "missing_key", "detail": "TALENT_EXA_API_KEY is not configured."}
    if exa_api_key:
        try:
            response = http_client.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": exa_api_key},
                json={
                    "query": "site:linkedin.com/in product marketing candidate san francisco",
                    "type": "auto",
                    "numResults": 1,
                },
            )
            response.raise_for_status()
            exa_check = {"status": "ok", "detail": "Exa API key accepted a search request."}
        except httpx.HTTPStatusError as exc:
            exa_check = {
                "status": f"http_{exc.response.status_code}",
                "detail": f"Exa returned HTTP {exc.response.status_code}.",
            }
        except httpx.HTTPError as exc:
            exa_check = {"status": "network_error", "detail": str(exc)}

    brightdata_check: dict[str, Any] = {
        "status": "missing_key",
        "detail": "TALENT_BRIGHTDATA_API_KEY is not configured.",
    }
    if brightdata_api_key:
        try:
            response = http_client.get(
                "https://api.brightdata.com/zone/get_active_zones",
                headers={"Authorization": f"Bearer {brightdata_api_key}"},
            )
            response.raise_for_status()
            payload = response.json()
            active_zones = sorted(
                {
                    str(item.get("name", "")).strip()
                    for item in payload
                    if isinstance(item, dict) and str(item.get("name", "")).strip()
                }
            )
            if not brightdata_zone:
                brightdata_check = {
                    "status": "missing_zone",
                    "detail": "Bright Data key is valid, but TALENT_BRIGHTDATA_ZONE is missing.",
                    "active_zones": active_zones,
                }
            elif brightdata_zone not in active_zones:
                brightdata_check = {
                    "status": "zone_not_found",
                    "detail": f"Configured zone '{brightdata_zone}' was not found in active zones.",
                    "active_zones": active_zones,
                }
            else:
                brightdata_check = {
                    "status": "ok",
                    "detail": "Bright Data key and zone are valid.",
                    "active_zones": active_zones,
                }
        except httpx.HTTPStatusError as exc:
            response_text = exc.response.text.strip().lower()
            if exc.response.status_code == 401 and "expired" in response_text:
                brightdata_check = {
                    "status": "expired_key",
                    "detail": "Bright Data API key exists but is expired.",
                }
            else:
                brightdata_check = {
                    "status": f"http_{exc.response.status_code}",
                    "detail": f"Bright Data returned HTTP {exc.response.status_code}.",
                }
        except httpx.HTTPError as exc:
            brightdata_check = {"status": "network_error", "detail": str(exc)}

    return {
        "providers": {
            "exa": exa_check,
            "brightdata": brightdata_check,
        }
    }


def apply_no_store_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"


@router.get("/status")
def get_system_status(response: Response) -> dict[str, Any]:
    apply_no_store_headers(response)
    return system_status_payload()


@router.get("/provider-checks")
def get_provider_checks(response: Response) -> dict[str, Any]:
    apply_no_store_headers(response)
    return provider_checks_payload()
