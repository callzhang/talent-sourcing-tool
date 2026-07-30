from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Any, Protocol
from urllib.parse import quote_plus, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

import httpx

from app.core.config import Settings, settings


SEARCH_CHANNELS = ("linkedin", "github", "openreview", "arxiv", "exa", "brightdata_discover")
RESEARCH_CHANNELS = ("openreview", "arxiv")
TECHNICAL_CHANNELS = ("github",)
ARXIV_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass(frozen=True)
class CandidateSourceResult:
    profile_url: str
    profile_source: str
    name: str
    headline: str | None
    location: str | None
    current_company: str | None
    current_title: str | None
    raw: dict[str, Any]


class SourcingConnector(Protocol):
    def search_people(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[CandidateSourceResult]:
        """Search for people matching a sourcing query."""


class SourcingConfigError(RuntimeError):
    """Raised when a selected channel cannot run with the current configuration."""


def get_sourcing_connector() -> SourcingConnector:
    return LiveSourcingConnector()


class LiveSourcingConnector:
    def __init__(self, app_settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = app_settings or settings
        self.client = client or httpx.Client(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "talent-sourcing-tool/0.1"},
            trust_env=False,
        )

    def search_people(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[CandidateSourceResult]:
        options = params or {}
        channels = normalize_search_channels(options.get("channels", []))
        limit = max(int(options.get("limit", 10)), 1)
        region = normalize_region(options.get("region"))
        per_channel_limit = max(limit, 3)

        results: list[CandidateSourceResult] = []
        for channel in channels:
            channel_results = self._search_channel(channel, query, per_channel_limit, region)
            results.extend(channel_results)
            if len(results) >= limit * max(len(channels), 1):
                break

        return filter_results_by_region(results, region)[:limit]

    def _search_channel(
        self, channel: str, query: str, limit: int, region: str
    ) -> list[CandidateSourceResult]:
        if channel == "github":
            return self._search_github(query, limit, region)
        if channel == "openreview":
            return self._search_openreview(query, limit, region)
        if channel == "arxiv":
            return self._search_arxiv(query, limit)
        if channel == "exa":
            return self._search_exa(query, limit, region)
        if channel == "linkedin":
            return self._search_linkedin(query, limit, region)
        if channel == "brightdata_discover":
            return self._search_brightdata_discover(query, limit, region)
        raise SourcingConfigError(f"Unsupported search channel: {channel}")

    def _search_github(self, query: str, limit: int, region: str) -> list[CandidateSourceResult]:
        search_query = query
        github_region = github_location_query(region)
        if github_region:
            search_query = f'{query} location:"{github_region}"'
        response = self.client.get(
            "https://api.github.com/search/users",
            params={"q": search_query, "per_page": limit},
            headers={"Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        items = response.json().get("items", [])

        results: list[CandidateSourceResult] = []
        for item in items[:limit]:
            login = str(item.get("login", "")).strip()
            profile_url = str(item.get("html_url", "")).strip()
            if not login or not profile_url:
                continue
            details_response = self.client.get(
                f"https://api.github.com/users/{quote_plus(login)}",
                headers={"Accept": "application/vnd.github+json"},
            )
            details_response.raise_for_status()
            details = details_response.json()
            name = str(details.get("name") or login).strip()
            company = string_or_none(details.get("company"))
            location = string_or_none(details.get("location"))
            bio = string_or_none(details.get("bio"))
            results.append(
                CandidateSourceResult(
                    profile_url=profile_url,
                    profile_source="github",
                    name=name,
                    headline=bio or f"GitHub builder profile: {login}",
                    location=location,
                    current_company=company,
                    current_title=None,
                    raw={
                        "channel": "github",
                        "query": query,
                        "region": region,
                        "sources": [
                            {
                                "source_type": "github",
                                "title": "GitHub profile",
                                "url": profile_url,
                            }
                        ],
                        "github": {
                            "login": login,
                            "followers": details.get("followers"),
                            "public_repos": details.get("public_repos"),
                        },
                    },
                )
            )
        return results

    def _search_openreview(
        self, query: str, limit: int, region: str
    ) -> list[CandidateSourceResult]:
        response = self.client.get(
            "https://api2.openreview.net/notes/search",
            params={"query": query, "content": "authors", "limit": limit},
        )
        response.raise_for_status()
        notes = response.json().get("notes", [])

        results: list[CandidateSourceResult] = []
        for note in notes:
            content = note.get("content", {})
            authors = read_openreview_value(content.get("authors"))
            author_ids = read_openreview_value(content.get("authorids"))
            if not isinstance(authors, list) or not authors:
                continue
            first_author = next((str(author).strip() for author in authors if str(author).strip()), "")
            if not first_author:
                continue
            profile_url = openreview_profile_url(first_author, author_ids)
            title = read_openreview_value(content.get("title"))
            abstract = read_openreview_value(content.get("abstract"))
            results.append(
                CandidateSourceResult(
                    profile_url=profile_url,
                    profile_source="openreview",
                    name=first_author,
                    headline=string_or_none(title) or "OpenReview author",
                    location=None,
                    current_company=None,
                    current_title=None,
                    raw={
                        "channel": "openreview",
                        "query": query,
                        "region": region,
                        "sources": [
                            {
                                "source_type": "openreview",
                                "title": string_or_none(title) or "OpenReview paper",
                                "url": note.get("id"),
                            },
                            {
                                "source_type": "openreview",
                                "title": "OpenReview author profile",
                                "url": profile_url,
                            },
                        ],
                        "paper": {
                            "title": title,
                            "abstract": abstract,
                            "paper_url": note.get("id"),
                            "author_ids": author_ids,
                        },
                    },
                )
            )
        return results

    def _search_arxiv(self, query: str, limit: int) -> list[CandidateSourceResult]:
        response = self.client.get(
            "https://export.arxiv.org/api/query",
            params={"search_query": f"all:{query}", "start": 0, "max_results": limit},
        )
        response.raise_for_status()

        root = ElementTree.fromstring(response.text)
        results: list[CandidateSourceResult] = []
        for entry in root.findall("atom:entry", ARXIV_ATOM_NS):
            title = text_or_none(entry.find("atom:title", ARXIV_ATOM_NS))
            summary = text_or_none(entry.find("atom:summary", ARXIV_ATOM_NS))
            paper_url = text_or_none(entry.find("atom:id", ARXIV_ATOM_NS))
            authors = [
                author_name.text.strip()
                for author_name in entry.findall("atom:author/atom:name", ARXIV_ATOM_NS)
                if author_name.text and author_name.text.strip()
            ]
            if not authors:
                continue
            first_author = authors[0]
            profile_url = (
                "https://arxiv.org/search/?"
                + urlencode({"query": first_author, "searchtype": "author"})
            )
            results.append(
                CandidateSourceResult(
                    profile_url=profile_url,
                    profile_source="arxiv",
                    name=first_author,
                    headline=title or "arXiv author",
                    location=None,
                    current_company=None,
                    current_title=None,
                    raw={
                        "channel": "arxiv",
                        "query": query,
                        "sources": [
                            {
                                "source_type": "arxiv",
                                "title": title or "arXiv paper",
                                "url": paper_url,
                            },
                            {
                                "source_type": "arxiv",
                                "title": "arXiv author search",
                                "url": profile_url,
                            },
                        ],
                        "paper": {
                            "title": title,
                            "summary": summary,
                            "paper_url": paper_url,
                            "authors": authors,
                        },
                    },
                )
            )
        return results

    def _search_exa(self, query: str, limit: int, region: str) -> list[CandidateSourceResult]:
        if not self.settings.exa_api_key.strip():
            raise SourcingConfigError("exa channel requires TALENT_EXA_API_KEY or EXA_API_KEY")
        response = self.client.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": self.settings.exa_api_key.strip()},
            json={
                "query": regionalized_query(query, region),
                "type": "auto",
                "numResults": limit,
                "category": "people",
                "contents": {"highlights": {"maxCharacters": 600}},
            },
        )
        response.raise_for_status()
        payload = response.json()
        return exa_results_to_candidates(payload.get("results", []), query, region, "exa")

    def _search_linkedin(self, query: str, limit: int, region: str) -> list[CandidateSourceResult]:
        if self.settings.exa_api_key.strip():
            response = self.client.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": self.settings.exa_api_key.strip()},
                json={
                    "query": f"site:linkedin.com/in {regionalized_query(query, region)}",
                    "type": "auto",
                    "numResults": limit,
                    "contents": {"highlights": {"maxCharacters": 600}},
                },
            )
            response.raise_for_status()
            payload = response.json()
            return exa_results_to_candidates(
                payload.get("results", []), query, region, "linkedin", domain_hint="linkedin.com"
            )
        if self.settings.brightdata_api_key.strip() and self.settings.brightdata_zone.strip():
            return self._search_brightdata_serp(
                query=f"site:linkedin.com/in {regionalized_query(query, region)}",
                limit=limit,
                region=region,
                channel="linkedin",
            )
        raise SourcingConfigError(
            "linkedin channel requires TALENT_EXA_API_KEY/EXA_API_KEY or "
            "TALENT_BRIGHTDATA_API_KEY/BRIGHTDATA_API_KEY with TALENT_BRIGHTDATA_ZONE/BRIGHTDATA_ZONE"
        )

    def _search_brightdata_discover(
        self, query: str, limit: int, region: str
    ) -> list[CandidateSourceResult]:
        if not self.settings.brightdata_api_key.strip() or not self.settings.brightdata_zone.strip():
            raise SourcingConfigError(
                "brightdata_discover channel requires TALENT_BRIGHTDATA_API_KEY/BRIGHTDATA_API_KEY "
                "and TALENT_BRIGHTDATA_ZONE/BRIGHTDATA_ZONE"
            )
        return self._search_brightdata_serp(
            query=regionalized_query(query, region),
            limit=limit,
            region=region,
            channel="brightdata_discover",
        )

    def _search_brightdata_serp(
        self, query: str, limit: int, region: str, channel: str
    ) -> list[CandidateSourceResult]:
        response = self.client.post(
            "https://api.brightdata.com/request",
            headers={"Authorization": f"Bearer {self.settings.brightdata_api_key.strip()}"},
            json={
                "zone": self.settings.brightdata_zone.strip(),
                "url": f"https://www.google.com/search?q={quote_plus(query)}&hl=en&gl=us",
                "format": "json",
                "method": "GET",
                "country": "us",
            },
        )
        response.raise_for_status()
        payload = response.json()
        organic = payload.get("organic", [])
        return serp_results_to_candidates(organic, query, region, channel)[:limit]


def normalize_search_channels(channels: list[str] | tuple[str, ...] | Any) -> list[str]:
    normalized_channels: list[str] = []
    for channel in channels if isinstance(channels, list | tuple) else []:
        normalized_channel = str(channel).strip().casefold()
        if normalized_channel in SEARCH_CHANNELS and normalized_channel not in normalized_channels:
            normalized_channels.append(normalized_channel)
    return normalized_channels


def default_job_search_channels(title: str, description: str) -> list[str]:
    role_text = f"{title} {description}".casefold()
    if any(keyword in role_text for keyword in ("research", "scientist", "algorithm", "applied ai")):
        return ["linkedin", "github", "openreview", "arxiv", "exa", "brightdata_discover"]
    if any(
        keyword in role_text
        for keyword in ("engineer", "developer", "product", "technical", "builder", "founder")
    ):
        return ["linkedin", "github", "exa", "brightdata_discover"]
    return ["linkedin", "exa", "brightdata_discover"]


def normalize_region(value: Any) -> str:
    return str(value or "").strip().casefold()


def filter_results_by_region(
    results: list[CandidateSourceResult], region: str
) -> list[CandidateSourceResult]:
    if not region:
        return results
    matched = [result for result in results if location_matches_region(result.location, region)]
    return matched or results


def location_matches_region(location: str | None, region: str) -> bool:
    if not location:
        return False
    return region in location.casefold()


def exa_results_to_candidates(
    results: list[dict[str, Any]],
    query: str,
    region: str,
    channel: str,
    domain_hint: str | None = None,
) -> list[CandidateSourceResult]:
    candidates: list[CandidateSourceResult] = []
    for item in results:
        url = string_or_none(item.get("url"))
        title = string_or_none(item.get("title"))
        if not url or (domain_hint and domain_hint not in url):
            continue
        name = infer_name_from_title(title or url)
        summary = summarize_text(item.get("summary")) or summarize_highlights(item.get("highlights"))
        candidates.append(
            CandidateSourceResult(
                profile_url=url,
                profile_source=channel,
                name=name,
                headline=title,
                location=extract_region_text(summary, region),
                current_company=None,
                current_title=None,
                raw={
                    "channel": channel,
                    "query": query,
                    "region": region,
                    "sources": [
                        {
                            "source_type": channel,
                            "title": title or "Exa result",
                            "url": url,
                        }
                    ],
                    "summary": summary,
                },
            )
        )
    return candidates


def serp_results_to_candidates(
    results: list[dict[str, Any]], query: str, region: str, channel: str
) -> list[CandidateSourceResult]:
    candidates: list[CandidateSourceResult] = []
    for item in results:
        url = string_or_none(item.get("link"))
        title = string_or_none(item.get("title"))
        snippet = string_or_none(item.get("description"))
        if not url or not title:
            continue
        candidates.append(
            CandidateSourceResult(
                profile_url=url,
                profile_source=channel,
                name=infer_name_from_title(title),
                headline=title,
                location=extract_region_text(snippet, region),
                current_company=None,
                current_title=None,
                raw={
                    "channel": channel,
                    "query": query,
                    "region": region,
                    "sources": [
                        {
                            "source_type": channel,
                            "title": title,
                            "url": url,
                        }
                    ],
                    "snippet": snippet,
                },
            )
        )
    return candidates


def infer_name_from_title(value: str) -> str:
    title = value.strip()
    if " | " in title:
        return title.split(" | ", 1)[0].strip()
    if " - " in title:
        return title.split(" - ", 1)[0].strip()
    return title


def summarize_highlights(value: Any) -> str | None:
    if not isinstance(value, list):
        return None
    parts = [str(item).strip() for item in value if str(item).strip()]
    return " ".join(parts) or None


def summarize_text(value: Any) -> str | None:
    text = string_or_none(value)
    if not text:
        return None
    return text[:600]


def extract_region_text(text: str | None, region: str) -> str | None:
    if not text or not region:
        return None
    return region.title() if region in text.casefold() else None


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def text_or_none(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    text = element.text.strip()
    return text or None


def read_openreview_value(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def openreview_profile_url(name: str, author_ids: Any) -> str:
    if isinstance(author_ids, list):
        for author_id in author_ids:
            text = str(author_id).strip()
            if text.startswith("~"):
                return f"https://openreview.net/profile?id={quote_plus(text)}"
            if text.startswith("http"):
                return text
    return f"https://openreview.net/search?term={quote_plus(name)}"


def regionalized_query(query: str, region: str) -> str:
    return query if not region else f"{query} {region}"


def github_location_query(region: str) -> str:
    if not region:
        return ""
    return region.split(",", 1)[0].strip()


def canonical_profile_url(profile_url: str) -> str:
    parsed = urlsplit(profile_url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    query = parsed.query
    if netloc.endswith("linkedin.com") and path.startswith("/in/"):
        query = ""
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_source_label(profile_source: str) -> str:
    normalized = profile_source.strip().casefold()
    if normalized == "brightdata_discover":
        return "Bright Data Discover"
    if normalized == "openreview":
        return "OpenReview"
    if normalized == "arxiv":
        return "arXiv"
    return normalized.capitalize()


def http_date_to_iso8601(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return parsedate_to_datetime(str(value)).astimezone(UTC).isoformat()
    except (TypeError, ValueError):
        return None


def available_search_channels(app_settings: Settings | None = None) -> dict[str, bool]:
    current_settings = app_settings or settings
    exa_available = bool(current_settings.exa_api_key.strip())
    brightdata_available = bool(
        current_settings.brightdata_api_key.strip() and current_settings.brightdata_zone.strip()
    )
    return {
        "linkedin": exa_available or brightdata_available,
        "github": True,
        "openreview": True,
        "arxiv": True,
        "exa": exa_available,
        "brightdata_discover": brightdata_available,
    }
