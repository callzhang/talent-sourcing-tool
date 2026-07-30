#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_STATUS_URL = "https://talent-sourcing-tool-zeta.vercel.app/api/system/status"
ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_ALIASES = {
    "DATABASE_URL": ["DATABASE_URL", "TALENT_DATABASE_URL"],
    "TALENT_DATABASE_URL": ["TALENT_DATABASE_URL", "DATABASE_URL"],
    "TALENT_OPENAI_API_KEY": ["TALENT_OPENAI_API_KEY", "OPENAI_API_KEY"],
    "TALENT_EXA_API_KEY": ["TALENT_EXA_API_KEY", "EXA_API_KEY"],
    "TALENT_BRIGHTDATA_API_KEY": ["TALENT_BRIGHTDATA_API_KEY", "BRIGHTDATA_API_KEY"],
    "TALENT_BRIGHTDATA_ZONE": ["TALENT_BRIGHTDATA_ZONE", "BRIGHTDATA_ZONE"],
}


def load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_local_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env.update(load_dotenv(ROOT_DIR / ".env"))
    env.update(load_dotenv(ROOT_DIR / "backend" / ".env"))
    for key, value in os.environ.items():
        if key not in env and value:
            env[key] = value
    return env


def fetch_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_system_status(status_url: str) -> dict[str, Any]:
    return fetch_json(status_url)


def api_base_url_for_status(status_url: str) -> str:
    suffix = "/api/system/status"
    if status_url.endswith(suffix):
        return status_url[: -len(suffix)] + "/api"
    return status_url.rsplit("/", 1)[0]


def provider_checks_url_for_status(status_url: str) -> str:
    if status_url.endswith("/status"):
        return status_url[: -len("/status")] + "/provider-checks"
    return status_url.rstrip("/") + "/provider-checks"


def fetch_provider_checks(provider_checks_url: str) -> dict[str, Any]:
    return fetch_json(provider_checks_url)


