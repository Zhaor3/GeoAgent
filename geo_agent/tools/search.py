from __future__ import annotations

import httpx

from geo_agent.config import settings
from geo_agent.models.schemas import Hypothesis, ToolResult, VisualClues
from geo_agent.tools.base import VerificationTool


class WebSearchTool(VerificationTool):
    name = "Web Search"

    async def verify(self, hypothesis: Hypothesis, clues: VisualClues) -> ToolResult:
        if not settings.SERPAPI_KEY:
            return ToolResult(
                tool_name=self.name,
                hypothesis_rank=hypothesis.rank,
                supports=False,
                confidence_delta=0,
                evidence_summary="SerpAPI key not configured",
            )

        search_terms = []
        ts = clues.text_and_signage
        for text in ts.get("visible_text", []):
            if len(text) > 2:
                search_terms.append(text)
        df = clues.distinctive_features
        search_terms.extend(df.get("brand_names", []))
        search_terms.extend(df.get("landmarks", []))

        if not search_terms:
            return ToolResult(
                tool_name=self.name,
                hypothesis_rank=hypothesis.rank,
                supports=False,
                confidence_delta=0,
                evidence_summary="No text clues to search for",
            )

        location_str = hypothesis.country
        if hypothesis.city:
            location_str = f"{hypothesis.city}, {location_str}"

        query = " ".join(search_terms[:4]) + f" {location_str}"

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(
                    "https://serpapi.com/search.json",
                    params={
                        "q": query,
                        "api_key": settings.SERPAPI_KEY,
                        "num": 5,
                    },
                )
                data = resp.json()
                organic = data.get("organic_results", [])

                if not organic:
                    return ToolResult(
                        tool_name=self.name,
                        hypothesis_rank=hypothesis.rank,
                        supports=False,
                        confidence_delta=-3,
                        evidence_summary=f"No web results for query: {query[:60]}",
                    )

                country_lower = hypothesis.country.lower()
                city_lower = (hypothesis.city or "").lower()
                match_count = 0
                for result in organic:
                    snippet = (result.get("snippet", "") + result.get("title", "")).lower()
                    if country_lower in snippet:
                        match_count += 1
                    if city_lower and city_lower in snippet:
                        match_count += 2

                if match_count >= 3:
                    delta = 10.0
                    supports = True
                    summary = f"Web search strongly supports — '{query[:40]}' matches {hypothesis.city or hypothesis.country}"
                elif match_count >= 1:
                    delta = 5.0
                    supports = True
                    summary = f"Web search partially supports — some mentions of {hypothesis.country}"
                else:
                    delta = -5.0
                    supports = False
                    summary = f"Web search did not find location matches for query"

                return ToolResult(
                    tool_name=self.name,
                    hypothesis_rank=hypothesis.rank,
                    supports=supports,
                    confidence_delta=delta,
                    evidence_summary=summary,
                )
            except Exception as e:
                return ToolResult(
                    tool_name=self.name,
                    hypothesis_rank=hypothesis.rank,
                    supports=False,
                    confidence_delta=0,
                    evidence_summary=f"Web search error: {e}",
                )
