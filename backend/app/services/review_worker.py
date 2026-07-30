from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings, settings


REQUIRED_REVIEW_FIELDS = {
    "candidate_id",
    "job_id",
    "overall_score",
    "recommendation",
    "decision_summary",
}


REVIEW_PROMPT = """你正在此工作区执行候选人评审。
从 input.json 读取评审任务、候选人、岗位和评分标准。
严格遵循 review.schema.json 的输出合同。
使用 profile_data.raw.signals、profile_data.raw.risks 和公开资料字段作为证据。
strong_proceed 评为 85-100 分，proceed 为 70-84 分，borderline 为 55-69 分，低于 55 分为 pass。
对只做 GTM、只做平台、咨询经历过重或缺少亲自完成 AI 原型证据的候选人降分。
每个分数低于 70 的 dimension_scores 项必须使用以下之一填写 reason_code：
weak_builder_evidence, insufficient_ai_native_signal, too_enterprise_sales_oriented,
platform_only_background, solutions_architecture_mismatch, consulting_heavy_profile,
或 insufficient_public_evidence。
所有面向 HR 的文本字段必须使用简体中文；JSON 字段名、recommendation 和 reason_code 保持 schema 中的英文值。
然后在当前工作区写入一个单独 JSON 对象 review.json。
不要直接写数据库，也不要修改 review.json 以外的文件。"""


OPENAI_REVIEW_PROMPT = """你是负责高质量人才搜索流程的资深招聘分析师。
只输出一个严格符合 review.schema.json 的 JSON 对象。
只能使用 input.json 中已有的证据，不得虚构个人经历。
若证据不足或存在歧义，保守评分并说明不确定性。
所有给 HR 阅读的文本字段必须使用简体中文；JSON 字段名、recommendation 和 reason_code 保持 schema 规定的英文值。"""


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
    workspace: Path | None
    input_path: Path | None
    output_path: Path | None
    review: dict[str, Any]


class ReviewRunner(Protocol):
    def run_review(self, review_job_id: str, payload: dict[str, Any]) -> ReviewWorkerResult:
        """Generate a structured candidate review."""


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
        self._copy_codex_auth(temp_codex_home)
        input_path = workspace / "input.json"
        output_path = workspace / "review.json"

        review_input = {"review_job_id": review_job_id, **payload}
        input_path.write_text(json.dumps(review_input, indent=2, sort_keys=True))
        (workspace / "review.schema.json").write_text(
            json.dumps(build_review_schema(), indent=2, sort_keys=True)
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

        validated_review = validate_review_output(json.loads(output_path.read_text()))
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
                    "--sandbox",
                    "workspace-write",
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

    @staticmethod
    def _copy_codex_auth(temp_codex_home: Path) -> None:
        source_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
        source_auth = source_home / "auth.json"
        if source_auth.exists():
            shutil.copy2(source_auth, temp_codex_home / "auth.json")


class OpenAIReviewWorker:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: int,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip():
            raise RuntimeError(
                "openai review provider requires TALENT_OPENAI_API_KEY or OPENAI_API_KEY"
            )
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(
            timeout=float(timeout_seconds),
            follow_redirects=True,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            trust_env=False,
        )

    def run_review(self, review_job_id: str, payload: dict[str, Any]) -> ReviewWorkerResult:
        review_input = {"review_job_id": review_job_id, **payload}
        schema_json = json.dumps(build_review_schema(), indent=2, sort_keys=True)
        input_json = json.dumps(review_input, indent=2, sort_keys=True)
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": OPENAI_REVIEW_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"review.schema.json:\n{schema_json}\n\n"
                            f"input.json:\n{input_json}\n\n"
                            "只返回 JSON 对象。"
                        ),
                    },
                ],
            },
        )
        response.raise_for_status()
        payload_json = response.json()
        content = extract_openai_message_content(payload_json)
        try:
            review = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OpenAI review response was not valid JSON: {content}") from exc

        validated_review = validate_review_output(review)
        return ReviewWorkerResult(
            workspace=None,
            input_path=None,
            output_path=None,
            review=validated_review.model_dump(),
        )


def build_review_schema() -> dict[str, Any]:
    return {
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
    }


def validate_review_output(review: dict[str, Any]) -> ReviewOutput:
    missing_fields = sorted(REQUIRED_REVIEW_FIELDS.difference(review))
    if missing_fields:
        raise RuntimeError(f"Review output missing required fields: {', '.join(missing_fields)}")
    try:
        return ReviewOutput.model_validate(review)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid review output: {exc}") from exc


def extract_openai_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError(f"OpenAI review response did not include choices: {payload}")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RuntimeError(f"OpenAI review response did not include message: {payload}")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text)
        if parts:
            return "".join(parts)
    raise RuntimeError(f"OpenAI review response content was empty: {payload}")


def resolve_review_provider(app_settings: Settings) -> str:
    if app_settings.review_provider != "auto":
        return app_settings.review_provider
    return "openai" if os.environ.get("VERCEL") == "1" else "codex"


def build_review_runner(
    app_settings: Settings | None = None, *, client: httpx.Client | None = None
) -> ReviewRunner:
    resolved_settings = app_settings or settings
    provider = resolve_review_provider(resolved_settings)
    if provider == "codex":
        return ReviewWorker(
            codex_command=[resolved_settings.codex_binary, "exec"],
            workspace_root=resolved_settings.review_workspace_root,
        )
    if provider == "openai":
        return OpenAIReviewWorker(
            api_key=resolved_settings.openai_api_key,
            model=resolved_settings.review_model,
            base_url=resolved_settings.openai_base_url,
            timeout_seconds=resolved_settings.review_timeout_seconds,
            client=client,
        )
    raise RuntimeError(f"Unsupported review provider: {provider}")
