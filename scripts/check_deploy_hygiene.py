from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
VERCELIGNORE_PATH = REPO_ROOT / ".vercelignore"
SUSPICIOUS_PATTERNS = [
    ("directory", "__pycache__", "**/__pycache__/"),
    ("file", ".pyc", "**/*.pyc"),
    ("file", "duplicate python file", "**/* 2.py"),
    ("file", ".DS_Store", ".DS_Store"),
]


def load_vercelignore_patterns(path: Path) -> list[str]:
    patterns: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def collect_suspicious_paths(repo_root: Path) -> list[tuple[str, Path, str]]:
    findings: list[tuple[str, Path, str]] = []
    ignored_roots = {
        ".git",
        ".tmp",
        ".vercel",
        "graphify-out",
        "frontend/node_modules",
        "frontend/playwright-report",
        "frontend/test-results",
        "frontend/coverage",
        "backend/.venv",
        "backend/.pytest_cache",
        "backend/.ruff_cache",
        "backend/.codex-review-runs",
    }

    for path in repo_root.rglob("*"):
        relative = path.relative_to(repo_root).as_posix()
        if any(
            relative == ignored_root or relative.startswith(f"{ignored_root}/")
            for ignored_root in ignored_roots
        ):
            continue
        if path.is_dir() and path.name == "__pycache__":
            findings.append(("directory", path, "__pycache__"))
        elif path.is_file() and path.suffix == ".pyc":
            findings.append(("file", path, ".pyc"))
        elif path.is_file() and path.name.endswith(" 2.py"):
            findings.append(("file", path, "duplicate python file"))
        elif path.is_file() and path.name == ".DS_Store":
            findings.append(("file", path, ".DS_Store"))
    return sorted(findings, key=lambda item: item[1].as_posix())


def is_ignored(relative_path: str, patterns: list[str], *, is_dir: bool) -> bool:
    candidate = relative_path.rstrip("/")
    for raw_pattern in patterns:
        pattern = raw_pattern.rstrip("/")
        path_match = PurePosixPath(candidate).match(pattern)
        if path_match:
            return True
        if is_dir:
            for parent in PurePosixPath(candidate).parents:
                if str(parent) == ".":
                    continue
                if parent.match(pattern):
                    return True
    return False


def render_report(
    findings: list[tuple[str, Path, str]],
    patterns: list[str],
    *,
    repo_root: Path = REPO_ROOT,
) -> tuple[str, bool]:
    lines: list[str] = []
    uncovered = False
    ignored_count = 0
    for path_type, absolute_path, label in findings:
        relative_path = absolute_path.relative_to(repo_root).as_posix()
        ignored = is_ignored(relative_path, patterns, is_dir=path_type == "directory")
        if ignored:
            ignored_count += 1
        else:
            lines.append(f"- {relative_path}: {label} (NOT ignored)")
        uncovered = uncovered or not ignored
    if not findings:
        return "No suspicious deploy artifacts found.", False
    if not lines:
        return (
            "All suspicious deploy artifacts are covered by .vercelignore."
            f" Covered artifacts: {ignored_count}",
            False,
        )
    lines.insert(0, f"Covered suspicious artifacts: {ignored_count}")
    return "\n".join(lines), uncovered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that suspicious local artifacts are excluded from Vercel deployments."
    )
    parser.parse_args(argv)

    patterns = load_vercelignore_patterns(VERCELIGNORE_PATH)
    findings = collect_suspicious_paths(REPO_ROOT)
    report, uncovered = render_report(findings, patterns, repo_root=REPO_ROOT)
    print(report)
    if uncovered:
        print(
            "\nDeployment hygiene check failed: at least one suspicious artifact is not covered by .vercelignore.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
