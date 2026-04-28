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
            "name": "Role Fit",
            "description": "Matches the role context, domain, and target profile.",
            "signals": [job.target_profile_text or job.description],
            "red_flags": [job.red_flags_text] if job.red_flags_text else [],
        },
        {
            "name": "AI-Native Working Style",
            "description": "Uses AI tools fluently to explore, prototype, and improve work.",
            "signals": ["Evidence of AI-assisted building, iteration, and judgment."],
            "red_flags": ["Treats AI as incidental rather than central to the work."],
        },
        {
            "name": "Builder Evidence",
            "description": "Shows shipped prototypes, products, experiments, or public work.",
            "signals": ["Concrete artifacts, demos, launches, or hands-on project history."],
            "red_flags": ["Only describes responsibilities without proof of building."],
        },
        {
            "name": "Communication and Judgment",
            "description": "Explains tradeoffs clearly and makes product-aware decisions.",
            "signals": ["Clear writing, strong framing, and sensible prioritization."],
            "red_flags": ["Unclear reasoning, weak product sense, or poor audience judgment."],
        },
        {
            "name": "Product and Market Discovery Judgment",
            "description": "Understands user needs, market context, positioning, and product risk.",
            "signals": [
                "Evidence of customer insight, market learning, positioning, or product discovery."
            ],
            "red_flags": ["Optimizes execution without validating customer or market assumptions."],
        },
    ]

    return {
        "version": 1,
        "source_hash": source_hash(job),
        "dimensions": dimensions,
    }


def rubric_to_json(job: JobCreate) -> str:
    return json.dumps(generate_rubric(job), sort_keys=True, separators=(",", ":"))
