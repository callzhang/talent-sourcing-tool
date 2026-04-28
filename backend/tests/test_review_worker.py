import json
import os
from pathlib import Path

import pytest

from app.services.review_worker import ReviewWorker


def test_review_worker_writes_input_and_reads_review_json(tmp_path: Path):
    fake_codex = tmp_path / "fake_codex.py"
    fake_codex.write_text(
        """
import json
from pathlib import Path

workspace = Path.cwd()
payload = json.loads((workspace / "input.json").read_text())
(workspace / "review.json").write_text(json.dumps({
    "candidate_id": payload["candidate_id"],
    "job_id": payload["job_id"],
    "overall_score": 8.5,
    "recommendation": "proceed",
    "decision_summary": "Strong match for the role.",
    "review_job_id": payload["review_job_id"],
}))
""".strip()
    )

    worker = ReviewWorker(codex_command=["python", str(fake_codex)], workspace_root=tmp_path)

    result = worker.run_review(
        "review_job_123",
        {"candidate_id": "candidate_123", "job_id": "job_123"},
    )

    assert result.workspace.parent == tmp_path
    assert result.input_path == result.workspace / "input.json"
    assert result.output_path == result.workspace / "review.json"
    assert result.review["overall_score"] == 8.5
    assert result.review["recommendation"] == "proceed"

    saved_input = json.loads(result.input_path.read_text())
    assert saved_input["review_job_id"] == "review_job_123"
    assert saved_input["candidate_id"] == "candidate_123"
    assert saved_input["job_id"] == "job_123"


def test_review_worker_invokes_codex_with_prompt_and_isolated_environment(
    tmp_path: Path,
):
    fake_codex = tmp_path / "codex"
    invocation_path = tmp_path / "invocation.json"
    fake_codex.write_text(
        f"""#!/usr/bin/env python
import json
import os
import sys
from pathlib import Path

cwd = Path.cwd()
payload = json.loads((cwd / "input.json").read_text())
Path({str(invocation_path)!r}).write_text(json.dumps({{
    "argv": sys.argv[1:],
    "cwd": str(cwd),
    "home": os.environ["HOME"],
    "codex_home": os.environ["CODEX_HOME"],
}}))
(cwd / "review.json").write_text(json.dumps({{
    "candidate_id": payload["candidate_id"],
    "job_id": payload["job_id"],
    "overall_score": 8.5,
    "recommendation": "proceed",
    "decision_summary": "Strong match for the role.",
}}))
""".strip()
    )
    fake_codex.chmod(fake_codex.stat().st_mode | 0o111)

    worker = ReviewWorker(codex_command=[str(fake_codex), "exec"], workspace_root=tmp_path)

    result = worker.run_review(
        "review_job_123",
        {"candidate_id": "candidate_123", "job_id": "job_123"},
    )

    invocation = json.loads(invocation_path.read_text())
    assert invocation["cwd"] == str(result.workspace)
    assert invocation["home"].startswith(str(tmp_path))
    assert invocation["codex_home"].startswith(str(tmp_path))
    assert invocation["home"] != os.environ.get("HOME")
    assert invocation["codex_home"] != os.environ.get("CODEX_HOME")
    assert "--cd" in invocation["argv"]
    assert str(result.workspace) in invocation["argv"]
    assert "--ephemeral" in invocation["argv"]
    assert "--ignore-user-config" in invocation["argv"]
    assert "--ignore-rules" in invocation["argv"]
    prompt = invocation["argv"][-1]
    assert "Read input.json" in prompt
    assert "review.schema.json" in prompt
    assert "write review.json" in prompt
    assert prompt != str(result.workspace)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("overall_score", "not-a-number"),
        ("recommendation", "hire_immediately"),
    ],
)
def test_review_worker_rejects_invalid_review_output(
    tmp_path: Path, field: str, value: object
):
    fake_codex = tmp_path / "fake_codex.py"
    review = {
        "candidate_id": "candidate_123",
        "job_id": "job_123",
        "overall_score": 8.5,
        "recommendation": "proceed",
        "decision_summary": "Strong match for the role.",
    }
    review[field] = value
    fake_codex.write_text(
        f"""
import json
from pathlib import Path

workspace = Path.cwd()
(workspace / "review.json").write_text(json.dumps({review!r}))
""".strip()
    )
    worker = ReviewWorker(codex_command=["python", str(fake_codex)], workspace_root=tmp_path)

    with pytest.raises(RuntimeError, match="Invalid review output"):
        worker.run_review(
            "review_job_123",
            {"candidate_id": "candidate_123", "job_id": "job_123"},
        )


def test_review_worker_reports_command_failure(tmp_path: Path):
    fake_codex = tmp_path / "fake_codex.py"
    fake_codex.write_text(
        "import sys\nprint('bad stdout')\nprint('bad stderr', file=sys.stderr)\nsys.exit(3)"
    )
    worker = ReviewWorker(codex_command=["python", str(fake_codex)], workspace_root=tmp_path)

    with pytest.raises(RuntimeError, match="exit code 3"):
        worker.run_review("review_job_123", {"candidate_id": "candidate_123", "job_id": "job_123"})


def test_review_worker_reports_missing_output(tmp_path: Path):
    fake_codex = tmp_path / "fake_codex.py"
    fake_codex.write_text("# intentionally does not write review.json")
    worker = ReviewWorker(codex_command=["python", str(fake_codex)], workspace_root=tmp_path)

    with pytest.raises(RuntimeError, match="did not create"):
        worker.run_review("review_job_123", {"candidate_id": "candidate_123", "job_id": "job_123"})


def test_review_worker_reports_missing_required_fields(tmp_path: Path):
    fake_codex = tmp_path / "fake_codex.py"
    fake_codex.write_text(
        """
from pathlib import Path
Path("review.json").write_text("{}")
""".strip()
    )
    worker = ReviewWorker(codex_command=["python", str(fake_codex)], workspace_root=tmp_path)

    with pytest.raises(RuntimeError, match="missing required fields"):
        worker.run_review("review_job_123", {"candidate_id": "candidate_123", "job_id": "job_123"})
