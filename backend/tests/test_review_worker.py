import json
from pathlib import Path

from app.services.review_worker import ReviewWorker


def test_review_worker_writes_input_and_reads_review_json(tmp_path: Path):
    fake_codex = tmp_path / "fake_codex.py"
    fake_codex.write_text(
        """
import json
import sys
from pathlib import Path

workspace = Path(sys.argv[-1])
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

