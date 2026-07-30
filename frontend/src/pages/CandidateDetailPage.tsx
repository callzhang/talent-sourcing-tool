import { FormEvent, useEffect, useRef, useState } from "react";

import { api } from "../api";
import type {
  Candidate,
  DraftPassReason,
  ReviewJob,
  ReviewPayload,
  ReviewRead,
  SystemStatus
} from "../types";

type CandidateDetailPageProps = {
  selectedJobId: string | null;
  candidate: Candidate | null;
  systemStatus?: SystemStatus | null;
  onBack: () => void;
};

type ReviewContext = {
  reviewId: string;
  jobId: string;
  candidateId: string;
};

type ReviewStageKey = "idle" | "pending" | "running" | "completed" | "failed";

export function CandidateDetailPage({
  selectedJobId,
  candidate,
  systemStatus = null,
  onBack
}: CandidateDetailPageProps) {
  const [loadedCandidate, setLoadedCandidate] = useState<Candidate | null>(candidate);
  const [reviewContext, setReviewContext] = useState<ReviewContext | null>(null);
  const [reviewJobId, setReviewJobId] = useState<string | null>(null);
  const [reviewJobStatus, setReviewJobStatus] = useState<ReviewStageKey>("idle");
  const [review, setReview] = useState<ReviewPayload | null>(null);
  const [draft, setDraft] = useState<DraftPassReason | null>(null);
  const [notes, setNotes] = useState("");
  const [passReason, setPassReason] = useState("");
  const [status, setStatus] = useState("已准备好进行 AI 评审。");
  const [isWorking, setIsWorking] = useState(false);
  const currentContextRef = useRef({
    selectedJobId,
    candidateId: candidate?.id ?? null,
    loadedCandidateId: loadedCandidate?.id ?? null,
    reviewContext
  });
  currentContextRef.current = {
    selectedJobId,
    candidateId: candidate?.id ?? null,
    loadedCandidateId: loadedCandidate?.id ?? null,
    reviewContext
  };
  const reviewId = reviewContext?.reviewId ?? null;
  const reviewConfigured = systemStatus?.capabilities.review_configured ?? true;
  const reviewStage = currentReviewStage({
    reviewConfigured,
    reviewJobId,
    reviewJobStatus,
    review,
    reviewContext
  });
  const decisionLocked = reviewStage.key === "running" || reviewStage.key === "pending";
  const reviewReadyForDecision = reviewStage.key === "completed";

  useEffect(() => {
    setLoadedCandidate(null);
    setReviewContext(null);
    setReviewJobId(null);
    setReviewJobStatus("idle");
    setReview(null);
    setDraft(null);
    setNotes("");
    setPassReason("");
    setIsWorking(false);

    if (!candidate || !selectedJobId) {
      setStatus("已准备好进行 AI 评审。");
      return;
    }

    let ignore = false;
    setStatus("正在加载候选人评审信息...");
    api
      .getCandidate(candidate.id, selectedJobId)
      .then((freshCandidate) => {
        if (!ignore) {
          setLoadedCandidate(freshCandidate);
        }
      })
      .catch(() => undefined);
    api
      .getLatestReview(selectedJobId, candidate.id)
      .then(async (latestReview: ReviewRead | null) => {
        if (!ignore && latestReview) {
          setReviewJobId(latestReview.review_job_id);
          setReviewJobStatus("completed");
          setReviewContext({
            reviewId: latestReview.id,
            jobId: latestReview.job_id,
            candidateId: latestReview.candidate_id
          });
          setReview(latestReview.review);
          setStatus("已加载最近一次评审。");
          return;
        }
        const latestReviewJob = await api.getLatestReviewJob(selectedJobId, candidate.id);
        if (!ignore && isReviewJob(latestReviewJob)) {
          hydrateRecoveredReviewJob(latestReviewJob);
        } else if (!ignore) {
          setStatus(
            reviewConfigured
              ? "已准备好进行 AI 评审。"
              : "当前部署尚未完成生产评审配置，暂时无法使用 AI 评审。"
          );
        }
      })
      .catch(() => undefined);
    return () => {
      ignore = true;
    };
  }, [candidate, reviewConfigured, selectedJobId]);

  useEffect(() => {
    if (!reviewJobId || reviewContext?.reviewId) {
      return;
    }
    const activeReviewJobId = reviewJobId;

    let ignore = false;
    let timeoutId: number | undefined;

    async function pollReviewJob() {
      try {
        const reviewJob = await api.runReviewJob(activeReviewJobId);
        if (ignore) {
          return;
        }
        applyReviewJob(reviewJob);
        if (reviewJob.status === "running" || reviewJob.status === "pending") {
          timeoutId = window.setTimeout(pollReviewJob, 2000);
        }
      } catch (error) {
        if (!ignore && isCurrentCandidateContext(selectedJobId ?? "", candidate?.id ?? "")) {
          setStatus(error instanceof Error ? error.message : "无法刷新评审任务。");
        }
      }
    }

    void pollReviewJob();

    return () => {
      ignore = true;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [candidate?.id, reviewContext?.reviewId, reviewJobId, selectedJobId]);

  const isCandidateContextReady =
    selectedJobId !== null &&
    candidate !== null &&
    loadedCandidate !== null &&
    loadedCandidate.id === candidate.id;

  function isCurrentCandidateContext(jobId: string, candidateId: string) {
    const currentContext = currentContextRef.current;
    return (
      currentContext.selectedJobId === jobId &&
      currentContext.candidateId === candidateId &&
      currentContext.loadedCandidateId === candidateId
    );
  }

  function isCurrentReviewContext(jobId: string, candidateId: string, activeReviewId: string) {
    const currentReviewContext = currentContextRef.current.reviewContext;
    return (
      isCurrentCandidateContext(jobId, candidateId) &&
      currentReviewContext?.jobId === jobId &&
      currentReviewContext.candidateId === candidateId &&
      currentReviewContext.reviewId === activeReviewId
    );
  }

  if (!selectedJobId || !candidate) {
    return (
      <section className="card">
        <button type="button" className="text-action" onClick={onBack}>
          返回候选人
        </button>
        <h2>候选人评审</h2>
        <p className="empty-state">请选择已搜索到的候选人进行评审。</p>
      </section>
    );
  }

  if (!isCandidateContextReady) {
    return (
      <section className="card">
        <button type="button" className="text-action" onClick={onBack}>
          返回候选人
        </button>
        <h2>候选人评审</h2>
        <p className="empty-state">正在加载候选人评审信息...</p>
      </section>
    );
  }

  async function startReview() {
    /* c8 ignore next 3 -- UI renders the action only after selected job and candidate are loaded. */
    if (!selectedJobId || !loadedCandidate) {
      return;
    }
    const requestedJobId = selectedJobId;
    const requestedCandidateId = loadedCandidate.id;
    setIsWorking(true);
    setReviewJobStatus("running");
    setStatus("正在进行 AI 评审...");
    try {
      const result = await api.startReview({
        job_id: requestedJobId,
        candidate_id: requestedCandidateId
      });
      if (!isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        return;
      }
      setReviewJobId(result.review_job_id);
      setDraft(null);
      if (result.review_id && result.review) {
        setReviewJobStatus("completed");
        setReviewContext({
          reviewId: result.review_id,
          jobId: requestedJobId,
          candidateId: requestedCandidateId
        });
        setReview(result.review);
        setStatus("AI 评审已完成。");
      } else {
        setReviewJobStatus(normalizeReviewStage(result.status));
        setReviewContext(null);
        setReview(null);
        setStatus(reviewStatusMessage(result.status));
      }
    } catch (error) {
      if (isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        setReviewJobStatus(reviewContext && review ? "completed" : "failed");
        setStatus(error instanceof Error ? error.message : "无法启动评审。");
      }
    } finally {
      if (isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        setIsWorking(false);
      }
    }
  }

  async function draftPassReason() {
    /* c8 ignore next 4 -- The draft button is disabled until a review context exists. */
    if (!reviewContext) {
      setStatus("请先完成评审，再生成淘汰原因草稿。");
      return;
    }
    const requestedReviewContext = reviewContext;
    setIsWorking(true);
    setStatus("正在生成淘汰原因草稿...");
    try {
      const generatedDraft = await api.getDraftPassReason(requestedReviewContext.reviewId);
      if (
        !isCurrentReviewContext(
          requestedReviewContext.jobId,
          requestedReviewContext.candidateId,
          requestedReviewContext.reviewId
        )
      ) {
        return;
      }
      setDraft(generatedDraft);
      setPassReason(generatedDraft.reason_text);
      setStatus("淘汰原因草稿已生成。");
    } catch (error) {
      if (
        isCurrentReviewContext(
          requestedReviewContext.jobId,
          requestedReviewContext.candidateId,
          requestedReviewContext.reviewId
        )
      ) {
        setStatus(error instanceof Error ? error.message : "无法生成淘汰原因草稿。");
      }
    } finally {
      if (
        isCurrentReviewContext(
          requestedReviewContext.jobId,
          requestedReviewContext.candidateId,
          requestedReviewContext.reviewId
        )
      ) {
        setIsWorking(false);
      }
    }
  }

  async function submitDecision(decision: "pass" | "proceed") {
    /* c8 ignore next 3 -- Decision controls render only after candidate context is loaded. */
    if (!selectedJobId || !loadedCandidate) {
      return;
    }
    const requestedJobId = selectedJobId;
    const requestedCandidateId = loadedCandidate.id;
    const requestedReviewContext = reviewContext;
    const requestedDraft = draft;
    if (decision === "pass" && passReason.trim().length === 0) {
      setStatus("淘汰决定必须填写原因。");
      return;
    }
    if (
      !isCurrentCandidateContext(requestedJobId, requestedCandidateId) ||
      (requestedReviewContext !== null &&
        !isCurrentReviewContext(
          requestedReviewContext.jobId,
          requestedReviewContext.candidateId,
          requestedReviewContext.reviewId
        ))
    ) {
      /* c8 ignore next 2 -- This protects against stale event closures that are not user-reachable. */
      return;
    }
    setIsWorking(true);
    setStatus(`正在保存${decision === "pass" ? "淘汰" : "推进"}决定...`);
    try {
      await api.createDecision({
        job_id: requestedJobId,
        candidate_id: requestedCandidateId,
        review_id: requestedReviewContext?.reviewId,
        decision,
        notes,
        pass_reason_code: requestedDraft?.reason_code ?? "manual_pass",
        pass_reason_text: decision === "pass" ? passReason : undefined
      });
      if (isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        setStatus(`已保存${decision === "pass" ? "淘汰" : "推进"}决定。`);
      }
    } catch (error) {
      if (isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        setStatus(error instanceof Error ? error.message : "无法保存决定。");
      }
    } finally {
      if (isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        setIsWorking(false);
      }
    }
  }

  function handleProceed(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitDecision("proceed");
  }

  function applyReviewJob(activeReviewJob: ReviewJob) {
    if (!isCurrentCandidateContext(activeReviewJob.job_id, activeReviewJob.candidate_id)) {
      return;
    }
    hydrateRecoveredReviewJob(activeReviewJob);
  }

  function hydrateRecoveredReviewJob(activeReviewJob: ReviewJob) {
    setReviewJobId(activeReviewJob.id);
    setReviewJobStatus(normalizeReviewStage(activeReviewJob.status));
    if (activeReviewJob.review_id && activeReviewJob.review) {
      setReviewContext({
        reviewId: activeReviewJob.review_id,
        jobId: activeReviewJob.job_id,
        candidateId: activeReviewJob.candidate_id
      });
      setReview(activeReviewJob.review);
    }
    if (activeReviewJob.status === "failed") {
      setStatus(activeReviewJob.error_message ?? "AI 评审失败。");
      return;
    }
    setStatus(reviewStatusMessage(activeReviewJob.status));
  }

  return (
    <section className="workspace-grid detail-grid" aria-labelledby="candidate-detail-heading">
      <div className="card">
        <button type="button" className="text-action" onClick={onBack}>
          返回候选人
        </button>
        <p className="section-kicker">候选人详情</p>
        <h2 id="candidate-detail-heading">{loadedCandidate.name}</h2>
        <p>{loadedCandidate.headline ?? "未获取简介"}</p>
        <p className="muted">
          {[loadedCandidate.current_company, loadedCandidate.location].filter(Boolean).join(" · ")}
        </p>
        <a href={loadedCandidate.profile_url} target="_blank" rel="noreferrer">
          打开 {profileSourceLabel(loadedCandidate.profile_source)} 资料
        </a>
        <div className="review-status-panel" aria-label="评审状态">
          <div className="split-heading">
            <span className={`status-pill status-pill-${reviewStage.tone}`}>{reviewStage.label}</span>
            {reviewJobId ? <code>{reviewJobId.slice(0, 16)}</code> : null}
          </div>
          <p className="muted review-status-copy">{reviewStage.description}</p>
        </div>
        <button
          type="button"
          className="primary-action"
          onClick={startReview}
          disabled={isWorking || !reviewConfigured || decisionLocked}
        >
          开始 AI 评审
        </button>
        <p className="muted">{status}</p>
      </div>

      <div className="card">
        <p className="section-kicker">AI 评审</p>
        <ReviewBlock review={review} />
        <button
          type="button"
          className="secondary-action"
          onClick={draftPassReason}
          disabled={isWorking || reviewId === null || !reviewReadyForDecision}
        >
          生成淘汰原因草稿
        </button>
        {draft ? <EvidenceList evidence={draft.evidence} /> : null}
      </div>

      <form className="card stack" onSubmit={handleProceed}>
        <p className="section-kicker">人工决定</p>
        <label>
          决定备注与反馈
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} />
        </label>
        <label>
          淘汰原因
          <textarea
            value={passReason}
            onChange={(event) => setPassReason(event.target.value)}
            rows={4}
          />
        </label>
        <div className="action-row">
          <button
            type="button"
            className="danger-action"
            disabled={isWorking || !reviewReadyForDecision}
            onClick={() => void submitDecision("pass")}
          >
            确认淘汰
          </button>
          <button type="submit" className="primary-action" disabled={isWorking || !reviewReadyForDecision}>
            确认推进
          </button>
        </div>
      </form>
    </section>
  );
}

function reviewStatusMessage(status: string): string {
  if (status === "completed") {
    return "AI 评审已完成。";
  }
  if (status === "failed") {
    return "AI 评审失败。";
  }
  if (status === "running") {
    return "AI 评审进行中...";
  }
  if (status === "pending") {
    return "AI 评审排队中...";
  }
  return `AI 评审状态：${status}`;
}

function currentReviewStage({
  reviewConfigured,
  reviewJobId,
  reviewJobStatus,
  review,
  reviewContext,
}: {
  reviewConfigured: boolean;
  reviewJobId: string | null;
  reviewJobStatus: ReviewStageKey;
  review: ReviewPayload | null;
  reviewContext: ReviewContext | null;
}): { key: "disabled" | "idle" | "pending" | "running" | "completed" | "failed"; label: string; description: string; tone: "neutral" | "warning" | "success" | "error" } {
  if (!reviewConfigured) {
    return {
      key: "disabled",
      label: "暂不可用",
      description: "当前生产环境的 AI 评审配置尚未完成。",
      tone: "warning"
    };
  }
  if (reviewJobStatus === "failed") {
    return {
      key: "failed",
      label: "失败",
      description: "最近一次评审失败，请查看下方错误信息。",
      tone: "error"
    };
  }
  if (reviewJobStatus === "pending") {
    return {
      key: "pending",
      label: "排队中",
      description: "评审任务已创建，正在等待开始。",
      tone: "warning"
    };
  }
  if (reviewJobStatus === "running") {
    return {
      key: "running",
      label: "进行中",
      description: "AI 正在评审，完成前无法提交人工决定。",
      tone: "warning"
    };
  }
  if (reviewJobStatus === "completed" && reviewJobId && reviewContext && review) {
    return {
      key: "completed",
      label: "已完成",
      description: "结构化 AI 评审已生成，可进行人工决定。",
      tone: "success"
    };
  }
  return {
    key: "idle",
    label: "待评审",
    description: "该候选人当前没有进行中的 AI 评审。",
    tone: "neutral"
  };
}

function normalizeReviewStage(status: string): ReviewStageKey {
  if (status === "completed") {
    return "completed";
  }
  if (status === "failed") {
    return "failed";
  }
  if (status === "running") {
    return "running";
  }
  if (status === "pending") {
    return "pending";
  }
  return "idle";
}

function isReviewJob(value: unknown): value is ReviewJob {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidateReviewJob = value as Partial<ReviewJob>;
  return (
    typeof candidateReviewJob.id === "string" &&
    typeof candidateReviewJob.job_id === "string" &&
    typeof candidateReviewJob.candidate_id === "string" &&
    typeof candidateReviewJob.status === "string"
  );
}

function profileSourceLabel(value: string): string {
  return (
    {
      linkedin: "LinkedIn",
      github: "GitHub",
      openreview: "OpenReview",
      arxiv: "arXiv",
      exa: "Exa",
      brightdata_discover: "Bright Data Discover"
    }[value] ?? "候选人"
  );
}

function ReviewBlock({ review }: { review: ReviewPayload | null }) {
  if (!review) {
    return <p className="empty-state">开始 AI 评审后，可查看评分、建议和证据。</p>;
  }
  return (
    <div className="review-block">
      <div className="score-badge">{review.overall_score ?? "暂无评分"}</div>
      <h3>{recommendationLabel(review.recommendation)}</h3>
      <p>{review.decision_summary ?? "未返回评审摘要。"}</p>
      <div className="evidence-grid">
        {(review.evidence ?? []).map((item, index) => (
          <article key={`${String(item.label ?? "evidence")}-${index}`} className="evidence-card">
            <strong>{String(item.label ?? `证据 ${index + 1}`)}</strong>
            <span>{String(item.detail ?? item.url ?? "无详情")}</span>
          </article>
        ))}
      </div>
    </div>
  );
}

function recommendationLabel(recommendation: string | null | undefined): string {
  return (
    {
      strong_proceed: "强烈建议推进",
      proceed: "建议推进",
      borderline: "边界匹配",
      pass: "不建议推进"
    }[recommendation ?? ""] ?? "暂无建议"
  );
}

function EvidenceList({ evidence }: { evidence: string[] }) {
  return (
    <ul className="compact-list">
      {evidence.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}
