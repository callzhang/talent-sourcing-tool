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
  const [status, setStatus] = useState("Loading jobs...");
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
        setStatus(loadedJobs.length > 0 ? "Select a JD to inspect its rubric." : "No JDs yet.");
        if (!selectedJobId && loadedJobs[0]) {
          onSelectJob(loadedJobs[0].id);
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "Unable to load jobs.");
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
          setStatus(error instanceof Error ? error.message : "Unable to load rubric.");
        }
      });
    return () => {
      ignore = true;
    };
  }, [selectedJobId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (jobsBlockedByStorage) {
      setStatus("Job creation is disabled in this deployment until durable database storage is configured.");
      return;
    }
    setIsSaving(true);
    setStatus("Generating rubric...");
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
      setStatus("JD created and rubric generated.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to create JD.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="jobs-grid">
      <section className="card job-list-pane" aria-label="Job listings">
        <p className="section-kicker">Jobs</p>
        <div className="split-heading">
          <h2 id="jobs-heading">Job listings</h2>
          <button
            type="button"
            className="secondary-action"
            onClick={startNewJob}
            disabled={jobsBlockedByStorage}
          >
            New Job
          </button>
        </div>
        <p className="muted">{status}</p>
        {jobsBlockedByStorage ? (
          <p className="muted">
            Job creation is blocked in production until durable database storage is configured.
          </p>
        ) : null}
        <div className="job-list">
          {jobs.map((job) => (
            <button
              key={job.id}
              type="button"
              className="list-row"
              aria-pressed={job.id === selectedJobId}
              onClick={() => onSelectJob(job.id)}
            >
              <strong>{job.title}</strong>
            </button>
          ))}
        </div>
      </section>

      <section className="card job-detail-pane" aria-label="Job detail">
        {isCreating ? (
          <section aria-labelledby="create-job-heading">
            <p className="section-kicker">New job</p>
            <h2 id="create-job-heading">Job draft</h2>
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
            <p className="section-kicker">Active rubric</p>
            <div className="split-heading">
              <h3>{activeJob?.job.title ?? "No JD selected"}</h3>
              {activeJob ? <span>{`v${activeJob.rubric.version}`}</span> : null}
            </div>
            <JobDetail job={activeJob} />
            <RubricPreview job={activeJob} />
          </>
        )}
      </section>
    </div>
  );

  function startNewJob() {
    if (jobsBlockedByStorage) {
      setStatus("Job creation is disabled in this deployment until durable database storage is configured.");
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
}

function JobDetail({ job }: { job: JobWithRubric | null }) {
  if (job === null) {
    return null;
  }

  return (
    <div className="job-detail">
      <DetailBlock label="JD description" value={job.job.description} />
      <DetailBlock label="Region" value={job.job.region} />
      <DetailBlock label="Target profile" value={job.job.target_profile_text} />
      <DetailBlock label="Red flags" value={job.job.red_flags_text} />
      <DetailBlock label="Search notes" value={job.job.search_notes} />
      <DetailBlock label="Search channels" value={job.job.search_channels.map(channelLabel).join(", ")} />
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
    return <p className="empty-state">Select a JD to see rubric dimensions.</p>;
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
            <EvidenceList label="Signals" items={dimension.signals} />
          ) : null}
          {dimension.red_flags && dimension.red_flags.length > 0 ? (
            <EvidenceList label="Red flags" items={dimension.red_flags} />
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
        JD title
        <input value={title} onChange={(event) => onTitleChange(event.target.value)} required />
      </label>
      <label>
        JD description
        <textarea
          value={description}
          onChange={(event) => onDescriptionChange(event.target.value)}
          required
          rows={5}
        />
      </label>
      <label>
        Region
        <input value={region} onChange={(event) => onRegionChange(event.target.value)} />
      </label>
      <label>
        Target profile
        <textarea
          value={targetProfile}
          onChange={(event) => onTargetProfileChange(event.target.value)}
        />
      </label>
      <label>
        Red flags
        <textarea value={redFlags} onChange={(event) => onRedFlagsChange(event.target.value)} />
      </label>
      <label>
        Search notes
        <textarea value={searchNotes} onChange={(event) => onSearchNotesChange(event.target.value)} />
      </label>
      <SearchChannelField value={searchChannels} onChange={onSearchChannelsChange} />
      <button className="primary-action" type="submit" disabled={isSaving || jobsBlockedByStorage}>
        Save Job
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
      <legend>Search channels</legend>
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
