from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class CandidateSourceResult:
    linkedin_url: str
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


class MockBrightDataConnector:
    def search_people(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[CandidateSourceResult]:
        limit = int((params or {}).get("limit", 10))
        fixtures = [
            CandidateSourceResult(
                linkedin_url="https://www.linkedin.com/in/maya-founder-pmm",
                name="Maya Chen",
                headline="Founding PMM for AI developer tools",
                location="San Francisco, CA",
                current_company="WedgeAI",
                current_title="Founding Product Marketing Lead",
                raw={"query": query, "source": "mock_bright_data", "rank": 1},
            ),
            CandidateSourceResult(
                linkedin_url="https://www.linkedin.com/in/leo-growth-ai",
                name="Leo Martinez",
                headline="Product marketer scaling AI startups from 0 to 1",
                location="New York, NY",
                current_company="LaunchGraph",
                current_title="Head of Growth",
                raw={"query": query, "source": "mock_bright_data", "rank": 2},
            ),
            CandidateSourceResult(
                linkedin_url="https://www.linkedin.com/in/priya-ai-market",
                name="Priya Raman",
                headline="AI GTM strategist and former founder",
                location="Austin, TX",
                current_company="SignalForge",
                current_title="GTM Advisor",
                raw={"query": query, "source": "mock_bright_data", "rank": 3},
            ),
        ]
        return fixtures[:limit]


def get_sourcing_connector() -> SourcingConnector:
    return MockBrightDataConnector()
