#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
LOCAL_ENV_FILES = [ROOT_DIR / ".env", ROOT_DIR / "backend" / ".env"]
ENV_SPECS = [
    {
        "canonical": "TALENT_DATABASE_URL",
        "aliases": ["TALENT_DATABASE_URL", "DATABASE_URL"],
        "description": "Durable production database URL",
        "required": True,
    },
    {
        "canonical": "TURSO_DATABASE_URL",
        "aliases": ["TURSO_DATABASE_URL"],
        "description": "Turso durable database URL",
        "required": False,
    },
    {
        "canonical": "TURSO_AUTH_TOKEN",
        "aliases": ["TURSO_AUTH_TOKEN"],
        "description": "Turso database authentication token",
        "required": False,
    },
    {
        "canonical": "TALENT_OPENAI_API_KEY",
        "aliases": ["TALENT_OPENAI_API_KEY", "OPENAI_API_KEY"],
        "description": "OpenAI key for production AI review",
        "required": True,
    },
    {
        "canonical": "TALENT_REVIEW_PROVIDER",
        "aliases": ["TALENT_REVIEW_PROVIDER", "REVIEW_PROVIDER"],
        "description": "Optional explicit review provider override",
        "required": False,
    },
    {
        "canonical": "TALENT_REVIEW_MODEL",
        "aliases": ["TALENT_REVIEW_MODEL", "REVIEW_MODEL"],
        "description": "Optional explicit review model override",
        "required": False,
    },
    {
        "canonical": "TALENT_EXA_API_KEY",
        "aliases": ["TALENT_EXA_API_KEY", "EXA_API_KEY"],
        "description": "Exa key for production sourcing",
        "required": False,
    },
    {
        "canonical": "TALENT_BRIGHTDATA_API_KEY",
        "aliases": ["TALENT_BRIGHTDATA_API_KEY", "BRIGHTDATA_API_KEY"],
        "description": "Bright Data API key for production sourcing",
        "required": False,
    },
    {
        "canonical": "TALENT_BRIGHTDATA_ZONE",
        "aliases": ["TALENT_BRIGHTDATA_ZONE", "BRIGHTDATA_ZONE"],
        "description": "Bright Data zone name for production sourcing",
        "required": False,
    },
]


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        if not raw_line or raw_line.lstrip().startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def collect_local_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for env_path in LOCAL_ENV_FILES:
        for key, value in load_env_file(env_path).items():
            if value and key not in values:
                values[key] = value
    for key, value in os.environ.items():
        if value and key not in values:
            values[key] = value
    return values


def resolve_values(local_values: dict[str, str]) -> list[dict[str, str | None]]:
    resolved: list[dict[str, str | None]] = []
    for spec in ENV_SPECS:
        source_key = next(
            (alias for alias in spec["aliases"] if local_values.get(alias, "").strip()),
            None,
        )
        value = local_values.get(source_key, "").strip() if source_key else ""
        resolved.append(
            {
                "canonical": spec["canonical"],
                "description": spec["description"],
                "required": "yes" if spec["required"] else "no",
                "source_key": source_key,
                "value": value or None,
            }
        )
    return resolved


def render_plan(resolved: list[dict[str, str | None]], environment: str) -> str:
    lines = [f"Target environment: {environment}"]
    lines.append("")
    lines.append("Required for readiness:")
    for item in resolved:
        if item["required"] != "yes":
            continue
        canonical = item["canonical"]
        source_key = item["source_key"]
        if canonical == "TALENT_DATABASE_URL" and not item["value"] and has_turso_storage(resolved):
            lines.append("- TALENT_DATABASE_URL: ready via TURSO_DATABASE_URL + TURSO_AUTH_TOKEN")
            continue
        if item["value"]:
            source_note = f" via {source_key}" if source_key and source_key != canonical else ""
            lines.append(f"- {canonical}: ready{source_note}")
        else:
            lines.append(f"- {canonical}: missing locally")
    lines.append("")
    lines.append("Optional channel coverage:")
    for item in resolved:
        if item["required"] != "no":
            continue
        canonical = item["canonical"]
        source_key = item["source_key"]
        if item["value"]:
            source_note = f" via {source_key}" if source_key and source_key != canonical else ""
            lines.append(f"- {canonical}: ready{source_note}")
        else:
            lines.append(f"- {canonical}: missing locally")
    return "\n".join(lines)


def missing_required_items(resolved: list[dict[str, str | None]]) -> list[str]:
    missing = [
        str(item["canonical"])
        for item in resolved
        if item["required"] == "yes" and not item["value"]
    ]
    if "TALENT_DATABASE_URL" in missing and has_turso_storage(resolved):
        missing.remove("TALENT_DATABASE_URL")
    return missing


def has_turso_storage(resolved: list[dict[str, str | None]]) -> bool:
    values = {str(item["canonical"]): str(item.get("value") or "").strip() for item in resolved}
    return bool(values.get("TURSO_DATABASE_URL") and values.get("TURSO_AUTH_TOKEN"))


def ensure_vercel_cli() -> int:
    if shutil.which("vercel"):
        return 0
    print("Missing `vercel` CLI in PATH. Install it before using --apply.", file=sys.stderr)
    return 1


def validate_required_items(resolved: list[dict[str, str | None]]) -> int:
    missing_required = missing_required_items(resolved)
    if not missing_required:
        return 0
    print(
        "Required variables are still missing locally: " + ", ".join(missing_required),
        file=sys.stderr,
    )
    return 1


def apply_env(
    environment: str, resolved: list[dict[str, str | None]], *, include_optional: bool
) -> int:
    if validate_required_items(resolved) != 0:
        print("Refusing to apply a partial Vercel environment.", file=sys.stderr)
        return 1
    if ensure_vercel_cli() != 0:
        return 1

    applied_any = False
    for item in resolved:
        if item["required"] != "yes" and not include_optional:
            continue
        value = item["value"]
        if not value:
            continue
        cmd = ["vercel", "env", "add", str(item["canonical"]), environment, "--force"]
        completed = subprocess.run(
            cmd,
            input=f"{value}",
            text=True,
            cwd=ROOT_DIR,
            capture_output=True,
            check=False,
        )
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        if completed.returncode != 0:
            return completed.returncode
        applied_any = True
    if not applied_any:
        print("No environment variables were applied because none were available locally.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve local env aliases into canonical Vercel variables for this project."
    )
    parser.add_argument(
        "--environment",
        choices=["production", "preview", "development"],
        default="production",
        help="Target Vercel environment (default: production).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually upload any locally available values to Vercel.",
    )
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="When applying, also upload optional channel variables such as Exa and Bright Data.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code when required Vercel variables are missing locally.",
    )
    args = parser.parse_args()

    local_values = collect_local_values()
    resolved = resolve_values(local_values)
    print(render_plan(resolved, args.environment))
    sys.stdout.flush()

    if args.strict and validate_required_items(resolved) != 0:
        return 1

    if not args.apply:
        return 0

    return apply_env(args.environment, resolved, include_optional=args.include_optional)


if __name__ == "__main__":
    raise SystemExit(main())
