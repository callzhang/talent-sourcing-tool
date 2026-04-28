from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


REQUIRED_REVIEW_FIELDS = {
    "candidate_id",
    "job_id",
    "overall_score",
    "recommendation",
    "decision_summary",
}


REVIEW_PROMPT = """You are running a file-protocol candidate review in this workspace.
Read input.json for the review job, candidate, job, and rubric payload.
Follow review.schema.json exactly for the output contract.
Then write review.json in this current workspace as a single JSON object.
Do not write directly to any database or modify files other than review.json."""


class ReviewOutput(BaseModel):
    candidate_id: str
    job_id: str
    overall_score: float
    recommendation: Literal["strong_proceed", "proceed", "borderline", "pass"]
    decision_summary: str
    dimension_scores: list[Any] = Field(default_factory=list)
    strengths: list[Any] = Field(default_factory=list)
    risks: list[Any] = Field(default_factory=list)
    evidence: list[Any] = Field(default_factory=list)
    sources: list[Any] = Field(default_factory=list)
    suggested_interview_questions: list[Any] = Field(default_factory=list)
    uncertainties: list[Any] = Field(default_factory=list)
    review_notes: str = ""


@dataclass(frozen=True)
class ReviewWorkerResult:
    workspace: Path
    input_path: Path
    output_path: Path
    review: dict[str, Any]


class ReviewWorker:
    def __init__(self, codex_command: list[str], workspace_root: str | Path) -> None:
        self.codex_command = codex_command
        self.workspace_root = Path(workspace_root)

    def run_review(self, review_job_id: str, payload: dict[str, Any]) -> ReviewWorkerResult:
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        workspace = Path(tempfile.mkdtemp(prefix=f"{review_job_id}-", dir=self.workspace_root))
        temp_home = Path(tempfile.mkdtemp(prefix=f"{review_job_id}-home-", dir=self.workspace_root))
        temp_codex_home = Path(
            tempfile.mkdtemp(prefix=f"{review_job_id}-codex-home-", dir=self.workspace_root)
        )
        input_path = workspace / "input.json"
        output_path = workspace / "review.json"

        review_input = {"review_job_id": review_job_id, **payload}
        input_path.write_text(json.dumps(review_input, indent=2, sort_keys=True))
        (workspace / "review.schema.json").write_text(
            json.dumps(
                {
                    "type": "object",
                    "required": sorted(REQUIRED_REVIEW_FIELDS),
                    "properties": {
                        "candidate_id": {"type": "string"},
                        "job_id": {"type": "string"},
                        "overall_score": {"type": "number"},
                        "recommendation": {
                            "type": "string",
                            "enum": ["strong_proceed", "proceed", "borderline", "pass"],
                        },
                        "decision_summary": {"type": "string"},
                        "dimension_scores": {"type": "array"},
                        "strengths": {"type": "array"},
                        "risks": {"type": "array"},
                        "evidence": {"type": "array"},
                        "sources": {"type": "array"},
                        "suggested_interview_questions": {"type": "array"},
                        "uncertainties": {"type": "array"},
                        "review_notes": {"type": "string"},
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )

        env = {**os.environ, "HOME": str(temp_home), "CODEX_HOME": str(temp_codex_home)}
        completed = subprocess.run(
            self._review_command(workspace),
            cwd=workspace,
            env=env,
            timeout=600,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Review worker command failed "
                f"with exit code {completed.returncode}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        if not output_path.exists():
            raise RuntimeError(f"Review worker did not create {output_path}")

        review = json.loads(output_path.read_text())
        missing_fields = sorted(REQUIRED_REVIEW_FIELDS.difference(review))
        if missing_fields:
            raise RuntimeError(f"Review output missing required fields: {', '.join(missing_fields)}")
        try:
            validated_review = ReviewOutput.model_validate(review)
        except ValidationError as exc:
            raise RuntimeError(f"Invalid review output: {exc}") from exc

        return ReviewWorkerResult(
            workspace=workspace,
            input_path=input_path,
            output_path=output_path,
            review=validated_review.model_dump(),
        )

    def _review_command(self, workspace: Path) -> list[str]:
        command = [*self.codex_command]
        if self._is_codex_exec_command(command):
            command.extend(
                [
                    "--cd",
                    str(workspace),
                    "--skip-git-repo-check",
                    "--ephemeral",
                    "--ignore-user-config",
                    "--ignore-rules",
                ]
            )
        command.append(REVIEW_PROMPT)
        return command

    @staticmethod
    def _is_codex_exec_command(command: list[str]) -> bool:
        return len(command) >= 2 and Path(command[0]).name == "codex" and command[1] == "exec"