def first_available(env: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = env.get(key, "").strip()
        if value:
            return value
    return ""


def validate_brightdata(env: dict[str, str]) -> tuple[str, list[str]]:
    api_key = first_available(env, "TALENT_BRIGHTDATA_API_KEY", "BRIGHTDATA_API_KEY")
    zone = first_available(env, "TALENT_BRIGHTDATA_ZONE", "BRIGHTDATA_ZONE")
    if not api_key:
        return ("missing_key", ["TALENT_BRIGHTDATA_API_KEY", "BRIGHTDATA_API_KEY"])

    request = Request(
        "https://api.brightdata.com/zone/get_active_zones",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        if exc.code == 401 and "expired" in body.lower():
            return ("expired_key", [])
        return (f"http_{exc.code}", [])
    except URLError:
        return ("network_error", [])

    zone_names = sorted(
        {
            str(item.get("name", "")).strip()
            for item in payload if isinstance(item, dict) and str(item.get("name", "")).strip()
        }
    )
    if not zone:
        return ("missing_zone", zone_names)
    if zone not in zone_names:
        return ("zone_not_found", zone_names)
    return ("ok", zone_names)


def render_missing_vars(status: dict[str, Any], local_env: dict[str, str]) -> str:
    missing = (
        status.get("capabilities", {})
        .get("missing_env_vars", {})
    )
    lines: list[str] = []
    sections = {
        "storage": missing.get("storage", []),
        "review": missing.get("review", []),
    }
    channels = missing.get("channels", {})
    for section_name, vars_list in sections.items():
        lines.extend(render_section(section_name, vars_list, local_env))
    for channel_name, vars_list in channels.items():
        if not vars_list:
            continue
        lines.extend(render_section(f"channel:{channel_name}", vars_list, local_env))
    return "\n".join(lines)


def render_status_items(
    title: str,
    items: list[dict[str, Any]] | None,
    local_env: dict[str, str],
) -> str:
    lines = [f"{title}:"]
    if not items:
        lines.append("(none)")
        return "\n".join(lines)

    for item in items:
        code = str(item.get("code", "unknown"))
        message = str(item.get("message", "")).strip()
        lines.append(f"- {code}: {message or '(no message)'}")

        env_vars = item.get("env_vars")
        if isinstance(env_vars, list) and env_vars:
            for variable in env_vars:
                available_locally, resolved_key = find_available_local_key(
                    local_env, str(variable)
                )
                detail = (
                    f"available locally via {resolved_key}"
                    if available_locally and resolved_key != variable
                    else "available locally"
                    if available_locally
                    else "not found locally"
                )
                lines.append(f"  env {variable}: {detail}")

        channels = item.get("channels")
        if isinstance(channels, list) and channels:
            lines.append(
                "  channels=" + ", ".join(str(channel).strip() for channel in channels if str(channel).strip())
            )
    return "\n".join(lines)


def render_section(section_name: str, vars_list: list[str], local_env: dict[str, str]) -> list[str]:
    lines = [f"[{section_name}]"]
    for variable in vars_list:
        available_locally, resolved_key = find_available_local_key(local_env, variable)
        detail = (
            f"available locally via {resolved_key}"
            if available_locally and resolved_key != variable
            else "available locally"
            if available_locally
            else "not found locally"
        )
        lines.append(
            f"- {variable}: {detail}"
        )
    return lines


def find_available_local_key(local_env: dict[str, str], variable: str) -> tuple[bool, str]:
    for candidate in ENV_ALIASES.get(variable, [variable]):
        if local_env.get(candidate, "").strip():
            return True, candidate
    return False, variable


def evaluate_exit_code(
    status: dict[str, Any],
    *,
    strict: bool,
    provider_results: dict[str, str] | None = None,
    write_guard_results: list[dict[str, Any]] | None = None,
) -> int:
    if not strict:
        return 0
    if not status.get("deployment_ready", False):
        return 1
    required_provider_checks = (
        status.get("capabilities", {}).get("required_provider_checks")
        if isinstance(status.get("capabilities"), dict)
        else None
    )
    provider_names = (
        [str(name) for name in required_provider_checks]
        if isinstance(required_provider_checks, list) and required_provider_checks
        else list((provider_results or {}).keys())
    )
    for provider_name in provider_names:
        provider_state = (provider_results or {}).get(provider_name)
        if provider_state != "ok":
            return 1
    for result in write_guard_results or []:
        if result.get("ok") is not True:
            return 1
    return 0


def normalize_provider_results(payload: dict[str, Any]) -> dict[str, str]:
    providers = payload.get("providers", {})
    if not isinstance(providers, dict):
        return {}
    normalized: dict[str, str] = {}
    for provider_name, provider_payload in providers.items():
        if isinstance(provider_payload, dict):
            state = provider_payload.get("status")
            if isinstance(state, str) and state:
                normalized[str(provider_name)] = state
    return normalized


def render_provider_checks(payload: dict[str, Any]) -> str:
    providers = payload.get("providers", {})
    if not isinstance(providers, dict) or not providers:
        return "(none)"
    lines: list[str] = []
    for provider_name, provider_payload in providers.items():
        if not isinstance(provider_payload, dict):
            continue
        state = str(provider_payload.get("status", "unknown"))
        lines.append(f"- {provider_name}={state}")
        detail = provider_payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            lines.append(f"  detail={detail.strip()}")
        active_zones = provider_payload.get("active_zones")
        if isinstance(active_zones, list) and active_zones:
            lines.append(
                "  active_zones="
                + ", ".join(str(zone).strip() for zone in active_zones if str(zone).strip())
            )
    return "\n".join(lines) or "(none)"


def request_json(method: str, url: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    request = Request(url, headers=headers, data=payload, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            parsed_body = json.loads(response_body) if response_body else None
            return response.getcode(), parsed_body
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_body = json.loads(response_body) if response_body else None
        except json.JSONDecodeError:
            parsed_body = response_body
        return exc.code, parsed_body
    except URLError as exc:
        return 0, str(exc)


def planned_write_guard_probes(status: dict[str, Any], status_url: str) -> list[dict[str, Any]]:
    missing = status.get("capabilities", {}).get("missing_env_vars", {})
    probes: list[dict[str, Any]] = []
    api_base_url = api_base_url_for_status(status_url).rstrip("/")

    if missing.get("storage"):
        probes.extend(
            [
                {
                    "name": "create_job",
                    "method": "POST",
                    "url": f"{api_base_url}/jobs",
                    "body": {
                        "title": "Production Guard Probe",
                        "description": "Probe should be blocked before persistence.",
                    },
                    "expected_status": 503,
                },
                {
                    "name": "create_search",
                    "method": "POST",
                    "url": f"{api_base_url}/search",
                    "body": {
                        "job_id": "job_guard_probe",
                        "query": "guard probe",
                    },
                    "expected_status": 503,
                },
                {
                    "name": "create_decision",
                    "method": "POST",
                    "url": f"{api_base_url}/reviews/decision",
                    "body": {
                        "job_id": "job_guard_probe",
                        "candidate_id": "candidate_guard_probe",
                        "decision": "proceed",
                    },
                    "expected_status": 503,
                },
            ]
        )
    if missing.get("review"):
        probes.append(
            {
                "name": "start_review",
                "method": "POST",
                "url": f"{api_base_url}/reviews/start",
                "body": {
                    "job_id": "job_guard_probe",
                    "candidate_id": "candidate_guard_probe",
                },
                "expected_status": 503,
            }
        )
    return probes


def execute_write_guard_probes(probes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for probe in probes:
        status_code, response_body = request_json(
            probe["method"], probe["url"], probe.get("body")
        )
        detail = (
            response_body.get("detail")
            if isinstance(response_body, dict) and isinstance(response_body.get("detail"), str)
            else response_body
        )
        results.append(
            {
                "name": probe["name"],
                "expected_status": probe["expected_status"],
                "actual_status": status_code,
                "ok": status_code == probe["expected_status"],
                "detail": detail,
            }
        )
    return results


def render_write_guard_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "(not needed)"
    lines: list[str] = []
    for result in results:
        state = "ok" if result.get("ok") else "failed"
        lines.append(
            f"- {result['name']}={state} "
            f"(expected {result['expected_status']}, got {result['actual_status']})"
        )
        detail = result.get("detail")
        if isinstance(detail, str) and detail.strip():
            lines.append(f"  detail={detail.strip()}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check production readiness for the Vercel deployment.")
    parser.add_argument(
        "--status-url",
        default=DEFAULT_STATUS_URL,
        help=f"System status endpoint to inspect (default: {DEFAULT_STATUS_URL})",
    )
    parser.add_argument(
        "--skip-provider-checks",
        action="store_true",
        help="Skip live provider checks from the deployed /api/system/provider-checks endpoint.",
    )
    parser.add_argument(
        "--skip-write-guard-checks",
        action="store_true",
        help="Skip live production write-guard probes that expect 503 while deployment is blocked.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code when production is not deployment-ready or a provider check fails.",
    )
    args = parser.parse_args()

    status = fetch_system_status(args.status_url)
    provider_checks_url = provider_checks_url_for_status(args.status_url)
    local_env = load_local_env()
    provider_results: dict[str, str] = {}
    write_guard_results: list[dict[str, Any]] = []

    print(f"status_url={args.status_url}")
    print(f"environment={status['environment']}")
    print(f"deployment_ready={status['deployment_ready']}")
    print("warnings:")
    for warning in status.get("warnings", []):
        print(f"- {warning}")

    print(
        "\n"
        + render_status_items(
            "hard_blockers",
            status.get("hard_blockers"),
            local_env,
        )
    )
    print(
        "\n"
        + render_status_items(
            "optional_degradations",
            status.get("optional_degradations"),
            local_env,
        )
    )
    print("\nmissing_env_vars:")
    print(render_missing_vars(status, local_env) or "(none)")

    if not args.skip_provider_checks:
        print("\nprovider_checks:")
        print(f"provider_checks_url={provider_checks_url}")
        provider_payload = fetch_provider_checks(provider_checks_url)
        provider_results = normalize_provider_results(provider_payload)
        print(render_provider_checks(provider_payload))
    if not args.skip_write_guard_checks:
        print("\nwrite_guard_checks:")
        planned_probes = planned_write_guard_probes(status, args.status_url)
        write_guard_results = execute_write_guard_probes(planned_probes)
        print(render_write_guard_results(write_guard_results))
    return evaluate_exit_code(
        status,
        strict=args.strict,
        provider_results=provider_results,
        write_guard_results=write_guard_results,
    )


if __name__ == "__main__":
    raise SystemExit(main())
