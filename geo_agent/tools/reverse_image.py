from __future__ import annotations

import httpx

from geo_agent.config import settings
from geo_agent.models.schemas import Hypothesis, ToolResult, VisualClues
from geo_agent.tools.base import VerificationTool


class ReverseImageSearchTool(VerificationTool):
    name = "Reverse Image"

    async def verify(self, hypothesis: Hypothesis, clues: VisualClues) -> ToolResult:
        if not settings.SERPAPI_KEY:
            return ToolResult(
                tool_name=self.name,
                hypothesis_rank=hypothesis.rank,
                supports=False,
                confidence_delta=0,
                evidence_summary="SerpAPI key not configured (needed for Google Lens)",
            )

        return ToolResult(
            tool_name=self.name,
            hypothesis_rank=hypothesis.rank,
            supports=False,
            confidence_delta=0,
            evidence_summary="Reverse image search requires image URL — skipped for local images",
        )
