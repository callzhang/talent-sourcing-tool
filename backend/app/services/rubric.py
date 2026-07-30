from __future__ import annotations

import hashlib
import json
from typing import Any

from app.schemas import JobCreate


def source_hash(job: JobCreate) -> str:
    source = job.model_dump(mode="json")
    payload = json.dumps(source, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_rubric(job: JobCreate) -> dict[str, Any]:
    dimensions = [
        {
            "name": "岗位匹配度",
            "description": "与岗位场景、领域和目标画像的匹配程度。",
            "signals": [job.target_profile_text or job.description],
            "red_flags": [job.red_flags_text] if job.red_flags_text else [],
        },
        {
            "name": "AI 原生工作方式",
            "description": "能熟练使用 AI 工具探索、搭建原型并持续改进工作。",
            "signals": ["有使用 AI 辅助构建、迭代和判断的明确证据。"],
            "red_flags": ["将 AI 视为偶发工具，而不是工作核心能力。"],
        },
        {
            "name": "实际构建证据",
            "description": "展示已交付的原型、产品、实验或公开作品。",
            "signals": ["有可验证的产物、演示、发布记录或亲自参与的项目经历。"],
            "red_flags": ["只描述职责，没有实际构建的证据。"],
        },
        {
            "name": "沟通与判断",
            "description": "能清晰解释取舍，并作出理解产品的判断。",
            "signals": ["表达清晰、问题框定准确、优先级合理。"],
            "red_flags": ["推理不清、产品感弱或受众判断不足。"],
        },
        {
            "name": "产品与市场探索判断",
            "description": "理解用户需求、市场背景、定位和产品风险。",
            "signals": [
                "有用户洞察、市场学习、定位或产品探索的证据。"
            ],
            "red_flags": ["只优化执行，却没有验证用户或市场假设。"],
        },
    ]

    return {
        "version": 1,
        "source_hash": source_hash(job),
        "dimensions": dimensions,
    }


def rubric_to_json(job: JobCreate) -> str:
    return json.dumps(generate_rubric(job), sort_keys=True, separators=(",", ":"))
