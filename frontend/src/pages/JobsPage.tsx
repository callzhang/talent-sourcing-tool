import { FormEvent, useEffect, useState } from "react";

import { api } from "../api";
import type { Job, JobWithRubric, SearchChannel, SystemStatus } from "../types";

const SEARCH_CHANNEL_OPTIONS: Array<{ value: SearchChannel; label: string }> = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "github", label: "GitHub" },
  { value: "openreview", label: "OpenReview" },
  { value: "arxiv", label: "arXiv" },
  { value: "exa", label: "Exa" },
  { value: "brightdata_discover", label: "Bright Data Discover" }
];

type JobsPageProps = {
  selectedJobId: string | null;
  systemStatus?: SystemStatus | null;
  onSelectJob: (jobId: string) => void;
  onCreatedJob: (job: JobWithRubric) => void;
};

export function JobsPage({
  selectedJobId,
  systemStatus = null,
  onSelectJob,
  onCreatedJob
}: JobsPageProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeJob, setActiveJob] = useState<JobWithRubric | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [region, setRegion] = useState("");
  const [targetProfile, setTargetProfile] = useState("");
  const [redFlags, setRedFlags] = useState("");
  const [searchNotes, setSearchNotes] = useState("");
  const [searchChannels, setSearchChannels] = useState<SearchChannel[]>([
    "linkedin",
    "github",
    "exa",
    "brightdata_discover"
  ]);
  const [status, setStatus] = useState("正在加载岗位...");
  const [isSaving, setIsSaving] = useState(false);
  const jobsBlockedByStorage =
    systemStatus?.environment === "vercel" &&
    !systemStatus.capabilities.persistent_storage_configured;

  useEffect(() => {
    let ignore = false;
    api
      .listJobs()
      .then((loadedJobs) => {
        if (ignore) {
          return;
        }
        setJobs(loadedJobs);
        setStatus(loadedJobs.length > 0 ? "请选择岗位以查看评分标准。" : "尚无岗位。");
        if (!selectedJobId && loadedJobs[0]) {
          onSelectJob(loadedJobs[0].id);
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "无法加载岗位。");
        }
      });
    return () => {
      ignore = true;
    };
  }, [onSelectJob, selectedJobId]);

  useEffect(() => {
    if (!selectedJobId) {
      setActiveJob(null);
      return;
    }
    // Clear the old detail before requesting the next job so a selection never
    // appears to show the wrong role while the network request is in flight.
    setActiveJob(null);
    let ignore = false;
    api
      .getJob(selectedJobId)
      .then((job) => {
        if (!ignore) {
          setIsCreating(false);
          setActiveJob(job);
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "无法加载评分标准。");
        }
      });
    return () => {
      ignore = true;
    };
  }, [selectedJobId]);

  // A parent selection update and the detail fetch are independent. Only show
  // data whose job id matches the current selection; otherwise the two panes
  // can briefly describe different roles.
  const displayedJob = activeJob?.job.id === selectedJobId ? activeJob : null;
  const isLoadingSelectedJob = selectedJobId !== null && displayedJob === null && !isCreating;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (jobsBlockedByStorage) {
      setStatus("当前部署尚未配置持久化数据库，无法新建岗位。");
      return;
    }
    setIsSaving(true);
    setStatus("正在生成评分标准...");
    try {
      const created = await api.createJob({
        title,
        description,
        region,
        target_profile_text: targetProfile,
        red_flags_text: redFlags,
        search_notes: searchNotes,
        search_channels: searchChannels
      });
      setJobs((current) => [created.job, ...current.filter((job) => job.id !== created.job.id)]);
      setActiveJob(created);
      setIsCreating(false);
      onCreatedJob(created);
      setStatus("岗位和评分标准已创建。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "无法创建岗位。");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="jobs-grid">
      <section className="card job-list-pane" aria-label="岗位列表">
        <p className="section-kicker">岗位</p>
        <div className="split-heading">
          <h2 id="jobs-heading">岗位列表</h2>
          <button
            type="button"
            className="secondary-action"
            onClick={startNewJob}
            disabled={jobsBlockedByStorage}
          >
            新建岗位
          </button>
        </div>
        <p className="muted">{status}</p>
        {jobsBlockedByStorage ? (
          <p className="muted">
            当前生产环境未配置持久化数据库，无法新建岗位。
          </p>
        ) : null}
        <div className="job-list">
          {jobs.map((job) => (
            <button
              key={job.id}
              type="button"
              className="list-row"
              aria-pressed={job.id === selectedJobId}
              onClick={() => selectJob(job.id)}
            >
              <strong>{job.title}</strong>
            </button>
          ))}
        </div>
      </section>

      <section className="card job-detail-pane" aria-label="岗位详情">
        {isCreating ? (
          <section aria-labelledby="create-job-heading">
            <p className="section-kicker">新建岗位</p>
            <h2 id="create-job-heading">岗位信息</h2>
            <JobForm
              title={title}
              description={description}
              region={region}
              targetProfile={targetProfile}
              redFlags={redFlags}
              searchNotes={searchNotes}
              searchChannels={searchChannels}
              isSaving={isSaving}
              jobsBlockedByStorage={jobsBlockedByStorage}
              onTitleChange={setTitle}
              onDescriptionChange={setDescription}
              onRegionChange={setRegion}
              onTargetProfileChange={setTargetProfile}
              onRedFlagsChange={setRedFlags}
              onSearchNotesChange={setSearchNotes}
              onSearchChannelsChange={setSearchChannels}
              onSubmit={handleSubmit}
            />
          </section>
        ) : (
          <>
            <p className="section-kicker">当前评分标准</p>
            <div className="split-heading">
              <h3>{isLoadingSelectedJob ? "正在加载岗位详情..." : displayedJob?.job.title ?? "未选择岗位"}</h3>
              {displayedJob ? <span>{`v${displayedJob.rubric.version}`}</span> : null}
            </div>
            {isLoadingSelectedJob ? <p className="empty-state">正在加载评分标准。</p> : null}
            {!isLoadingSelectedJob ? <JobDetail job={displayedJob} /> : null}
            {!isLoadingSelectedJob ? <RubricPreview job={displayedJob} /> : null}
          </>
        )}
      </section>
    </div>
  );

  function startNewJob() {
    if (jobsBlockedByStorage) {
      setStatus("当前部署尚未配置持久化数据库，无法新建岗位。");
      return;
    }
    setIsCreating(true);
    setActiveJob(null);
    setTitle("");
    setDescription("");
    setRegion("");
    setTargetProfile("");
    setRedFlags("");
    setSearchNotes("");
    setSearchChannels(["linkedin", "github", "exa", "brightdata_discover"]);
  }

  function selectJob(jobId: string) {
    // Effects run after paint. Clear synchronously from the click so the old
    // job cannot remain visible beside the newly selected list item.
    setIsCreating(false);
    setActiveJob(null);
    onSelectJob(jobId);
  }
}

