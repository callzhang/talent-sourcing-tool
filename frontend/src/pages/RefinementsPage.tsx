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
              <p className="rank-pill">{suggestionTypeLabel(suggestion.suggestion_type)}</p>
              <h3>{suggestionStatusLabel(suggestion.status)}</h3>
              <p>{suggestion.suggestion_text}</p>
              <span>产生原因：{reasonCodes(suggestion)}</span>
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
    return "未提供具体淘汰原因";
  }
  return reasonCodesValue.map((reasonCode) => reasonCodeLabel(String(reasonCode))).join("；");
}

function suggestionTypeLabel(value: string): string {
  return (
    {
      feedback_review: "基于淘汰反馈的岗位优化",
      query_rewrite: "建议调整搜索条件",
      rubric_adjustment: "建议调整评估标准"
    }[value] ?? "岗位优化建议"
  );
}

function suggestionStatusLabel(value: string): string {
  return (
    {
      pending: "待 HR 审阅",
      applied: "已采纳",
      dismissed: "未采纳",
      rejected: "未采纳"
    }[value] ?? "待处理"
  );
}

function reasonCodeLabel(value: string): string {
  return (
    {
      insufficient_public_evidence: "公开资料不足，无法确认关键经历",
      weak_builder_evidence: "缺少亲自交付或产品构建证据",
      insufficient_ai_native_signal: "缺少 AI 产品实践信号",
      too_enterprise_sales_oriented: "经历偏企业销售，和岗位侧重点不匹配",
      platform_only_background: "经历偏平台建设，缺少目标岗位所需经验",
      solutions_architecture_mismatch: "解决方案架构经历与岗位要求不匹配",
      consulting_heavy_profile: "咨询经历占比较高，需补充直接业务负责证据"
    }[value] ?? "其他需要核实的岗位匹配问题"
  );
}
