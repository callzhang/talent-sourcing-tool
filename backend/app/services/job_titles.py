from __future__ import annotations


JOB_TITLE_PREFIX = "US Frontier Team - "


def normalize_job_title(title: str) -> str:
    normalized_title = " ".join(title.split())
    if normalized_title.casefold().startswith(JOB_TITLE_PREFIX.casefold()):
        return normalized_title[len(JOB_TITLE_PREFIX) :].strip()
    return normalized_title


def job_title_key(title: str) -> str:
    return normalize_job_title(title).casefold()
