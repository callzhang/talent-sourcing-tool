from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
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
        if _matches_ai_product_engineer(query):
            return list(islice(_ai_product_engineer_fixtures(query), limit))

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


def _matches_ai_product_engineer(query: str) -> bool:
    normalized_query = query.lower()
    return "ai" in normalized_query and "product" in normalized_query and "engineer" in normalized_query


def _ai_product_engineer_fixtures(query: str) -> list[CandidateSourceResult]:
    profiles = [
        {
            "slug": "alex-rivera-ai-product-engineer",
            "name": "Alex Rivera",
            "headline": "AI Product Engineer building customer-facing agent demos",
            "location": "San Francisco, CA",
            "company": "PilotStack",
            "title": "Founding AI Product Engineer",
            "signals": [
                "Built LLM workflow prototypes directly with design partners",
                "Shipped customer demos from ambiguous product requirements",
                "Strong Python, TypeScript, and rapid UI/backend prototyping",
            ],
            "risks": [],
        },
        {
            "slug": "nora-kim-forward-ai-builder",
            "name": "Nora Kim",
            "headline": "Forward-deployed AI builder for B2B workflow automation",
            "location": "New York, NY",
            "company": "FieldPilot AI",
            "title": "Forward Deployed AI Engineer",
            "signals": [
                "Turned enterprise workflow discovery into clickable AI demos",
                "Owns customer requirement synthesis and prototype delivery",
                "Hands-on with LangGraph, Next.js, Python, and eval loops",
            ],
            "risks": [],
        },
        {
            "slug": "samir-patel-agent-product-prototyper",
            "name": "Samir Patel",
            "headline": "Product-minded engineer shipping agentic SaaS prototypes",
            "location": "Seattle, WA",
            "company": "Orbit Agents",
            "title": "AI Product Engineer",
            "signals": [
                "Built multi-agent support and sales assistant demos",
                "Comfortable running customer calls and translating feedback into specs",
                "Strong vibe-coding velocity across React and Python services",
            ],
            "risks": [],
        },
        {
            "slug": "emily-zhang-vibe-coding-ai",
            "name": "Emily Zhang",
            "headline": "AI-native full-stack engineer focused on prototype velocity",
            "location": "Los Angeles, CA",
            "company": "CanvasOps",
            "title": "Senior Product Engineer, AI",
            "signals": [
                "Built internal AI copilots from scratch with minimal design input",
                "Strong product judgment and demo storytelling",
                "Shipped production-grade prototypes under weekly customer deadlines",
            ],
            "risks": [],
        },
        {
            "slug": "jason-lee-ai-solutions-architect",
            "name": "Jason Lee",
            "headline": "AI solutions architect with customer demo experience",
            "location": "Austin, TX",
            "company": "EnterpriseAI Labs",
            "title": "Solutions Architect",
            "signals": [
                "Deep customer-facing discovery experience",
                "Built demo environments for AI workflow pilots",
            ],
            "risks": [
                "More solutions architecture than product engineering",
                "Less public evidence of owning product iteration end-to-end",
            ],
        },
        {
            "slug": "lina-morales-ai-product-founder",
            "name": "Lina Morales",
            "headline": "Former founder building AI workflow products",
            "location": "Miami, FL",
            "company": "Independent",
            "title": "AI Product Builder",
            "signals": [
                "Founded an AI workflow automation tool and built MVP personally",
                "Strong customer discovery and product narrative",
                "Comfortable with fast prototype loops and demo-driven sales",
            ],
            "risks": [],
        },
        {
            "slug": "ben-owens-backend-ml-platform",
            "name": "Ben Owens",
            "headline": "Backend ML platform engineer for model infrastructure",
            "location": "Denver, CO",
            "company": "ScaleGrid",
            "title": "Senior ML Platform Engineer",
            "signals": [
                "Strong Python and infrastructure depth",
                "Experience supporting LLM serving systems",
            ],
            "risks": [
                "Limited product/customer-facing evidence",
                "More platform engineering than AI product prototyping",
            ],
        },
        {
            "slug": "rachel-singh-ai-demo-engineer",
            "name": "Rachel Singh",
            "headline": "Demo-driven AI engineer for early-stage SaaS products",
            "location": "Boston, MA",
            "company": "Northstar AI",
            "title": "Product Engineer",
            "signals": [
                "Built AI demos for founders and beta customers",
                "Fast full-stack builder with strong PMF discovery instincts",
                "Uses evals and customer transcripts to refine prototypes",
            ],
            "risks": [],
        },
        {
            "slug": "owen-brooks-gtm-ai-consultant",
            "name": "Owen Brooks",
            "headline": "AI GTM consultant building lightweight demos",
            "location": "Chicago, IL",
            "company": "GTM Forge",
            "title": "AI GTM Consultant",
            "signals": [
                "Good market discovery and demo communication",
                "Understands AI buyer workflows",
            ],
            "risks": [
                "Consulting-heavy background",
                "Unclear hands-on engineering depth beyond light demos",
            ],
        },
        {
            "slug": "victoria-nguyen-agentic-product-engineer",
            "name": "Victoria Nguyen",
            "headline": "Agentic product engineer building vertical AI workflows",
            "location": "San Mateo, CA",
            "company": "WorkflowSmith",
            "title": "Staff AI Product Engineer",
            "signals": [
                "Built vertical agent workflow demos with customers in the loop",
                "Strong TypeScript, Python, prompt/eval iteration, and product sense",
                "Owns ambiguous requirements through prototype, demo, and follow-up",
            ],
            "risks": [],
        },
    ]
    return [
        CandidateSourceResult(
            linkedin_url=f"https://www.linkedin.com/in/{profile['slug']}",
            name=str(profile["name"]),
            headline=str(profile["headline"]),
            location=str(profile["location"]),
            current_company=str(profile["company"]),
            current_title=str(profile["title"]),
            raw={
                "query": query,
                "source": "mock_bright_data",
                "rank": rank,
                "target_role": "AI Product Engineer",
                "signals": profile["signals"],
                "risks": profile["risks"],
            },
        )
        for rank, profile in enumerate(profiles, start=1)
    ]
