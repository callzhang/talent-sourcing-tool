from __future__ import annotations

import importlib.util
from io import BytesIO
from pathlib import Path
import subprocess
from urllib.error import HTTPError


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_script_module(name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_runs_live_hr_e2e_only_through_a_job_environment_variable():
    workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text()

    assert "if: ${{ secrets.TALENT_OPENAI_API_KEY != '' }}" not in workflow
    assert "TALENT_OPENAI_API_KEY: ${{ secrets.TALENT_OPENAI_API_KEY }}" in workflow
    assert "if: ${{ env.TALENT_OPENAI_API_KEY != '' }}" in workflow
    assert "if: ${{ env.TALENT_OPENAI_API_KEY == '' }}" in workflow


def test_prepare_vercel_env_resolves_aliases_and_renders_plan():
    module = load_script_module("prepare_vercel_env", "scripts/prepare_vercel_env.py")

    resolved = module.resolve_values(
        {
            "REVIEW_PROVIDER": "openai",
            "TALENT_REVIEW_MODEL": "gpt-4.1-mini",
            "EXA_API_KEY": "exa-key",
            "BRIGHTDATA_API_KEY": "bright-key",
            "TALENT_BRIGHTDATA_ZONE": "discover_zone",
        }
    )

    assert resolved[:1] == [
        {
            "canonical": "TALENT_DATABASE_URL",
            "description": "Durable production database URL",
            "required": "yes",
            "source_key": None,
            "value": None,
        }
    ]
    assert resolved[1:3] == [
        {
            "canonical": "TURSO_DATABASE_URL",
            "description": "Turso durable database URL",
            "required": "no",
            "source_key": None,
            "value": None,
        },
        {
            "canonical": "TURSO_AUTH_TOKEN",
            "description": "Turso database authentication token",
            "required": "no",
            "source_key": None,
            "value": None,
        },
    ]
    assert resolved[3:] == [
        {
            "canonical": "TALENT_OPENAI_API_KEY",
            "description": "OpenAI key for production AI review",
            "required": "yes",
            "source_key": None,
            "value": None,
        },
        {
            "canonical": "TALENT_REVIEW_PROVIDER",
            "description": "Optional explicit review provider override",
            "required": "no",
            "source_key": "REVIEW_PROVIDER",
            "value": "openai",
        },
        {
            "canonical": "TALENT_REVIEW_MODEL",
            "description": "Optional explicit review model override",
            "required": "no",
            "source_key": "TALENT_REVIEW_MODEL",
            "value": "gpt-4.1-mini",
        },
        {
            "canonical": "TALENT_EXA_API_KEY",
            "description": "Exa key for production sourcing",
            "required": "no",
            "source_key": "EXA_API_KEY",
            "value": "exa-key",
        },
        {
            "canonical": "TALENT_BRIGHTDATA_API_KEY",
            "description": "Bright Data API key for production sourcing",
            "required": "no",
            "source_key": "BRIGHTDATA_API_KEY",
            "value": "bright-key",
        },
        {
            "canonical": "TALENT_BRIGHTDATA_ZONE",
            "description": "Bright Data zone name for production sourcing",
            "required": "no",
            "source_key": "TALENT_BRIGHTDATA_ZONE",
            "value": "discover_zone",
        },
    ]

    plan = module.render_plan(resolved, "production")
    assert "Target environment: production" in plan
    assert "Required for readiness:" in plan
    assert "Optional channel coverage:" in plan
    assert "- TALENT_REVIEW_PROVIDER: ready via REVIEW_PROVIDER" in plan
    assert "- TALENT_REVIEW_MODEL: ready" in plan
    assert "- TALENT_EXA_API_KEY: ready via EXA_API_KEY" in plan
    assert "- TALENT_BRIGHTDATA_API_KEY: ready via BRIGHTDATA_API_KEY" in plan
    assert "- TALENT_DATABASE_URL: missing locally" in plan


def test_prepare_vercel_env_accepts_turso_as_durable_storage():
    module = load_script_module("prepare_vercel_env_turso", "scripts/prepare_vercel_env.py")

    resolved = module.resolve_values(
        {
            "TURSO_DATABASE_URL": "libsql://example.turso.io",
            "TURSO_AUTH_TOKEN": "test-token",
            "TALENT_OPENAI_API_KEY": "sk-test",
        }
    )

    assert module.missing_required_items(resolved) == []
    assert "TALENT_DATABASE_URL: ready via TURSO_DATABASE_URL + TURSO_AUTH_TOKEN" in module.render_plan(
        resolved, "production"
    )


def test_prepare_vercel_env_reports_missing_required_items():
    module = load_script_module("prepare_vercel_env_missing_required", "scripts/prepare_vercel_env.py")

    missing = module.missing_required_items(
        [
            {"canonical": "TALENT_DATABASE_URL", "required": "yes", "value": None},
            {"canonical": "TALENT_OPENAI_API_KEY", "required": "yes", "value": "sk-test"},
            {"canonical": "TALENT_EXA_API_KEY", "required": "no", "value": None},
        ]
    )

    assert missing == ["TALENT_DATABASE_URL"]


def test_prepare_vercel_env_apply_fails_without_vercel_cli(monkeypatch, capsys):
    module = load_script_module("prepare_vercel_env_missing_cli", "scripts/prepare_vercel_env.py")

    monkeypatch.setattr(module.shutil, "which", lambda name: None)

    exit_code = module.apply_env(
        "production",
        [
            {
                "canonical": "TALENT_DATABASE_URL",
                "required": "yes",
                "value": "postgres://example",
            }
        ],
        include_optional=False,
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Missing `vercel` CLI in PATH" in captured.err


def test_prepare_vercel_env_validate_required_items_reports_missing(capsys):
    module = load_script_module("prepare_vercel_env_validate_required", "scripts/prepare_vercel_env.py")

    exit_code = module.validate_required_items(
        [
            {"canonical": "TALENT_DATABASE_URL", "required": "yes", "value": None},
            {"canonical": "TALENT_OPENAI_API_KEY", "required": "yes", "value": "sk-test"},
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Required variables are still missing locally: TALENT_DATABASE_URL" in captured.err


def test_prepare_vercel_env_apply_refuses_partial_apply_when_required_vars_still_missing(
    monkeypatch, capsys
):
    module = load_script_module("prepare_vercel_env_apply_partial", "scripts/prepare_vercel_env.py")

    monkeypatch.setattr(module.shutil, "which", lambda name: "/opt/homebrew/bin/vercel")

    calls: list[tuple[list[str], str | None]] = []

    def fake_run(cmd, input=None, text=None, cwd=None, capture_output=None, check=None):  # noqa: ANN001, ANN202
        calls.append((cmd, input))
        return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    exit_code = module.apply_env(
        "production",
        [
            {
                "canonical": "TALENT_DATABASE_URL",
                "required": "yes",
                "value": "postgres://example",
            },
            {
                "canonical": "TALENT_OPENAI_API_KEY",
                "required": "yes",
                "value": None,
            },
        ],
        include_optional=False,
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert calls == []
    assert "Required variables are still missing locally: TALENT_OPENAI_API_KEY" in captured.err
    assert "Refusing to apply a partial Vercel environment." in captured.err


def test_prepare_vercel_env_main_strict_returns_nonzero_when_required_missing(monkeypatch, capsys):
    module = load_script_module("prepare_vercel_env_main_strict", "scripts/prepare_vercel_env.py")

    monkeypatch.setattr(
        module,
        "collect_local_values",
        lambda: {"EXA_API_KEY": "exa-key"},
    )
    monkeypatch.setattr(module.sys, "argv", ["prepare_vercel_env.py", "--strict"])

    exit_code = module.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Target environment: production" in captured.out
    assert "Required variables are still missing locally:" in captured.err


def test_port_utils_returns_preferred_port_when_available():
    module = load_script_module("port_utils_preferred", "scripts/port_utils.py")

    port = module.find_available_port(19173)

    assert port == 19173


def test_port_utils_skips_occupied_port():
    module = load_script_module("port_utils_occupied", "scripts/port_utils.py")

    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 19174))
        sock.listen(1)

        port = module.find_available_port(19174)

    assert port == 19175


def test_check_deploy_hygiene_reports_ignored_suspicious_artifacts(tmp_path):
    module = load_script_module("check_deploy_hygiene_ok", "scripts/check_deploy_hygiene.py")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".vercelignore").write_text("**/__pycache__/\n**/*.pyc\n**/* 2.py\n")
    (repo_root / "backend" / "app" / "__pycache__").mkdir(parents=True)
    (repo_root / "backend" / "app" / "__pycache__" / "main.cpython-312.pyc").write_text("x")
    (repo_root / "backend" / "app" / "main 2.py").write_text("x")

    patterns = module.load_vercelignore_patterns(repo_root / ".vercelignore")
    findings = module.collect_suspicious_paths(repo_root)
    report, uncovered = module.render_report(findings, patterns, repo_root=repo_root)

    assert report == "All suspicious deploy artifacts are covered by .vercelignore. Covered artifacts: 3"
    assert uncovered is False


def test_check_deploy_hygiene_fails_when_suspicious_artifact_is_uncovered(tmp_path):
    module = load_script_module("check_deploy_hygiene_fail", "scripts/check_deploy_hygiene.py")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".vercelignore").write_text("**/__pycache__/\n")
    (repo_root / "backend").mkdir()
    (repo_root / "backend" / "main 2.py").write_text("x")

    patterns = module.load_vercelignore_patterns(repo_root / ".vercelignore")
    findings = module.collect_suspicious_paths(repo_root)
    report, uncovered = module.render_report(findings, patterns, repo_root=repo_root)

    assert "Covered suspicious artifacts: 0" in report
    assert "backend/main 2.py: duplicate python file (NOT ignored)" in report
    assert uncovered is True


def test_check_production_readiness_finds_alias_keys_and_renders_missing_sections():
    module = load_script_module(
        "check_production_readiness", "scripts/check_production_readiness.py"
    )

    assert module.find_available_local_key(
        {"BRIGHTDATA_API_KEY": "bright-key"}, "TALENT_BRIGHTDATA_API_KEY"
    ) == (True, "BRIGHTDATA_API_KEY")
    assert module.find_available_local_key({}, "TALENT_OPENAI_API_KEY") == (
        False,
        "TALENT_OPENAI_API_KEY",
    )

    rendered = module.render_missing_vars(
        {
            "capabilities": {
                "missing_env_vars": {
                    "storage": ["DATABASE_URL", "TALENT_DATABASE_URL"],
                    "review": ["TALENT_OPENAI_API_KEY"],
                    "channels": {
                        "brightdata_discover": [
                            "TALENT_BRIGHTDATA_API_KEY",
                            "TALENT_BRIGHTDATA_ZONE",
                        ]
                    },
                }
            }
        },
        {"BRIGHTDATA_API_KEY": "bright-key"},
    )
    assert "[storage]" in rendered
    assert "- TALENT_OPENAI_API_KEY: not found locally" in rendered
    assert (
        "- TALENT_BRIGHTDATA_API_KEY: available locally via BRIGHTDATA_API_KEY"
        in rendered
    )
    assert (
        module.provider_checks_url_for_status("https://example.com/api/system/status")
        == "https://example.com/api/system/provider-checks"
    )


def test_check_production_readiness_renders_structured_blockers_and_degradations():
    module = load_script_module(
        "check_production_readiness_structured_status",
        "scripts/check_production_readiness.py",
    )

    blockers = module.render_status_items(
        "hard_blockers",
        [
            {
                "code": "durable_storage_missing",
                "message": "Configure DATABASE_URL for durable state.",
                "env_vars": ["DATABASE_URL", "TALENT_DATABASE_URL"],
            }
        ],
        {"TALENT_DATABASE_URL": "postgres://example"},
    )
    degradations = module.render_status_items(
        "optional_degradations",
        [
            {
                "code": "optional_channel_unavailable",
                "message": "Optional production channel unavailable: Bright Data Discover.",
                "channels": ["brightdata_discover"],
                "env_vars": ["TALENT_BRIGHTDATA_API_KEY"],
            }
        ],
        {"BRIGHTDATA_API_KEY": "bright-key"},
    )

    assert "hard_blockers:" in blockers
    assert "- durable_storage_missing: Configure DATABASE_URL for durable state." in blockers
    assert "env DATABASE_URL: available locally via TALENT_DATABASE_URL" in blockers
    assert "optional_degradations:" in degradations
    assert "channels=brightdata_discover" in degradations
    assert "env TALENT_BRIGHTDATA_API_KEY: available locally via BRIGHTDATA_API_KEY" in degradations


def test_check_production_readiness_detects_expired_brightdata_key(monkeypatch):
    module = load_script_module(
        "check_production_readiness_expired", "scripts/check_production_readiness.py"
    )

    def fake_urlopen(request, timeout=30):  # noqa: ARG001
        raise HTTPError(
            request.full_url,
            401,
            "Unauthorized",
            hdrs=None,
            fp=BytesIO(b"Token expired"),
        )

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    state, detail = module.validate_brightdata({"BRIGHTDATA_API_KEY": "expired-key"})
    assert state == "expired_key"
    assert detail == []


def test_check_production_readiness_reports_missing_zone_from_active_zones(monkeypatch):
    module = load_script_module(
        "check_production_readiness_zone", "scripts/check_production_readiness.py"
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self):
            return b'[{"name":"discover_zone"},{"name":"serp_zone"}]'

    monkeypatch.setattr(module, "urlopen", lambda request, timeout=30: FakeResponse())

    state, detail = module.validate_brightdata({"BRIGHTDATA_API_KEY": "valid-key"})
    assert state == "missing_zone"
    assert detail == ["discover_zone", "serp_zone"]


def test_check_production_readiness_normalizes_and_renders_live_provider_checks():
    module = load_script_module(
        "check_production_readiness_live_provider",
        "scripts/check_production_readiness.py",
    )

    payload = {
        "providers": {
            "exa": {
                "status": "ok",
                "detail": "Exa API key accepted a search request.",
            },
            "brightdata": {
                "status": "expired_key",
                "detail": "Bright Data API key exists but is expired.",
                "active_zones": ["discover_zone"],
            },
        }
    }

    assert module.normalize_provider_results(payload) == {
        "exa": "ok",
        "brightdata": "expired_key",
    }
    rendered = module.render_provider_checks(payload)
    assert "- exa=ok" in rendered
    assert "detail=Exa API key accepted a search request." in rendered
    assert "- brightdata=expired_key" in rendered
    assert "active_zones=discover_zone" in rendered


def test_check_production_readiness_plans_live_write_guard_probes():
    module = load_script_module(
        "check_production_readiness_write_guards",
        "scripts/check_production_readiness.py",
    )

    probes = module.planned_write_guard_probes(
        {
            "capabilities": {
                "missing_env_vars": {
                    "storage": ["DATABASE_URL"],
                    "review": ["TALENT_OPENAI_API_KEY"],
                }
            }
        },
        "https://example.com/api/system/status",
    )

    assert [probe["name"] for probe in probes] == [
        "create_job",
        "create_search",
        "create_decision",
        "start_review",
    ]
    assert probes[0]["url"] == "https://example.com/api/jobs"
    assert probes[-1]["url"] == "https://example.com/api/reviews/start"


def test_check_production_readiness_executes_and_renders_write_guard_probes(monkeypatch):
    module = load_script_module(
        "check_production_readiness_write_guard_execution",
        "scripts/check_production_readiness.py",
    )

    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(method, url, body=None):  # noqa: ANN001, ANN202
        calls.append((method, url, body))
        return 503, {"detail": "Production write actions are disabled."}

    monkeypatch.setattr(module, "request_json", fake_request_json)

    results = module.execute_write_guard_probes(
        [
            {
                "name": "create_job",
                "method": "POST",
                "url": "https://example.com/api/jobs",
                "body": {"title": "Guard Probe", "description": "Blocked"},
                "expected_status": 503,
            }
        ]
    )

    assert calls == [
        (
            "POST",
            "https://example.com/api/jobs",
            {"title": "Guard Probe", "description": "Blocked"},
        )
    ]
    assert results == [
        {
            "name": "create_job",
            "expected_status": 503,
            "actual_status": 503,
            "ok": True,
            "detail": "Production write actions are disabled.",
        }
    ]
    rendered = module.render_write_guard_results(results)
    assert "- create_job=ok (expected 503, got 503)" in rendered
    assert "detail=Production write actions are disabled." in rendered


def test_check_production_readiness_strict_fails_when_not_ready():
    module = load_script_module(
        "check_production_readiness_strict_not_ready",
        "scripts/check_production_readiness.py",
    )

    exit_code = module.evaluate_exit_code(
        {"deployment_ready": False},
        strict=True,
        provider_results={},
    )

    assert exit_code == 1


def test_check_production_readiness_strict_fails_when_provider_is_not_ok():
    module = load_script_module(
        "check_production_readiness_strict_provider",
        "scripts/check_production_readiness.py",
    )

    exit_code = module.evaluate_exit_code(
        {"deployment_ready": True, "capabilities": {"required_provider_checks": ["exa"]}},
        strict=True,
        provider_results={"exa": "http_401", "brightdata": "expired_key"},
    )

    assert exit_code == 1


def test_check_production_readiness_strict_passes_when_ready_and_required_providers_ok():
    module = load_script_module(
        "check_production_readiness_strict_ok", "scripts/check_production_readiness.py"
    )

    exit_code = module.evaluate_exit_code(
        {"deployment_ready": True, "capabilities": {"required_provider_checks": ["exa"]}},
        strict=True,
        provider_results={"exa": "ok", "brightdata": "expired_key"},
    )

    assert exit_code == 0