function JobDetail({ job }: { job: JobWithRubric | null }) {
  if (job === null) {
    return null;
  }

  return (
    <div className="job-detail">
      <DetailBlock label="职位描述" value={job.job.description} />
      <DetailBlock label="工作地区" value={job.job.region} />
      <DetailBlock label="目标画像" value={job.job.target_profile_text} />
      <DetailBlock label="排除条件" value={job.job.red_flags_text} />
      <DetailBlock label="搜索要点" value={job.job.search_notes} />
      <DetailBlock label="搜索渠道" value={job.job.search_channels.map(channelLabel).join(", ")} />
    </div>
  );
}

function DetailBlock({ label, value }: { label: string; value: string }) {
  if (!value.trim()) {
    return null;
  }

  return (
    <section className="detail-block" aria-label={label}>
      <p className="detail-label">{label}</p>
      <p>{value}</p>
    </section>
  );
}

function RubricPreview({ job }: { job: JobWithRubric | null }) {
  if (job === null) {
    return <p className="empty-state">请选择岗位以查看评分维度。</p>;
  }

  return (
    <div className="rubric-list">
      {job.rubric.rubric.dimensions.map((dimension) => (
        <article key={dimension.name} className="rubric-item">
          <strong>{dimension.name}</strong>
          {dimension.weight !== undefined ? <span>{dimension.weight}%</span> : null}
          {dimension.description ? <p>{dimension.description}</p> : null}
          {dimension.scoring_guidance ? <p>{dimension.scoring_guidance}</p> : null}
          {dimension.signals && dimension.signals.length > 0 ? (
            <EvidenceList label="匹配信号" items={dimension.signals} />
          ) : null}
          {dimension.red_flags && dimension.red_flags.length > 0 ? (
            <EvidenceList label="风险信号" items={dimension.red_flags} />
          ) : null}
        </article>
      ))}
    </div>
  );
}

type JobFormProps = {
  title: string;
  description: string;
  region: string;
  targetProfile: string;
  redFlags: string;
  searchNotes: string;
  searchChannels: SearchChannel[];
  isSaving: boolean;
  jobsBlockedByStorage: boolean;
  onTitleChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onRegionChange: (value: string) => void;
  onTargetProfileChange: (value: string) => void;
  onRedFlagsChange: (value: string) => void;
  onSearchNotesChange: (value: string) => void;
  onSearchChannelsChange: (value: SearchChannel[]) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

function JobForm({
  title,
  description,
  region,
  targetProfile,
  redFlags,
  searchNotes,
  searchChannels,
  isSaving,
  jobsBlockedByStorage,
  onTitleChange,
  onDescriptionChange,
  onRegionChange,
  onTargetProfileChange,
  onRedFlagsChange,
  onSearchNotesChange,
  onSearchChannelsChange,
  onSubmit
}: JobFormProps) {
  return (
    <form className="stack" onSubmit={onSubmit}>
      <label>
        岗位名称
        <input value={title} onChange={(event) => onTitleChange(event.target.value)} required />
      </label>
      <label>
        职位描述
        <textarea
          value={description}
          onChange={(event) => onDescriptionChange(event.target.value)}
          required
          rows={5}
        />
      </label>
      <label>
        工作地区
        <input value={region} onChange={(event) => onRegionChange(event.target.value)} />
      </label>
      <label>
        目标画像
        <textarea
          value={targetProfile}
          onChange={(event) => onTargetProfileChange(event.target.value)}
        />
      </label>
      <label>
        排除条件
        <textarea value={redFlags} onChange={(event) => onRedFlagsChange(event.target.value)} />
      </label>
      <label>
        搜索要点
        <textarea value={searchNotes} onChange={(event) => onSearchNotesChange(event.target.value)} />
      </label>
      <SearchChannelField value={searchChannels} onChange={onSearchChannelsChange} />
      <button className="primary-action" type="submit" disabled={isSaving || jobsBlockedByStorage}>
        保存岗位
      </button>
    </form>
  );
}

function EvidenceList({ label, items }: { label: string; items: string[] }) {
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

function SearchChannelField({
  value,
  onChange
}: {
  value: SearchChannel[];
  onChange: (channels: SearchChannel[]) => void;
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
              onChange={() => onChange(toggleChannel(value, channel.value))}
            />
            <span className="channel-option-label">{channel.label}</span>
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

function channelLabel(channel: string): string {
  return SEARCH_CHANNEL_OPTIONS.find((option) => option.value === channel)?.label ?? channel;
}
