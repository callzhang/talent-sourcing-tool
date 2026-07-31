import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import type { Candidate, Job, SystemStatus } from "../types";

type CandidatesPageProps = {
  selectedJobId: string | null;
  jobs: Job[];
  candidates: Candidate[];
  systemStatus?: SystemStatus | null;
  onSelectJob: (jobId: string) => void;
  onLoadedCandidates: (candidates: Candidate[]) => void;
  onReviewCandidate: (candidate: Candidate) => void;
};

export function CandidatesPage({
  selectedJobId,
  jobs,
  candidates,
  systemStatus = null,
  onSelectJob,
  onLoadedCandidates,
  onReviewCandidate
}: CandidatesPageProps) {
  const [status, setStatus] = useState("正在加载已搜索候选人...");
  const [activeCandidateId, setActiveCandidateId] = useState<string | null>(null);
  const searchBlockedByStorage =
    systemStatus?.environment === "vercel" &&
    !systemStatus.capabilities.persistent_storage_configured;

  const activeCandidate = useMemo(() => {
    return (
      candidates.find((candidate) => candidate.id === activeCandidateId) ??
      candidates[0] ??
      null
    );
  }, [activeCandidateId, candidates]);

  useEffect(() => {
    if (!selectedJobId) {
      setStatus("请先选择岗位再查看候选人。");
      return;
    }
    let ignore = false;
    api
      .listCandidates(selectedJobId)
      .then(async (loadedCandidates) => {
        if (ignore) {
          return;
        }
        onLoadedCandidates(loadedCandidates);
        setActiveCandidateId((currentCandidateId) => {
          if (loadedCandidates.some((candidate) => candidate.id === currentCandidateId)) {
            return currentCandidateId;
          }
          return loadedCandidates[0]?.id ?? null;
        });
        setStatus(
          loadedCandidates.length > 0
            ? "请查看已完成搜索任务中的候选人。"
            : searchBlockedByStorage
              ? "当前生产环境未配置持久化数据库，无法搜索。"
              : "该岗位尚无搜索到的候选人。"
        );
        if (loadedCandidates.length === 0 && jobs.length > 1) {
          await selectLatestCandidateJob(selectedJobId, jobs, onSelectJob, () => ignore);
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "无法加载候选人。");
        }
      });
    return () => {
      ignore = true;
    };
  }, [jobs, onLoadedCandidates, onSelectJob, selectedJobId]);

  return (
    <div className="candidates-grid">
      <section className="card candidate-list-pane" aria-label="候选人列表">
        <p className="section-kicker">候选人评审队列</p>
        <h2 id="candidates-heading">候选人</h2>
        {jobs.length > 0 ? (
          <label className="compact-field">
            评审岗位
            <select
              value={selectedJobId ?? ""}
              onChange={(event) => onSelectJob(event.target.value)}
            >
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <p className="muted">{status}</p>
        {searchBlockedByStorage ? (
          <p className="muted">
            当前生产环境无法写入搜索数据，候选人评审队列将保持为空。
          </p>
        ) : null}
        <div className="candidate-list">
          {candidates.map((candidate) => (
            <button
              key={candidate.id}
              type="button"
              className="list-row candidate-list-row"
              aria-pressed={candidate.id === activeCandidate?.id}
              onClick={() => setActiveCandidateId(candidate.id)}
            >
              <strong>{candidate.name}</strong>
              <span>{candidate.headline ?? "未获取简介"}</span>
              <span>{[candidate.current_company, candidate.location].filter(Boolean).join(" · ")}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="card candidate-detail-pane" aria-label="候选人详情">
        <p className="section-kicker">当前候选人</p>
        <CandidateDetail candidate={activeCandidate} onReviewCandidate={onReviewCandidate} />
      </section>
    </div>
  );
}

async function selectLatestCandidateJob(
  selectedJobId: string,
  jobs: Job[],
  onSelectJob: (jobId: string) => void,
  isIgnored: () => boolean
) {
  try {
    const latestCandidates = await api.listCandidates();
    const latestCandidate = latestCandidates.find((candidate) => candidate.last_search_run_id);
    if (isIgnored() || !latestCandidate?.last_search_run_id) {
      return;
    }
    const latestSearchRun = await api.getSearchRun(latestCandidate.last_search_run_id);
    if (
      !isIgnored() &&
      latestSearchRun.job_id !== selectedJobId &&
      jobs.some((job) => job.id === latestSearchRun.job_id)
    ) {
      onSelectJob(latestSearchRun.job_id);
    }
  } catch {
    return;
  }
}

function CandidateDetail({
  candidate,
  onReviewCandidate
}: {
  candidate: Candidate | null;
  onReviewCandidate: (candidate: Candidate) => void;
}) {
  if (candidate === null) {
    return <p className="empty-state">请选择候选人以查看搜索证据。</p>;
  }

  const raw = rawProfile(candidate);
  const signals = stringList(raw.signals);
  const risks = stringList(raw.risks);
  const sources = sourceList(raw.sources);
  const channels = candidateChannels(candidate, raw);

  return (
    <div className="candidate-detail">
      <div className="split-heading">
        <h3>{candidate.name}</h3>
        <span>{candidate.last_search_rank ? `第 ${candidate.last_search_rank} 名` : "已入库"}</span>
      </div>
      <p>{candidate.headline ?? "未获取简介"}</p>
      <p className="muted">
        {[candidate.current_company, candidate.location].filter(Boolean).join(" · ")}
      </p>
      <a href={candidate.profile_url} target="_blank" rel="noreferrer">
        打开 {sourceLabel(candidate.profile_source)} 资料
      </a>
      <div className="candidate-profile-summary">
        <p className="detail-label">岗位匹配信息</p>
        <p>{signals[0] ?? "尚未提取到可确认的岗位匹配信号。"}</p>
        <p className="detail-label">候选人所在地区</p>
        <p>{candidate.location ?? "公开资料未提供所在地。"}</p>
        <p className="detail-label">搜索渠道</p>
        <p>{channels.join("、")}</p>
        {candidate.last_search_query ? (
          <>
            <p className="detail-label">本次搜索关键词</p>
            <p>{candidate.last_search_query}</p>
          </>
        ) : null}
      </div>
      <EvidenceList label="匹配信号" items={signals} />
      <EvidenceList label="风险信号" items={risks} />
      {sources.length > 0 ? (
        <div>
          <p className="detail-label">来源</p>
          <div className="source-list">
            {sources.map((source) => (
              <a key={source.url} href={source.url} target="_blank" rel="noreferrer">
                {source.title}
              </a>
            ))}
          </div>
        </div>
      ) : null}
      <button
        type="button"
        className="secondary-action"
        onClick={() => onReviewCandidate(candidate)}
      >
        评审 {candidate.name}
      </button>
    </div>
  );
}

function candidateChannels(candidate: Candidate, raw: Record<string, unknown>): string[] {
  const channels = new Set([sourceLabel(candidate.profile_source)]);
  const sources = raw.sources;
  if (Array.isArray(sources)) {
    for (const source of sources) {
      if (typeof source === "object" && source !== null && !Array.isArray(source)) {
        const sourceRecord = source as Record<string, unknown>;
        const sourceType =
          typeof sourceRecord.source_type === "string"
            ? sourceRecord.source_type
            : typeof sourceRecord.channel === "string"
              ? sourceRecord.channel
              : null;
        if (sourceType) {
          channels.add(sourceLabel(sourceType));
        }
      }
    }
  }
  return [...channels];
}

function EvidenceList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div>
      <p className="detail-label">{label}</p>
      <ul className="compact-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function rawProfile(candidate: Candidate): Record<string, unknown> {
  const raw = candidate.profile_data.raw;
  if (typeof raw === "object" && raw !== null && !Array.isArray(raw)) {
    return raw as Record<string, unknown>;
  }
  return {};
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.length > 0);
}

function sourceList(value: unknown): Array<{ title: string; url: string }> {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (typeof item !== "object" || item === null || Array.isArray(item)) {
      return [];
    }
    const source = item as Record<string, unknown>;
    const title = typeof source.title === "string" ? source.title : null;
    const url = typeof source.url === "string" ? source.url : null;
    const sourceType =
      typeof source.source_type === "string"
        ? source.source_type
        : typeof source.channel === "string"
          ? source.channel
          : inferSourceType(url);
    return title && url
      ? [{ title: formatSourceLabel(sourceType, title), url }]
      : [];
  });
}

function sourceLabel(value: string): string {
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

function inferSourceType(url: string | null): string {
  if (!url) {
    return "来源";
  }
  if (url.includes("linkedin.com")) {
    return "linkedin";
  }
  if (url.includes("github.com")) {
    return "github";
  }
  if (url.includes("openreview.net")) {
    return "openreview";
  }
  if (url.includes("arxiv.org")) {
    return "arxiv";
  }
  if (url.includes("exa.ai")) {
    return "exa";
  }
  if (url.includes("brightdata.com")) {
    return "brightdata_discover";
  }
  return "source";
}

function formatSourceLabel(sourceType: string, title: string): string {
  const labels: Record<string, string> = {
    linkedin: "LinkedIn",
    github: "GitHub",
    openreview: "OpenReview",
    arxiv: "arXiv",
    exa: "Exa",
    brightdata_discover: "Bright Data Discover",
    source: "来源"
  };
  return `${labels[sourceType] ?? sourceType}: ${title}`;
}
