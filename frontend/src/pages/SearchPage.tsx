import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { api } from "../api";
import type {
  Candidate,
  Job,
  SearchChannel,
  SearchRun,
  SearchRunDetail,
  SystemStatus
} from "../types";

const SEARCH_CHANNEL_OPTIONS: Array<{ value: SearchChannel; label: string }> = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "github", label: "GitHub" },
  { value: "openreview", label: "OpenReview" },
  { value: "arxiv", label: "arXiv" },
  { value: "exa", label: "Exa" },
  { value: "brightdata_discover", label: "Bright Data Discover" }
];

type SearchPageProps = {
  jobs: Job[];
  selectedJobId: string | null;
  systemStatus: SystemStatus | null;
  onSelectJob: (jobId: string) => void;
  onCandidatesFound: (candidates: Candidate[]) => void;
  onReviewCandidate: (candidate: Candidate) => void;
};

export function SearchPage({
  jobs,
  selectedJobId,
  systemStatus,
  onSelectJob,
  onCandidatesFound,
  onReviewCandidate
}: SearchPageProps) {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState("10");
  const [channels, setChannels] = useState<SearchChannel[]>([]);
  const [runs, setRuns] = useState<SearchRun[]>([]);
  const [runDetails, setRunDetails] = useState<Record<string, SearchRunDetail>>({});
  const [status, setStatus] = useState("请选择岗位后创建搜索任务。");
  const [isSearching, setIsSearching] = useState(false);
  const startedRunIds = useRef(new Set<string>());
  const selectedJob = jobs.find((job) => job.id === selectedJobId) ?? null;
  const availableChannels = useMemo(
    () => searchChannelsForStatus(systemStatus),
    [systemStatus]
  );
  const searchBlockedByStorage =
    systemStatus?.environment === "vercel" &&
    !systemStatus.capabilities.persistent_storage_configured;
  const activeRunIdsKey = runs
    .filter((run) => run.status === "pending" || run.status === "running")
    .map((run) => run.id)
    .join("|");

  useEffect(() => {
    setQuery(searchQueryForJob(selectedJob));
    const preferredChannels = selectedJob?.search_channels ?? [];
    const nextChannels =
      availableChannels.length === 0
        ? preferredChannels
        : preferredChannels.filter((channel) => availableChannels.includes(channel));
    setChannels((currentChannels) =>
      sameChannels(currentChannels, nextChannels) ? currentChannels : nextChannels
    );
  }, [availableChannels, selectedJob]);

  useEffect(() => {
    if (!selectedJobId) {
      setRuns([]);
      setRunDetails({});
      return;
    }
    let ignore = false;
    api
      .listSearchRuns(selectedJobId)
      .then((loadedRuns) => {
        if (!ignore) {
          setRuns(loadedRuns);
          setRunDetails({});
          loadedRuns.forEach((run) => {
            api
              .getSearchRun(run.id)
              .then((detail) => {
                if (!ignore) {
                  setRunDetails((current) => ({ ...current, [run.id]: detail }));
                }
              })
              .catch(() => undefined);
          });
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "无法加载搜索任务历史。");
        }
      });
    return () => {
      ignore = true;
    };
  }, [selectedJobId]);

  useEffect(() => {
    if (activeRunIdsKey.length === 0) {
      return;
    }
    const activeRunIds = activeRunIdsKey.split("|");

    let ignore = false;
    const refresh = () => {
      activeRunIds.forEach((runId) => {
        api
          .getSearchRun(runId)
          .then((detail) => {
            if (!ignore) {
              applyRunDetail(detail);
            }
          })
          .catch(() => undefined);
      });
    };
    refresh();
    const interval = window.setInterval(refresh, 1_000);
    return () => {
      ignore = true;
      window.clearInterval(interval);
    };
  }, [activeRunIdsKey]);

  function applyRunDetail(detail: SearchRunDetail) {
    setRunDetails((current) => ({ ...current, [detail.id]: detail }));
    setRuns((current) =>
      current.map((run) => (run.id === detail.id ? searchRunFromDetail(detail) : run))
    );
    if (detail.status === "completed") {
      onCandidatesFound(detail.candidates);
      setStatus(`搜索完成，找到 ${detail.candidates.length} 位候选人。`);
      setIsSearching(false);
    } else if (detail.status === "failed") {
      setStatus(searchRunError(detail) || "搜索失败，请在搜索历史中查看详情。");
      setIsSearching(false);
    }
  }

  function startRun(searchRunId: string) {
    if (startedRunIds.current.has(searchRunId)) {
      return;
    }
    startedRunIds.current.add(searchRunId);
    void api
      .runSearchRun(searchRunId)
      .then(applyRunDetail)
      .catch((error: unknown) => {
        setStatus(error instanceof Error ? error.message : "无法执行搜索任务。");
        setIsSearching(false);
      });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedJobId) {
      setStatus("请先创建或选择岗位。");
      return;
    }
    if (searchBlockedByStorage) {
      setStatus(
        "当前生产环境未配置持久化数据库，无法搜索。"
      );
      return;
    }
    if (channels.length === 0) {
      setStatus("当前部署没有可用的搜索渠道。");
      return;
    }
    setIsSearching(true);
    setStatus(`正在通过 ${formatChannels(channels)} 搜索候选人...`);
    try {
      const result = await api.createSearch({
        job_id: selectedJobId,
        query,
        channels,
        params: {
          limit: Number(limit) || 10,
          region: selectedJob?.region.trim() ?? ""
        }
      });
      setRuns((current) => [result, ...current.filter((run) => run.id !== result.id)]);
      setStatus(`搜索任务已进入队列：${formatChannels(result.channels)}。`);
      startRun(result.id);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "无法创建搜索任务。");
    }
  }

  return (
    <section className="workspace-grid" aria-labelledby="search-heading">
      <div className="card card-form">
        <p className="section-kicker">人才搜索</p>
        <h2 id="search-heading">搜索任务</h2>
        <form className="stack" onSubmit={handleSubmit}>
          <label>
            岗位
            <select
              value={selectedJobId ?? ""}
              onChange={(event) => onSelectJob(event.target.value)}
              required
            >
              <option value="" disabled>
                选择岗位
              </option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            搜索条件
            <textarea
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              required
              rows={5}
            />
          </label>
          <label>
            候选人数量
            <input
              min="1"
              type="number"
              value={limit}
              onChange={(event) => setLimit(event.target.value)}
            />
          </label>
          <SearchChannelField
            value={channels}
            onChange={setChannels}
            availableChannels={availableChannels}
          />
          <div className="search-channel-summary" aria-live="polite">
            <span className="detail-label">搜索渠道</span>
            <strong>{formatChannels(channels)}</strong>
          </div>
          <div className="search-channel-summary">
            <span className="detail-label">工作地区</span>
            <strong>{selectedJob?.region.trim() || "未设置工作地区"}</strong>
          </div>
          {searchBlockedByStorage ? (
            <p className="muted">
              当前生产环境未配置持久化数据库，无法搜索。
            </p>
          ) : null}
          <button
            className="primary-action"
            type="submit"
            disabled={isSearching || channels.length === 0 || searchBlockedByStorage}
          >
            创建搜索任务
          </button>
        </form>
        <p className="muted">{status}</p>
      </div>

      <div className="card">
        <p className="section-kicker">搜索历史</p>
        <h3>{runs.length} 条已保存记录</h3>
        <div className="job-list">
          {runs.map((run) => (
            <article key={run.id} className="list-row static-row">
              <strong>{run.query}</strong>
              <span>
                {searchRunStatusLabel(run.status)} · {run.candidate_count} 位候选人
              </span>
              <span>{formatRunRegion(run.params)}</span>
              <span>{run.channels.map(channelLabel).join(" + ")}</span>
              <RunProgress progress={run.progress} />
              <RunCandidates
                candidates={runDetails[run.id]?.candidates ?? []}
                onReviewCandidate={onReviewCandidate}
              />
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function searchRunFromDetail(detail: SearchRunDetail): SearchRun {
  const { candidates: _candidates, ...run } = detail;
  return run;
}

function searchRunError(detail: SearchRunDetail): string | null {
  const errorMessage = detail.progress.error_message;
  return typeof errorMessage === "string" && errorMessage.length > 0 ? errorMessage : null;
}

function searchRunStatusLabel(status: string): string {
  return (
    {
      pending: "等待执行",
      running: "正在搜索",
      completed: "已完成",
      failed: "失败"
    }[status] ?? status
  );
}

function RunProgress({ progress = {} }: { progress?: Record<string, unknown> }) {
  const worker = typeof progress.worker === "number" ? progress.worker : 1;
  const completed = typeof progress.completed_channels === "number" ? progress.completed_channels : 0;
  const total = typeof progress.total_channels === "number" ? progress.total_channels : 0;
  const active = typeof progress.active_channel === "string" ? progress.active_channel : null;
  const errorMessage = typeof progress.error_message === "string" ? progress.error_message : null;
  const channelErrors = channelErrorsForProgress(progress);

  return (
    <div className="run-progress">
      <span aria-label={`执行器 ${worker}；已完成 ${completed}/${total} 个渠道`}>
        执行器 {worker} · 已完成 {completed}/{total} 个渠道
        {active ? ` · ${channelLabel(active)}` : ""}
      </span>
      {channelErrors.map(([channel, error]) => (
        <span key={channel} className="run-channel-error">
          {channelLabel(channel)} 失败：{error}
        </span>
      ))}
      {errorMessage ? <span className="run-channel-error">任务失败：{errorMessage}</span> : null}
    </div>
  );
}

function channelErrorsForProgress(progress: Record<string, unknown>): Array<[string, string]> {
  const value = progress.channel_errors;
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return [];
  }
  return Object.entries(value).flatMap(([channel, error]) =>
    typeof error === "string" && error.length > 0 ? [[channel, error]] : []
  );
}

function SearchChannelField({
  value,
  onChange,
  availableChannels
}: {
  value: SearchChannel[];
  onChange: (channels: SearchChannel[]) => void;
  availableChannels: SearchChannel[];
}) {
  return (
    <fieldset className="channel-fieldset">
      <legend>搜索渠道</legend>
      <div className="channel-option-list">
        {SEARCH_CHANNEL_OPTIONS.map((channel) => (
          <label key={channel.value} className="checkbox-row">
            <input
              type="checkbox"
              checked={value.includes(channel.value)}
              disabled={!availableChannels.includes(channel.value)}
              onChange={() => onChange(toggleChannel(value, channel.value))}
            />
            <span className="channel-option-label">
              {channel.label}
              {!availableChannels.includes(channel.value) ? (
                <span className="channel-option-state">暂不可用</span>
              ) : null}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function toggleChannel(current: SearchChannel[], channel: SearchChannel): SearchChannel[] {
  if (current.includes(channel)) {
    return current.filter((value) => value !== channel);
  }
  return SEARCH_CHANNEL_OPTIONS.map((option) => option.value).filter(
    (value) => value === channel || current.includes(value)
  );
}

function sameChannels(current: SearchChannel[], next: SearchChannel[]): boolean {
  if (current.length !== next.length) {
    return false;
  }
  return current.every((channel, index) => channel === next[index]);
}

function channelLabel(channel: string): string {
  return SEARCH_CHANNEL_OPTIONS.find((option) => option.value === channel)?.label ?? channel;
}

function formatChannels(channels: string[]): string {
  const labels = channels.map(channelLabel);
  if (labels.length === 0) {
    return "未选择渠道";
  }
  return labels.join(" + ");
}

function formatRunRegion(params: Record<string, unknown> = {}): string {
  const region = typeof params.region === "string" ? params.region.trim() : "";
  return region || "未设置工作地区";
}

function searchQueryForJob(job: Job | null): string {
  if (job === null) {
    return "";
  }

  return job.search_notes.trim() || job.description.trim() || job.title;
}

function searchChannelsForStatus(systemStatus: SystemStatus | null): SearchChannel[] {
  if (systemStatus === null) {
    return SEARCH_CHANNEL_OPTIONS.map((channel) => channel.value);
  }

  const channelAvailability = systemStatus.capabilities.channel_availability;
  if (channelAvailability) {
    return SEARCH_CHANNEL_OPTIONS.map((channel) => channel.value).filter(
      (channel) => channelAvailability[channel] ?? false
    );
  }

  const publicChannels = new Set(systemStatus.capabilities.public_channels as SearchChannel[]);
  return SEARCH_CHANNEL_OPTIONS.map((channel) => channel.value).filter((channel) => {
    if (publicChannels.has(channel)) {
      return true;
    }
    if (channel === "exa") {
      return systemStatus.capabilities.exa_configured;
    }
    if (channel === "linkedin") {
      return systemStatus.capabilities.linkedin_configured ?? (
        systemStatus.capabilities.exa_configured ||
        systemStatus.capabilities.brightdata_configured
      );
    }
    if (channel === "brightdata_discover") {
      return systemStatus.capabilities.brightdata_configured;
    }
    return false;
  });
}

function RunCandidates({
  candidates,
  onReviewCandidate
}: {
  candidates: Candidate[];
  onReviewCandidate: (candidate: Candidate) => void;
}) {
  if (candidates.length === 0) {
    return null;
  }

  return (
    <div className="run-candidate-list">
      {candidates.map((candidate) => (
        <button
          key={candidate.id}
          type="button"
          className="text-action run-candidate-row"
          aria-label={`查看 ${candidate.name}`}
          onClick={() => onReviewCandidate(candidate)}
        >
          <strong>{candidate.name}</strong>
          <span>{candidate.headline ?? "未获取简介"}</span>
        </button>
      ))}
    </div>
  );
}
