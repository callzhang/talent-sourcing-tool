import { useEffect, useState } from "react";

import { api } from "../api";
import type { Job, RefinementSuggestion } from "../types";

type RefinementsPageProps = {
  jobs: Job[];
  selectedJobId: string | null;
  onSelectJob: (jobId: string) => void;
};

export function RefinementsPage({ jobs, selectedJobId, onSelectJob }: RefinementsPageProps) {
  const [suggestions, setSuggestions] = useState<RefinementSuggestion[]>([]);
  const [status, setStatus] = useState("请选择岗位以查看已保存的优化建议。");

  useEffect(() => {
    if (!selectedJobId) {
      setSuggestions([]);
      return;
    }
    let ignore = false;
    api
      .listRefinementSuggestions(selectedJobId)
      .then((loadedSuggestions) => {
        if (!ignore) {
          setSuggestions(loadedSuggestions);
          setStatus(
            loadedSuggestions.length > 0
              ? "已根据淘汰原因生成优化建议。"
              : "暂无优化建议。"
          );
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "无法加载优化建议。");
        }
      });
    return () => {
      ignore = true;
    };
  }, [selectedJobId]);

  return (
    <section className="workspace-grid" aria-labelledby="refinements-heading">
      <div className="card">
        <p className="section-kicker">反馈闭环</p>
        <h2 id="refinements-heading">岗位优化建议</h2>
        <label>
          岗位
          <select
            value={selectedJobId ?? ""}
            onChange={(event) => onSelectJob(event.target.value)}
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
        <p className="muted">{status}</p>
      </div>

      <div className="card">
        <div className="refinement-grid">
          {suggestions.map((suggestion) => (
            <article key={suggestion.id} className="refinement-card">
              <p className="rank-pill">{suggestion.suggestion_type}</p>
              <h3>{suggestion.status}</h3>
              <p>{suggestion.suggestion_text}</p>
              <span>{reasonCodes(suggestion)}</span>
            </article>
          ))}
          {suggestions.length === 0 ? (
            <p className="empty-state">淘汰候选人时填写原因，即可生成岗位优化建议。</p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function reasonCodes(suggestion: RefinementSuggestion) {
  const reasonCodesValue = suggestion.suggestion_metadata.reason_codes;
  if (!Array.isArray(reasonCodesValue) || reasonCodesValue.length === 0) {
    return "未记录原因代码";
  }
  return reasonCodesValue.map(String).join(", ");
}
